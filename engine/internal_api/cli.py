"""python -m engine.internal_api pull (--date D | --from D1 --to D2)  (docs/contracts/internal-api.md)"""
import argparse
import sys

from ..store.db import connect, db_path
from ..store.status import days_between
from ..writer import now_local
from .pull import PullError, pull_day


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine.internal_api")
    parser.add_argument("--db", default=None, help="database file (default: ECOM_DB, else out/store/ecom.db)")
    sub = parser.add_subparsers(dest="command", required=True)
    pull_p = sub.add_parser("pull", help="store the internal API snapshot for a day (or a range) in the store")
    pull_p.add_argument("--date", default=None, help="business date (default: today, Eastern)")
    pull_p.add_argument("--from", dest="start", default=None, help="first day of a range, instead of --date")
    pull_p.add_argument("--to", dest="end", default=None, help="last day of the range")
    args = parser.parse_args(argv)

    if args.start:
        days = days_between(args.start, args.end or args.start)
    else:
        days = [args.date or now_local().date().isoformat()]
    conn = connect(args.db)
    failed = []
    try:
        for day in days:
            try:
                s = pull_day(conn, day)
            except PullError as e:
                failed.append(day)
                print(f"internal_api: pull {day} failed, nothing changed: {e}", file=sys.stderr)
                continue
            print(f"internal_api: {day}: {s['rows']} rows, {s['metrics']} metrics, source {s['source']}"
                  + (f" ({s['note']})" if s["note"] else ""))
    finally:
        conn.close()
    if len(days) > 1:
        print(f"internal_api: {len(days) - len(failed)} of {len(days)} days pulled into {db_path(args.db)}")
    return 1 if failed else 0
