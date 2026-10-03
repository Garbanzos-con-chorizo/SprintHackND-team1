"""Command line entry: python -m engine run [--inbox inbox] [--out out] [--date YYYY-MM-DD]."""
import argparse
from pathlib import Path

from .contract import EXPECTED_SOURCES
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
    args = parser.parse_args(argv)

    business_date = args.date or now_local().date().isoformat()
    run(args.inbox, args.out, business_date)
    print(f"engine: wrote {args.out}/ for {business_date}")
    return 0
