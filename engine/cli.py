"""Command line entry: python -m engine run [--inbox inbox] [--out out] [--date YYYY-MM-DD]."""
import argparse
from pathlib import Path

from .contract import EXPECTED_SOURCES
from .writer import now_local, write_outputs


def run(inbox: Path, out: Path, business_date: str) -> None:
    # V1 scaffold: no parsers yet (V2/V3), so nothing is read from inbox.
    # Every expected source is therefore reported as missing, never as $0.
    source_status = {
        "generated_at": now_local().isoformat(),
        "business_date": business_date,
        "sources": {s: {"status": "missing", "files": [], "rows": 0} for s in EXPECTED_SOURCES},
    }
    write_outputs(out, rows=[], source_status=source_status, warnings=[])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="parse inbox/ and write the files in out/")
    run_p.add_argument("--inbox", type=Path, default=Path("inbox"))
    run_p.add_argument("--out", type=Path, default=Path("out"))
    run_p.add_argument("--date", default=None, help="business date YYYY-MM-DD (default: today, Eastern)")
    args = parser.parse_args(argv)

    business_date = args.date or now_local().date().isoformat()
    run(args.inbox, args.out, business_date)
    print(f"engine: wrote {args.out}/ for {business_date}")
    return 0
