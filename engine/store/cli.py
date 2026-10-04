"""python -m engine.store init | load | status | backfill  (docs/contracts/store.md)"""
import argparse
import json
import sys
from pathlib import Path

from .backfill import backfill
from .db import connect, db_path
from .load import LoadError, load_day
from .status import format_status, latest_month, month_bounds, store_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine.store")
    parser.add_argument("--db", default=None, help="database file (default: ECOM_DB, else out/store/ecom.db)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create the database, or add what is missing")
    load_p = sub.add_parser("load", help="load one business date from the engine and pulse files")
    load_p.add_argument("--in-dir", type=Path, default=Path("out"), help="engine output folder (default: out)")
    load_p.add_argument("--date", default=None, help="business date (default: the one in source_status.json)")
    load_p.add_argument("--pulse-dir", type=Path, default=None, help="pulse folder (default: <in-dir>/pulse)")
    status_p = sub.add_parser("status", help="days present, partial and not loaded, per marketplace")
    status_p.add_argument("--month", default=None, help="YYYY-MM (default: the latest month in the store)")
    status_p.add_argument("--from", dest="start", default=None, help="first day, instead of --month")
    status_p.add_argument("--to", dest="end", default=None, help="last day, with --from")
    back_p = sub.add_parser("backfill", help="engine + pulse + load for every day of a range")
    back_p.add_argument("--inbox", type=Path, required=True, help="folder with the exports for the range")
    back_p.add_argument("--from", dest="start", required=True, help="first business date YYYY-MM-DD")
    back_p.add_argument("--to", dest="end", required=True, help="last business date YYYY-MM-DD")
    back_p.add_argument("--out", type=Path, default=Path("out"), help="engine and pulse output folder (default: out)")
    args = parser.parse_args(argv)

    conn = connect(args.db)
    try:
        if args.command == "init":
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            print(f"store: {db_path(args.db)} ready (schema version {version})")
            return 0
        if args.command == "status":
            return status(conn, args)
        if args.command == "backfill":
            return backfill_cmd(conn, args)
        day = args.date or default_date(args.in_dir)
        if not day:
            print("store: no --date given and no source_status.json to take it from", file=sys.stderr)
            return 1
        try:
            s = load_day(conn, args.in_dir, day, args.pulse_dir)
        except LoadError as e:
            print(f"store: load {day} failed, nothing changed: {e}", file=sys.stderr)
            return 1
        print(f"store: loaded {day}: {s['transactions']} transactions, {s['pulse_rows']} pulse rows, "
              f"{s['warnings']} warnings; revenue {s['revenue_cents'] / 100:,.2f} USD "
              f"({', '.join(s['included']) or 'no marketplace with data'}) [{s['run_id']}]")
        return 0
    finally:
        conn.close()


def default_date(in_dir: Path) -> str | None:
    try:
        return json.loads((in_dir / "source_status.json").read_text(encoding="utf-8")).get("business_date")
    except (OSError, ValueError):
        return None


def status(conn, args) -> int:
    if args.start:
        start, end = args.start, args.end or args.start
    else:
        month = args.month or latest_month(conn)
        if not month:
            print(f"store: {db_path(args.db)} is empty (no day loaded yet)")
            return 0
        start, end = month_bounds(month)
    print(f"store: {db_path(args.db)}")
    print(format_status(store_status(conn, start, end)))
    return 0


def backfill_cmd(conn, args) -> int:
    def show(r):
        if r["result"] == "ok":
            print(f"  {r['date']}  ok      {r['transactions']:>5} transactions  revenue {r['revenue_cents'] / 100:>12,.2f} USD"
                  f"  internal {r['internal_rows']:>3} rows  ({', '.join(r['included']) or 'no marketplace with data'})")
        else:
            print(f"  {r['date']}  FAILED  {r['message']}")

    print(f"store: backfill {args.start} to {args.end} from {args.inbox} into {db_path(args.db)}")
    results = backfill(conn, args.inbox, args.out, args.start, args.end, on_day=show)
    failed = [r["date"] for r in results if r["result"] != "ok"]
    print(f"store: {len(results) - len(failed)} of {len(results)} days loaded"
          + (f"; failed: {', '.join(failed)}" if failed else ""))
    print(format_status(store_status(conn, args.start, args.end)))
    return 1 if failed else 0
