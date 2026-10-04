"""What the nightly store holds, for the portal (reports.hub): coverage, runs, and the daily revenue trend.

Read-only, by the table and view names of docs/contracts/store.md ("Rules for readers"): `v_daily`,
`transactions`, `internal_daily`, `kpi_values`, `runs`. engine.store is not imported, and every
database read is in this file. No KPI is computed here: the trend plots `v_daily` as stored.

    python -m reports.store_view [--db out/store/ecom.db]     # prints what the portal would show
"""
import argparse
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def db_path():
    """The store's path as the contract sets it: ECOM_DB, else out/store/ecom.db."""
    return Path(os.environ.get("ECOM_DB") or ROOT / "out" / "store" / "ecom.db")


def summary(path=None, trend_days=35):
    """A dict of what the store holds, or None when there is no store at `path`."""
    path = Path(path or db_path())
    if not path.is_file():
        return None
    con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        one = lambda sql: con.execute(sql).fetchone()
        days = con.execute("SELECT business_date, marketplaces_ok, marketplaces_no_data, revenue_cents "
                           "FROM v_daily ORDER BY business_date").fetchall()
        internal_days, internal_sources = one("SELECT COUNT(DISTINCT business_date), "
                                              "GROUP_CONCAT(DISTINCT source) FROM internal_daily")
        kpis = dict(con.execute("SELECT period_type, COUNT(DISTINCT period_start) FROM kpi_values "
                                "GROUP BY period_type").fetchall())
        runs = con.execute("SELECT command, business_date, started_at, result, rows_written, message "
                           "FROM runs ORDER BY started_at DESC LIMIT 8").fetchall()
        return {
            "path": path,
            "days": len(days),
            "first": days[0][0] if days else None,
            "last": days[-1][0] if days else None,
            "partial": [d for d, _, no_data, _ in days if no_data],
            "transactions": one("SELECT COUNT(*) FROM transactions")[0],
            "internal_days": internal_days,
            "internal_sources": sorted((internal_sources or "").split(",")) if internal_sources else [],
            "kpi_periods": kpis,
            "failed_runs": one("SELECT COUNT(*) FROM runs WHERE result = 'failed'")[0],
            "runs": [dict(zip(("command", "date", "started", "result", "rows", "message"), r)) for r in runs],
            "trend": [{"date": d, "revenue_cents": rev, "partial": bool(no_data)} for d, _, no_data, rev in days[-trend_days:]],
        }
    finally:
        con.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", help="default: $ECOM_DB, else out/store/ecom.db")
    s = summary(ap.parse_args(argv).db)
    print(json.dumps(s, indent=2, default=str) if s else f"no store at {db_path()}")


if __name__ == "__main__":
    main()
