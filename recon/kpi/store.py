"""The nightly store (docs/contracts/store.md), as the KPIs use it.

The only module of recon/kpi that knows table and column names, so reading from somewhere
else (the files, if the store is late) means replacing `load` and nothing more. It reads
`pulse_daily`, `transactions` and `internal_daily` through a read-only connection and writes
only `kpi_values` and its `runs` line. Only `pulse_daily` is required: a missing
`transactions` or `internal_daily` table reads as empty.
"""
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_DB = Path("out") / "store" / "ecom.db"


class StoreError(Exception):
    """The database is absent or cannot be read."""


@dataclass(frozen=True)
class PulseRow:
    business_date: str
    marketplace: str
    status: str
    gross_cents: int | None
    refunds_cents: int | None
    revenue_cents: int | None
    fees_cents: int | None
    orders: int | None


@dataclass(frozen=True)
class Sale:
    marketplace: str
    order_id: str
    customer_id: str
    units: int | None  # None until the transactions carry `units`


@dataclass(frozen=True)
class InternalRow:
    business_date: str
    metric: str
    dimension: str
    value: float
    source: str  # mock | api


@dataclass(frozen=True)
class WindowData:
    """Everything stored for a range of days."""

    pulse: list
    sales: list
    internal: list


def default_path():
    return Path(os.environ.get("ECOM_DB") or DEFAULT_DB)


def connect(path):
    """Open the database read-only. StoreError if it is absent, unreadable or has no pulse_daily."""
    path = Path(path)
    if not path.is_file():
        raise StoreError(f"no database at {path}")
    try:
        con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as e:
        raise StoreError(f"cannot open {path}: {e}") from e
    try:
        tables = _tables(con)
    except StoreError as e:
        con.close()
        raise StoreError(f"cannot read {path}: {e}") from e
    if "pulse_daily" not in tables:
        con.close()
        raise StoreError(f"{path} has no pulse_daily table")
    return con


def latest_business_date(con):
    """The newest day with a pulse row, or None if there is none."""
    newest = _query(con, "SELECT MAX(business_date) FROM pulse_daily")[0][0]
    return date.fromisoformat(newest) if newest else None


def load(con, start, end):
    """WindowData for the days `start`..`end`, both included."""
    span = (start.isoformat(), end.isoformat())
    tables = _tables(con)
    pulse = [
        PulseRow(day, marketplace, status, *map(_int, numbers))
        for day, marketplace, status, *numbers in _query(
            con,
            "SELECT business_date, marketplace, status, gross_cents, refunds_cents, revenue_cents, fees_cents, orders"
            " FROM pulse_daily WHERE business_date BETWEEN ? AND ? ORDER BY business_date, marketplace",
            span,
        )
    ]
    sales = []
    if "transactions" in tables:
        units = "units" if "units" in _columns(con, "transactions") else "NULL"
        sales = [
            Sale(marketplace, order_id, customer_id or "", _int(n))
            for marketplace, order_id, customer_id, n in _query(
                con,
                f"SELECT marketplace, order_id, customer_id, {units} FROM transactions"
                " WHERE type = 'sale' AND business_date BETWEEN ? AND ? ORDER BY business_date, marketplace, order_id",
                span,
            )
        ]
    internal = []
    if "internal_daily" in tables:
        internal = [
            InternalRow(day, metric, dimension, float(value), source)
            for day, metric, dimension, value, source in _query(
                con,
                "SELECT business_date, metric, dimension, value, source FROM internal_daily"
                " WHERE business_date BETWEEN ? AND ? ORDER BY business_date, metric, dimension",
                span,
            )
        ]
    return WindowData(pulse, sales, internal)


def _int(value):
    return None if value is None else int(value)


def _tables(con):
    return {name for (name,) in _query(con, "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}


def _columns(con, table):
    return {row[1] for row in _query(con, f"PRAGMA table_info({table})")}


def _query(con, sql, args=()):
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.Error as e:
        raise StoreError(str(e)) from e


def kpi_rows(doc):
    """The rows of a KPI file for kpi_values: one per KPI, or one per category for a ranking."""
    period = doc["period"]
    rows = []
    for k in doc["kpis"]:
        values = [(row["label"], row["value"]) for row in k["rows"] or []] or [("", k["value"])]
        rows += [(period["type"], period["start"], period["through"], k["id"], dimension, value, k["unit"],
                  k["status"], k["source"], doc["generated_at"]) for dimension, value in values]
    return rows


def save_kpis(path, doc):
    """Record a KPI file in kpi_values, as store.md asks: the period's rows are deleted and
    inserted again in one transaction, and the run is logged. Returns the number of rows."""
    period, rows = doc["period"], kpi_rows(doc)
    run_id = f"kpi-{period['type']}-{period['id']}-{uuid.uuid4().hex[:8]}"
    try:
        con = sqlite3.connect(path)
        try:
            with con:
                con.execute("DELETE FROM kpi_values WHERE period_type = ? AND period_start = ?",
                            (period["type"], period["start"]))
                con.executemany(
                    "INSERT INTO kpi_values (period_type, period_start, period_end, kpi_id, dimension, value, unit,"
                    " status, source, computed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
                con.execute(
                    "INSERT INTO runs (run_id, command, business_date, started_at, finished_at, files_read,"
                    " rows_written, warnings_total, result, message) VALUES (?, 'kpi', NULL, ?, ?, ?, ?, 0, 'ok', ?)",
                    (run_id, doc["generated_at"], doc["generated_at"], json.dumps([]), len(rows), period["label"]))
        finally:
            con.close()
    except sqlite3.Error as e:
        raise StoreError(f"kpi_values not written: {e}") from e
    return len(rows)
