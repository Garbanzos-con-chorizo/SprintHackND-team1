"""internal_api pull (V2.6): one night's internal API snapshot into the store (internal_daily).

Same rule as store load: one date, one database transaction, delete then insert, so a re-run
leaves the same rows. A failed pull changes nothing but a 'failed' row in runs. It runs after
store load for the date: the mock splits that day's pulse revenue (read from the store) into
category sales, so without the pulse there are no category rows (no data, not 0).
"""
import sqlite3
import uuid

from ..store.load import record_run
from ..writer import now_local
from .client import InternalApiError, make_client
from .snapshot import snapshot_rows


class PullError(Exception):
    pass


def store_revenue(conn: sqlite3.Connection):
    """Revenue per marketplace with data on a day, as the store has it (for the mock's category split)."""
    return lambda day: dict(conn.execute(
        "SELECT marketplace, revenue_cents FROM pulse_daily WHERE business_date = ? AND status = 'ok'", (day,)))


def store_units_sold(conn: sqlite3.Connection):
    """Units sold on a day, as the store has them (sale rows; an order without a unit count counts once),
    for the mock's units-by-days-since-listing. None when nothing is stored for the day."""
    def units(day):
        n, rows = conn.execute("SELECT SUM(COALESCE(units, 1)), COUNT(*) FROM transactions "
                               "WHERE business_date = ? AND type = 'sale'", (day,)).fetchone()
        return int(n) if rows else None
    return units


def pull_day(conn: sqlite3.Connection, day: str, api=None) -> dict:
    """Store the snapshot for `day`; returns a summary, raises PullError."""
    api = api or make_client(store_revenue(conn), store_units_sold(conn))
    run_id = f"pull-{day}-{uuid.uuid4().hex[:8]}"
    started = now_local().isoformat()
    try:
        rows = snapshot_rows(api, day)
        with conn:
            conn.execute("DELETE FROM internal_daily WHERE business_date = ?", (day,))
            conn.executemany(
                "INSERT INTO internal_daily (business_date, metric, dimension, value, unit, source, run_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(r["business_date"], r["metric"], r["dimension"], r["value"], r["unit"], r["source"], run_id)
                 for r in rows])
            record_run(conn, "pull", run_id, day, started, [], len(rows), 0, "ok")
    except (InternalApiError, KeyError, ValueError, sqlite3.Error) as e:
        with conn:
            record_run(conn, "pull", run_id, day, started, [], 0, 0, "failed", str(e))
        raise PullError(str(e)) from e
    has_pulse = conn.execute("SELECT 1 FROM pulse_daily WHERE business_date = ? LIMIT 1", (day,)).fetchone()
    return {"run_id": run_id, "business_date": day, "rows": len(rows),
            "metrics": len({r["metric"] for r in rows}), "source": rows[0]["source"] if rows else None,
            "category_rows": sum(r["metric"] == "category_sales_cents" for r in rows),
            "note": "" if has_pulse else "no pulse in the store for this date: no category rows; run store load first"}
