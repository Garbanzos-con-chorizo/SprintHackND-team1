"""Weekly scorecard: Dani's KPI file for an ISO week, rendered by reports.scorecard (O2.5, D2.11).

The page is reports/scorecard/week-<YYYY>-W<WW>.html, next to the day and month scorecards (one
switch links them). No arithmetic here: every number, status and badge comes from
out/kpi/week-<YYYY>-W<WW>.json (docs/contracts/kpi.md). When that file is missing or covers only
part of the week, `python -m recon.kpi --week` writes it first from the store.

The weekly email (reports/email_gen.py) reads reports/weekly/<YYYY>-W<WW>.html and .csv, so the page
is copied there and the KPIs are written as a CSV in that layout (Section, KPI, Marketplace, Value,
Unit, Source; money in dollars, no data blank, simulated KPIs labelled).

    python -m reports.weekly --week 2026-W38 [--kpi-dir out/kpi] [--dest reports/weekly]
    python -m reports.weekly --date 2026-09-16      # the week containing that day
"""
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from reports import hub, scorecard
from reports.theme import CSS, PAGE

ROOT = Path(__file__).resolve().parent.parent
KPI_DIR = ROOT / "out" / "kpi"
DEST = ROOT / "reports" / "weekly"
CSV_COLUMNS = ["Week", "Section", "KPI", "Category", "Marketplace", "Value", "Unit", "Source", "Status", "Note"]
UNITS = {"cents": "USD"}


def parse_week(text):
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", text)
    if not m:
        raise argparse.ArgumentTypeError("week must look like 2026-W38")
    return date.fromisocalendar(int(m[1]), int(m[2]), 1)


def week_id(monday):
    year, week, _ = monday.isocalendar()
    return f"{year}-W{week:02d}"


def covers_week(path):
    if not path.exists():
        return False
    period = json.loads(path.read_text(encoding="utf-8"))["period"]
    return period["through"] >= period["end"]


def kpi_file(week, kpi_dir=KPI_DIR):
    """The week's KPI file; asks recon.kpi for it when it is missing or covers only part of the week."""
    path = Path(kpi_dir) / f"week-{week}.json"
    if not covers_week(path):
        done = subprocess.run([sys.executable, "-m", "recon.kpi", "--week", week, "--out-dir", str(kpi_dir)],
                              cwd=ROOT, capture_output=True, text=True)
        if done.returncode:
            print(f"recon.kpi --week {week}: {(done.stderr or done.stdout).strip().splitlines()[-1:]}")
    if not path.exists():
        raise SystemExit(f"no KPI file for {week} in {kpi_dir}; load the week into the store "
                         f"(python -m engine.store backfill ...), then python -m recon.kpi --week {week}")
    return path


def csv_value(value, unit):
    if value is None:
        return ""
    if unit == "cents":
        return f"{value / 100:.2f}"
    return f"{value:.4f}" if unit == "ratio" else f"{value:g}"


def write_csv(path, kf):
    """The KPI file as rows for Excel and the weekly email: one per KPI, one per top-10 category."""
    week = kf["period"]["id"]
    areas = {a["id"]: a["name"] for a in kf["areas"]}
    sim_label = (kf.get("internal_data") or {}).get("label") or "Simulated internal data"
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for k in kf["kpis"]:
            source = sim_label if k["simulated"] else ("Marketplace files" if k["source"] == "files" else "Goodwill internal data")
            unit = UNITS.get(k["unit"], k["unit"])
            base = [week, areas.get(k["area"], k["area"]), k["name"]]
            tail = [source, k["status"], k.get("note") or ""]
            if k["kind"] == "ranking":
                for r in k["rows"] or []:
                    w.writerow(base + [r["label"], "All", csv_value(r["value"], k["unit"]), unit] + tail)
            else:
                w.writerow(base + ["", "All", csv_value(k["value"], k["unit"]), unit] + tail)


def render_index(dest, scorecards):
    """The weeks built so far, each linking to its scorecard page."""
    weeks = sorted((f.stem for f in dest.glob("*.html") if re.fullmatch(r"\d{4}-W\d{2}", f.stem)), reverse=True)
    rel = Path("..") / scorecards.name
    latest = ' <span class="muted">(latest)</span>'
    items = "\n".join(f'  <li><a href="{rel.as_posix()}/week-{w}.html">{scorecard.stem_label("week-" + w)}'
                      f'{latest if i == 0 else ""}</a></li>' for i, w in enumerate(weeks))
    body = (f'<header><h1>Weekly scorecards</h1><p>{len(weeks)} week(s)</p></header>'
            f'<ul class="days">\n{items or "<li>None yet</li>"}\n</ul>'
            f'<p class="nav"><a href="{rel.as_posix()}/index.html">All scorecards</a> · <a href="../index.html">Reports</a></p>')
    return PAGE.substitute(title="Weekly scorecards", css=CSS, body=body)


def build(kfile, dest=DEST, scorecards=scorecard.DEST):
    """Render the week's scorecard page and its copy + CSV for the email. Returns the scorecard page."""
    kf = json.loads(Path(kfile).read_text(encoding="utf-8"))
    page = scorecard.build(kfile, scorecards)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    week = kf["period"]["id"]
    shutil.copyfile(page, dest / f"{week}.html")
    write_csv(dest / f"{week}.csv", kf)
    (dest / "index.html").write_text(render_index(dest, Path(scorecards)), encoding="utf-8")
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--week", type=parse_week, help="ISO week, e.g. 2026-W38")
    g.add_argument("--date", type=date.fromisoformat, help="any day in the week")
    ap.add_argument("--kpi-dir", default=str(KPI_DIR), help="folder with week-<id>.json (python -m recon.kpi)")
    ap.add_argument("--dest", default=str(DEST))
    args = ap.parse_args(argv)
    monday = args.week or args.date - timedelta(days=args.date.weekday())
    week = week_id(monday)
    page = build(kpi_file(week, Path(args.kpi_dir)), Path(args.dest))
    kf = json.loads((page.with_suffix(".json")).read_text(encoding="utf-8"))
    sim = sum(k["simulated"] for k in kf["kpis"])
    cov = kf["coverage"]
    print(f"wrote {page} and {Path(args.dest) / week}.html/.csv: {cov['days_complete']}/{cov['days_expected']} days "
          f"complete, {len(kf['kpis'])} KPIs ({sim} simulated)")
    print(f"wrote {hub.build(Path(args.dest).parent)}")


if __name__ == "__main__":
    main()
