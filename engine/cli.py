"""Command line entry: python -m engine run [--inbox inbox] [--out out] [--date YYYY-MM-DD]."""
import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

from .coverage import build_source_coverage
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
    write_outputs(out, rows=batch.rows, source_status=source_status, warnings=batch.warnings,
                  payouts=batch.payouts, bank=batch.bank,
                  source_coverage=build_source_coverage(business_date, batch.files), tables=batch.tables)


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
    fetch_p.add_argument("--from", dest="start", default=None, help="with --to and --simulate: every day of the range")
    fetch_p.add_argument("--to", dest="end", default=None, help="last business date of the range")
    fetch_p.add_argument("--source", default=None, help="only this source, e.g. upright (several: a,b)")
    fetch_p.add_argument("--close-month", default=None, metavar="YYYY-MM",
                         help="the month-end sources of that month (ledger, bank feed, statements) instead of a day's reports")
    fetch_p.add_argument("--simulate", action="store_true",
                         help="demo: write synthetic reports as each provider's API would deliver them")
    args = parser.parse_args(argv)

    business_date = args.date or now_local().date().isoformat()
    if args.command == "fetch":
        if args.close_month:
            if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.close_month) or args.date or args.start or args.end:
                parser.error("--close-month takes YYYY-MM and goes without --date, --from or --to")
            return fetch_close(args.inbox, args.out, args.close_month, args.source, simulate=args.simulate)
        if args.start or args.end:
            if not (args.start and args.end and args.simulate):
                parser.error("--from and --to go together and need --simulate")
            days = (date.fromisoformat(args.start) + timedelta(days=i)
                    for i in range((date.fromisoformat(args.end) - date.fromisoformat(args.start)).days + 1))
            codes = [fetch(args.inbox, args.out, d.isoformat(), args.source, simulate=True) for d in days]
            return 1 if any(codes) else 0
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


def fetch_close(inbox: Path, out: Path, month: str, only: str | None = None, scrapers=None,
                env: dict | None = None, simulate: bool = False) -> int:
    """The month-end sources of `month` (YYYY-MM) into inbox/. With `simulate`, each provider's simulator
    writes the file its API would have delivered, and `out/expected_close_sources.json` holds the answer
    key for those files, computed from the generated records (never by a parser)."""
    from .scrapers.base import load_scrapers
    from .scrapers.env import load_env
    from .scrapers.runner import run_close_scrapers, write_log

    scrapers = load_scrapers() if scrapers is None else scrapers
    log, expected = run_close_scrapers(scrapers, month, inbox, load_env() if env is None else env, only, simulate)
    write_log(out, log)
    if simulate:
        key = {"month": month, "simulated": True,
               "note": "Answer key for the files `engine fetch --simulate --close-month` wrote: synthetic data, "
                       "computed from the generated records, never by the engine's parsers.", **expected}
        with open(out / "expected_close_sources.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(key, f, indent=2)
            f.write("\n")
    for source, entry in log["sources"].items():
        detail = f" ({entry['detail']})" if entry["detail"] else ""
        print(f"fetch {source}: {entry['status']}{detail}")
    return 1 if any(e["status"] == "failed" for e in log["sources"].values()) else 0
