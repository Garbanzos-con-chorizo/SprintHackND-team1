"""store load (V2.2): one business date from the engine and pulse files into the store.

Rules from docs/contracts/store.md: one date, one database transaction, all or nothing. The
date's rows are deleted and inserted again, so re-running a date leaves the same data and rows
the engine no longer produces disappear. A failed load changes nothing but the runs log.
"""
import csv
import json
import sqlite3
import uuid
from pathlib import Path

from ..contract import COLUMNS
from ..writer import now_local

TXN_INSERT = (
    "INSERT OR REPLACE INTO transactions (txn_id, source, marketplace, type, business_date, order_id, "
    "customer_id, customer_basis, gross_cents, fee_cents, units, shipping_cents, handling_cents, source_file, "
    "source_row, run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
# The v1 columns are required; shipping_cents, handling_cents and units (v2) are read when present,
# so a transactions.csv written before them still loads (0, 0 and unknown).
REQUIRED = COLUMNS[:COLUMNS.index("shipping_cents")]
PULSE_FIELDS = ["gross_cents", "refunds_cents", "revenue_cents", "fees_cents", "orders", "customers",
                "customer_basis"]


class LoadError(Exception):
    """The inputs for a date are missing or inconsistent; nothing was loaded."""


def load_day(conn: sqlite3.Connection, in_dir: Path, business_date: str,
             pulse_dir: Path | None = None) -> dict:
    """Load `business_date` from `in_dir` (transactions.csv, warnings.json, source_status.json)
    and `pulse_dir/<date>.json` (default `in_dir/pulse`). Returns a summary; raises LoadError."""
    run_id = f"load-{business_date}-{uuid.uuid4().hex[:8]}"
    started = now_local().isoformat()
    try:
        txns = read_transactions(in_dir / "transactions.csv", business_date)
        pulse = read_pulse((pulse_dir or in_dir / "pulse") / f"{business_date}.json", business_date)
        warnings = read_json(in_dir / "warnings.json", default=[])
        files = files_read(read_json(in_dir / "source_status.json", default={}))
        with conn:
            for table in ("transactions", "pulse_daily", "warnings"):
                conn.execute(f"DELETE FROM {table} WHERE business_date = ?", (business_date,))
            conn.executemany(TXN_INSERT, [[t[c] for c in COLUMNS[:10]] + [
                t["units"], t["shipping_cents"], t["handling_cents"], t["source_file"], t["source_row"], run_id]
                for t in txns])
            conn.executemany(
                "INSERT INTO pulse_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [[business_date, mk, m["status"]] + [m.get(f) for f in PULSE_FIELDS] + [run_id]
                 for mk, m in pulse["marketplaces"].items()])
            conn.executemany(
                "INSERT INTO warnings VALUES (?, ?, ?, ?, ?, ?, ?)",
                [[run_id, i, business_date, w.get("kind", ""), w.get("source_file") or "", w.get("source_row"),
                  w.get("reason") or ""] for i, w in enumerate(warnings, 1)])
            log_run(conn, run_id, business_date, started, files, len(txns), len(warnings), "ok")
    except (LoadError, sqlite3.Error) as e:
        with conn:
            log_run(conn, run_id, business_date, started, [], 0, 0, "failed", str(e))
        raise LoadError(str(e)) from e
    return {"run_id": run_id, "business_date": business_date, "transactions": len(txns),
            "pulse_rows": len(pulse["marketplaces"]), "warnings": len(warnings),
            "revenue_cents": pulse["enterprise"]["revenue_cents"], "included": pulse["enterprise"]["included"]}


def read_transactions(path: Path, business_date: str) -> list[dict]:
    """The rows of transactions.csv for one date (the file may hold other days)."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                raise LoadError(f"{path}: missing column(s) {', '.join(missing)}")
            rows = [r for r in reader if r["business_date"] == business_date]
    except OSError as e:
        raise LoadError(f"cannot read {path}: {e.strerror or e}") from e
    try:
        for r in rows:
            r["customer_id"] = r["customer_id"] or ""
            for c in ("gross_cents", "fee_cents", "source_row"):
                r[c] = int(r[c])
            for c in ("shipping_cents", "handling_cents"):
                r[c] = int(r.get(c) or 0)
            r["units"] = int(r["units"]) if r.get("units") else None
    except ValueError as e:
        raise LoadError(f"{path}: bad number ({e})") from e
    return rows


def read_pulse(path: Path, business_date: str) -> dict:
    if not path.exists():
        raise LoadError(f"no pulse file {path}: run `python -m recon.pulse --date {business_date}` first")
    pulse = read_json(path)
    if pulse.get("business_date") != business_date:
        raise LoadError(f"{path} is for {pulse.get('business_date')}, not {business_date}")
    marketplaces, enterprise = pulse.get("marketplaces"), pulse.get("enterprise")
    if not isinstance(marketplaces, dict) or not isinstance(enterprise, dict) or \
            not all(isinstance(m, dict) and m.get("status") for m in marketplaces.values()):
        raise LoadError(f"{path} does not follow docs/contracts/pulse.md (marketplaces with a status, enterprise)")
    return pulse


def read_json(path: Path, default=None):
    if default is not None and not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LoadError(f"cannot read {path}: {e}") from e


def files_read(source_status: dict) -> list[str]:
    return sorted({f for s in (source_status.get("sources") or {}).values() for f in s.get("files", [])})


def log_run(conn, run_id, business_date, started, files, rows, warnings, result, message=""):
    record_run(conn, "load", run_id, business_date, started, files, rows, warnings, result, message)


def record_run(conn, command, run_id, business_date, started, files, rows, warnings, result, message=""):
    """One row in `runs` for any command that writes to the store (load, pull, kpi)."""
    conn.execute(
        "INSERT INTO runs (run_id, command, business_date, started_at, finished_at, files_read, rows_written, "
        "warnings_total, result, message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, command, business_date, started, now_local().isoformat(), json.dumps(files), rows, warnings,
         result, message))
