"""Weekly dashboard: a week of daily pulses plus the KPI groups from decision 006.

Reads out/pulse/<date>.json for the ISO week (Monday to Sunday), adds internal data from the
mock Goodwill internal API (reports/mock_api.py), and writes reports/weekly/<YYYY>-W<WW>.html,
<YYYY>-W<WW>.csv and index.html. KPIs are computed in reports/kpi.py (shared with the monthly
scorecard); every KPI says where it comes from, and simulated ones are badged on the page.

    python -m reports.weekly --week 2026-W38 [--src out/pulse] [--dest reports/weekly]
    python -m reports.weekly --date 2026-09-16      # the week containing that day
"""
import argparse
import re
from datetime import date, timedelta
from pathlib import Path

from reports import hub, kpi
from reports.pulse import CSS, PAGE

ROOT = Path(__file__).resolve().parent.parent


def parse_week(text):
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", text)
    if not m:
        raise argparse.ArgumentTypeError("week must look like 2026-W38")
    return date.fromisocalendar(int(m[1]), int(m[2]), 1)


def render(monday, pulses, rows, t):
    sunday = monday + timedelta(days=6)
    year, week_no, _ = monday.isocalendar()
    text, complete = kpi.summary(rows, t, 7, "week")
    body = kpi.PAGE_BODY.substitute(
        title=f"Weekly dashboard: week {week_no}, {year}",
        range=f"{monday:%a %b} {monday.day} to {sunday:%a %b} {sunday.day}, {sunday.year}",
        coverage=f"{len(pulses)} of 7 daily pulses",
        mock=" · <strong>mock data</strong>" if any(p.get("mock") for p in pulses) else "",
        summary=kpi.escape(text), summary_class="" if complete else " alert", simnote=kpi.SIMNOTE,
        sections=kpi.sections_html(rows, t),
        definitions=kpi.definitions("ISO week, Monday to Sunday, Eastern time."),
        nav='<a href="index.html">All weeks</a>',
    )
    return PAGE.substitute(title=f"Weekly dashboard {year}-W{week_no:02d}", css=CSS + kpi.KPI_CSS, body=body)


def render_index(dest):
    weeks = sorted((f.stem for f in dest.glob("*.html") if re.fullmatch(r"\d{4}-W\d{2}", f.stem)), reverse=True)
    items = "\n".join(f'  <li><a href="{w}.html">{w}{" (latest)" if i == 0 else ""}</a></li>'
                      for i, w in enumerate(weeks))
    body = (f'<header><h1>Weekly dashboard</h1><p>Goodwill Michiana e-commerce · {len(weeks)} week(s)</p></header>'
            f'<ul class="days">\n{items}\n</ul>')
    return PAGE.substitute(title="Weekly dashboard", css=CSS + kpi.KPI_CSS, body=body)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--week", type=parse_week, help="ISO week, e.g. 2026-W38")
    g.add_argument("--date", type=date.fromisoformat, help="any day in the week")
    ap.add_argument("--src", default=str(ROOT / "out" / "pulse"))
    ap.add_argument("--dest", default=str(ROOT / "reports" / "weekly"))
    args = ap.parse_args(argv)
    monday = args.week or args.date - timedelta(days=args.date.weekday())
    sunday = monday + timedelta(days=6)
    src = Path(args.src)
    pulses = kpi.load_days(src, monday, sunday)
    if not pulses:
        raise SystemExit(f"no pulse files for the week of {monday} in {src}")
    prior = kpi.load_days(src, monday - timedelta(days=7), monday - timedelta(days=1))
    rows, t = kpi.compute(monday, sunday, pulses, prior, 7, "week")
    year, week_no, _ = monday.isocalendar()
    name = f"{year}-W{week_no:02d}"
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{name}.html").write_text(render(monday, pulses, rows, t), encoding="utf-8")
    kpi.write_csv(dest / f"{name}.csv", "Week", name, rows)
    (dest / "index.html").write_text(render_index(dest), encoding="utf-8")
    sim = sum(k["source"] == "simulated" for k in rows)
    print(f"wrote {dest / name}.html and .csv: {len(pulses)}/7 days, {len(rows)} KPIs ({sim} simulated)")
    print(f"wrote {hub.build(dest.parent)}")


if __name__ == "__main__":
    main()
