"""Weekly dashboard: the week's COO scorecard, rendered from Dani's KPI file (docs/contracts/kpi.md).

The week's numbers come from `python -m recon.kpi --week <id>` (`out/kpi/week-<id>.json`), the same file and
the same page as the nightly week-to-date scorecard, so the two never disagree. This command makes sure the
file exists (computing it from the store when it doesn't), then writes

  reports/scorecard/week-<YYYY>-W<WW>.html   the page, via reports.scorecard (no arithmetic here)
  reports/scorecard/week-<YYYY>-W<WW>.csv    the KPI table for Excel and Power BI (engine.export)

    python -m reports.weekly --week 2026-W38 [--kpi-dir out/kpi] [--dest reports/scorecard]
    python -m reports.weekly --date 2026-09-16      # the week containing that day
"""
import argparse
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from engine.export.kpi_csv import write_kpi_csv
from reports import hub, scorecard

ROOT = Path(__file__).resolve().parent.parent


def parse_week(text):
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", text)
    if not m:
        raise argparse.ArgumentTypeError("week must look like 2026-W38")
    return date.fromisocalendar(int(m[1]), int(m[2]), 1)


def kpi_file_for(week_id, kpi_dir):
    """out/kpi/week-<id>.json, computed from the store first if it is not there (a full Monday-to-Sunday week)."""
    path = Path(kpi_dir) / f"week-{week_id}.json"
    if not path.exists():
        done = subprocess.run([sys.executable, "-m", "recon.kpi", "--week", week_id, "--out-dir", str(kpi_dir)],
                              cwd=ROOT, capture_output=True, text=True)
        if done.returncode or not path.exists():
            raise SystemExit(f"no KPI file for {week_id} and recon.kpi could not make one: "
                             f"{(done.stderr or done.stdout).strip()[-300:]}")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--week", type=parse_week, help="ISO week, e.g. 2026-W38")
    g.add_argument("--date", type=date.fromisoformat, help="any day in the week")
    ap.add_argument("--kpi-dir", default=str(ROOT / "out" / "kpi"))
    ap.add_argument("--dest", default=str(ROOT / "reports" / "scorecard"))
    args = ap.parse_args(argv)
    monday = args.week or args.date - timedelta(days=args.date.weekday())
    year, week_no, _ = monday.isocalendar()
    kpi_file = kpi_file_for(f"{year}-W{week_no:02d}", args.kpi_dir)
    page = scorecard.build(kpi_file, args.dest)
    write_kpi_csv(kpi_file, args.dest)
    page = scorecard.build(kpi_file, args.dest)  # again, so the page links the CSV just written
    print(f"wrote {page} and its CSV")
    print(f"wrote {hub.build(Path(args.dest).parent)}")


if __name__ == "__main__":
    main()
