"""python -m engine.store init | load --in-dir out --date YYYY-MM-DD  (docs/contracts/store.md)"""
import argparse
import json
import sys
from pathlib import Path

from .db import connect, db_path
from .load import LoadError, load_day


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine.store")
    parser.add_argument("--db", default=None, help="database file (default: ECOM_DB, else out/store/ecom.db)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create the database, or add what is missing")
    load_p = sub.add_parser("load", help="load one business date from the engine and pulse files")
    load_p.add_argument("--in-dir", type=Path, default=Path("out"), help="engine output folder (default: out)")
    load_p.add_argument("--date", default=None, help="business date (default: the one in source_status.json)")
    load_p.add_argument("--pulse-dir", type=Path, default=None, help="pulse folder (default: <in-dir>/pulse)")
    args = parser.parse_args(argv)

    conn = connect(args.db)
    try:
        if args.command == "init":
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            print(f"store: {db_path(args.db)} ready (schema version {version})")
            return 0
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
