"""Command line entry: python -m engine run [--inbox inbox] [--out out] [--date YYYY-MM-DD]."""
import argparse
from pathlib import Path

from .ingest import EmailAttachmentAdapter, NormalizedBatch, ingest
from .parsers import Parser
from .status import build_source_status
from .writer import now_local, write_outputs


def run(inbox: Path, out: Path, business_date: str, parsers: list[Parser] | None = None) -> None:
    batch = ingest([EmailAttachmentAdapter(inbox, parsers)], business_date)
    write_day(batch, out, business_date)


def write_day(batch: NormalizedBatch, out: Path, business_date: str) -> None:
    """The three output files for one business date from an ingested inbox. Backfill ingests once
    and calls this per day, so a backfilled day is exactly what `engine run --date` would write."""
    source_status = build_source_status(business_date, now_local().isoformat(), batch.files, batch.rows)
    write_outputs(out, rows=batch.rows, source_status=source_status, warnings=batch.warnings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="parse inbox/ and write the files in out/")
    run_p.add_argument("--inbox", type=Path, default=Path("inbox"))
    run_p.add_argument("--out", type=Path, default=Path("out"))
    run_p.add_argument("--date", default=None, help="business date YYYY-MM-DD (default: today, Eastern)")
    fetch_p = sub.add_parser("fetch", help="download reports from the portals into inbox/")
    fetch_p.add_argument("--inbox", type=Path, default=Path("inbox"))
    fetch_p.add_argument("--out", type=Path, default=Path("out"))
    fetch_p.add_argument("--date", default=None, help="business date YYYY-MM-DD (default: today, Eastern)")
    fetch_p.add_argument("--source", default=None, help="only this source, e.g. upright")
    fetch_p.add_argument("--simulate", action="store_true",
                         help="demo: write synthetic reports as each provider's API would deliver them")
    args = parser.parse_args(argv)

    business_date = args.date or now_local().date().isoformat()
    if args.command == "fetch":
        return fetch(args.inbox, args.out, business_date, args.source, simulate=args.simulate)
    run(args.inbox, args.out, business_date)
    print(f"engine: wrote {args.out}/ for {business_date}")
    return 0


def fetch(inbox: Path, out: Path, business_date: str, only: str | None = None,
          scrapers=None, env: dict | None = None, simulate: bool = False) -> int:
    from .scrapers.base import load_scrapers
    from .scrapers.env import load_env
    from .scrapers.runner import run_scrapers, write_log

    scrapers = load_scrapers() if scrapers is None else scrapers
    log = run_scrapers(scrapers, business_date, inbox, load_env() if env is None else env, only, simulate)
    write_log(out, log)
    for source, entry in log["sources"].items():
        detail = f" ({entry['detail']})" if entry["detail"] else ""
        print(f"fetch {source}: {entry['status']}{detail}")
    # Exit non-zero only for real failures; 'not_configured' is expected until a portal is set up.
    return 1 if any(e["status"] == "failed" for e in log["sources"].values()) else 0
