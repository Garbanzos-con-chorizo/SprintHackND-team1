"""python -m recon.pulse --date YYYY-MM-DD"""
import argparse
import sys
from datetime import date, datetime, timedelta
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

    out_dir = args.out_dir or args.in_dir / "pulse"
    prior_date = (date.fromisoformat(business_date) - timedelta(days=1)).isoformat()
    try:
        prior_pulse = io.load_pulse(out_dir / f"{prior_date}.json")
    except (OSError, ValueError):
        prior_pulse = None  # unreadable prior file: recompute from the rows instead

    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    pulse = calc.build_pulse(rows, source_status, warnings, business_date, generated_at, prior_pulse)

    target = io.write_pulse(out_dir, pulse)
    e = pulse["enterprise"]
    left_out = ", ".join(f"{x['marketplace']} {x['status']}" for x in e["excluded"]) or "none"
    print(f"pulse: wrote {target} (revenue {e['revenue_cents'] / 100:.2f} USD, no data: {left_out})")
    return 0
