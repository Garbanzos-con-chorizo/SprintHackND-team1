"""python -m engine.export kpi-csv (--kpi-file F | --period day|week|month) [--dest DIR]"""
import argparse
import sys
from pathlib import Path

from .kpi_csv import write_kpi_csv

KPI_DIR = Path("out") / "kpi"
DEST = Path("reports") / "scorecard"  # next to the scorecard page of the same name, for its download link


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine.export")
    sub = parser.add_subparsers(dest="command", required=True)
    csv_p = sub.add_parser("kpi-csv", help="the KPI file as one long CSV for Excel and Power BI")
    src = csv_p.add_mutually_exclusive_group(required=True)
    src.add_argument("--kpi-file", type=Path, help="a KPI file from python -m recon.kpi")
    src.add_argument("--period", choices=["day", "week", "month"], help="use out/kpi/latest-<period>.json")
    csv_p.add_argument("--dest", type=Path, default=DEST, help=f"output folder (default: {DEST.as_posix()})")
    args = parser.parse_args(argv)

    kpi_path = args.kpi_file or KPI_DIR / f"latest-{args.period}.json"
    if not kpi_path.exists():
        print(f"export: no KPI file at {kpi_path}; run `python -m recon.kpi` first", file=sys.stderr)
        return 1
    try:
        target = write_kpi_csv(kpi_path, args.dest)
    except (ValueError, KeyError) as e:
        print(f"export: {kpi_path} does not follow docs/contracts/kpi.md ({e})", file=sys.stderr)
        return 1
    print(f"export: wrote {target}")
    return 0
