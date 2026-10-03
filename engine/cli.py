"""Command line entry: python -m engine run [--inbox inbox] [--out out] [--date YYYY-MM-DD]."""
import argparse
from pathlib import Path

from .contract import EXPECTED_SOURCES
from .dedupe import dedupe_rows
from .parsers import Ambiguous, NoMatch, Parser, detect_source, load_sources
from .table import SUPPORTED_SUFFIXES, UnreadableFile, read_table
from .writer import now_local, write_outputs


def _inbox_files(inbox: Path) -> list[Path]:
    if not inbox.is_dir():
        return []
    return sorted(
        p for p in inbox.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        and not p.name.startswith(("~$", "."))  # Excel lock files, hidden files
    )


def _file_warning(name: str, kind: str, reason: str) -> dict:
    return {"source_file": name, "source_row": 0, "kind": kind, "reason": reason}


def run(inbox: Path, out: Path, business_date: str, parsers: list[Parser] | None = None) -> None:
    parsers = load_sources() if parsers is None else parsers
    rows: list[dict] = []
    warnings: list[dict] = []

    for path in _inbox_files(inbox):
        try:
            table = read_table(path)
            parser = detect_source(table, parsers)
        except UnreadableFile as exc:
            warnings.append(_file_warning(path.name, "unparseable", str(exc)))
            continue
        except (NoMatch, Ambiguous) as exc:
            warnings.append(_file_warning(path.name, "unparseable", str(exc)))
            continue
        result = parser.parse(table)
        rows.extend(result.rows)
        warnings.extend(result.warnings)

    rows, duplicate_warnings = dedupe_rows(rows)
    warnings.extend(duplicate_warnings)

    # Per-source status is P-V4. Until then every expected source reports `missing`, never $0.
    source_status = {
        "generated_at": now_local().isoformat(),
        "business_date": business_date,
        "sources": {s: {"status": "missing", "files": [], "rows": 0} for s in EXPECTED_SOURCES},
    }
    write_outputs(out, rows=rows, source_status=source_status, warnings=warnings)


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
    args = parser.parse_args(argv)

    business_date = args.date or now_local().date().isoformat()
    if args.command == "fetch":
        return fetch(args.inbox, args.out, business_date, args.source)
    run(args.inbox, args.out, business_date)
    print(f"engine: wrote {args.out}/ for {business_date}")
    return 0


def fetch(inbox: Path, out: Path, business_date: str, only: str | None = None,
          scrapers=None, env: dict | None = None) -> int:
    from .scrapers.base import load_scrapers
    from .scrapers.env import load_env
    from .scrapers.runner import run_scrapers, write_log

    scrapers = load_scrapers() if scrapers is None else scrapers
    log = run_scrapers(scrapers, business_date, inbox, load_env() if env is None else env, only)
    write_log(out, log)
    for source, entry in log["sources"].items():
        detail = f" ({entry['detail']})" if entry["detail"] else ""
        print(f"fetch {source}: {entry['status']}{detail}")
    # Exit non-zero only for real failures; 'not_configured' is expected until a portal is set up.
    return 1 if any(e["status"] == "failed" for e in log["sources"].values()) else 0
