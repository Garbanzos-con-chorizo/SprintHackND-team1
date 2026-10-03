"""python -m recon.pulse --date YYYY-MM-DD"""
import argparse
import sys
from datetime import date
from pathlib import Path

from . import calc, io


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pulse", description="Write the nightly pulse JSON.")
    parser.add_argument("--date", type=date.fromisoformat, help="business date; default: the date in source_status.json")
    parser.add_argument("--in-dir", type=Path, default=Path("out"), help="folder with the engine output (default: out)")
    parser.add_argument("--out-dir", type=Path, default=None, help="where to write (default: <in-dir>/pulse)")
    args = parser.parse_args(argv)

    try:
        rows, dropped = io.load_transactions(args.in_dir / "transactions.csv")
    except (OSError, ValueError) as e:
        print(f"pulse: cannot read transactions: {e}", file=sys.stderr)
        return 1
    source_status = io.load_source_status(args.in_dir / "source_status.json")
    warnings = io.load_warnings(args.in_dir / "warnings.json")

    business_date = args.date.isoformat() if args.date else (source_status or {}).get("business_date")
    if not business_date:
        print("pulse: no --date given and no source_status.json to take it from", file=sys.stderr)
        return 1
    if dropped:
        print(f"pulse: dropped {dropped} repeated txn_id row(s)", file=sys.stderr)

    try:
        calc.build_pulse(rows, source_status, warnings, business_date)
    except NotImplementedError as e:
        print(f"pulse: read {len(rows)} rows for {business_date}, but {e}", file=sys.stderr)
        return 2
    # P-D4: write <out-dir>/<date>.json and latest.json
    return 0
