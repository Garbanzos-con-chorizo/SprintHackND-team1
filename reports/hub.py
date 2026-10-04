"""Portal for the reporting suite: reports/index.html links to the latest nightly pulse, weekly
dashboard, monthly COO scorecard and month-end close, with their files. Static HTML, opens from disk.

Each card shows the headline sentence of the latest page (its summary line), red when that page
flags missing data, so staff see the state of things before clicking.

    python -m reports.hub [--root reports]     # also run at the end of run_nightly, weekly and monthly
"""
import argparse
import re
from datetime import date, datetime
from html import escape, unescape
from pathlib import Path

from reports.theme import CSS, PAGE

ROOT = Path(__file__).resolve().parent.parent

HUB_CSS = """
/* One panel per report, divided by hairlines; the top rule is blue, red when the page flags missing data */
.hub-grid { display:flex; flex-wrap:wrap; gap:1px; margin:var(--sp-5) 0 0; background:var(--rule); border:var(--bd); }
.hub-card { flex:1 1 260px; display:flex; flex-direction:column; gap:var(--sp-3); padding:var(--sp-5) var(--sp-5) var(--sp-5);
  background:var(--bg); border-top:3px solid var(--blue); }
.hub-card.alert { border-top-color:var(--red); }
.hub-card.empty { border-top-color:var(--rule-dk); background:var(--bg-1); }
.hub-card .label { color:var(--blue); }
.hub-card.alert .label { color:var(--red); }
.hub-card h2 { font-size:var(--fs-lead); font-weight:var(--fw-bold); line-height:1.3; }
.hub-card h2 a { color:var(--ink); }
.hub-card .headline { font-weight:var(--fw-semi); line-height:1.4; }
.hub-card .links { font-size:var(--fs-small); color:var(--muted); margin-top:auto; padding-top:var(--sp-3); border-top:var(--bd); }
.hub-card .built { font-size:var(--fs-small); color:var(--muted); }
@media print {
  @page { size:letter portrait; margin:0.5in; }
  .hub-grid { margin-top:8pt; }
  .hub-card { flex-basis:45%; padding:6pt 8pt; gap:3pt; break-inside:avoid; }
  .hub-card h2 { font-size:10pt; }
  .hub-card .links { display:none; }
}
"""


def _long_day(stem):
    d = date.fromisoformat(stem)
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def _week(stem):
    year, week = stem.split("-W")
    monday = date.fromisocalendar(int(year), int(week), 1)
    return f"Week {int(week)}, {year} (from {monday:%b} {monday.day})"


def _month(stem):
    return f"{date.fromisoformat(stem[:7] + '-01'):%B %Y}"


# What the portal shows: folder, page name pattern, how to name the period, related files.
SUITE = [
    {"title": "Nightly pulse", "what": "Revenue and customers by marketplace for the day that just ended.",
     "folder": "pulse", "pattern": r"\d{4}-\d{2}-\d{2}", "period": _long_day,
     "extras": lambda s: [(f"{s}.csv", "CSV"), (f"{s}.email.html", "Email copy")],
     "archive": ("index.html", "All days"),
     "build": "python -m reports.run_nightly --scenario gw_day_clean"},
    {"title": "Weekly dashboard", "what": "The week's totals and the five KPI groups.",
     "folder": "weekly", "pattern": r"\d{4}-W\d{2}", "period": _week,
     "extras": lambda s: [(f"{s}.csv", "KPI CSV")],
     "archive": ("index.html", "All weeks"),
     "build": "python -m reports.weekly --week 2026-W38"},
    {"title": "COO scorecard (monthly)", "what": "Goodwill's 15 KPIs in five areas, from the KPI file.",
     "folder": "scorecard", "pattern": r"month-\d{4}-\d{2}", "period": lambda s: _month(s[6:]),
     "extras": lambda s: [(f"{s}.json", "KPI file"), (f"../monthly/{s[6:]}.csv", "Daily CSV")],
     "archive": ("index.html", "All scorecards"),
     "build": "python -m recon.kpi --month 2026-09, then python -m reports.monthly --month 2026-09"},
    {"title": "Month-end close", "what": "Business Central import files, reconciliation and exceptions.",
     "folder": "close", "pattern": r"\d{4}-\d{2}", "period": _month,
     "extras": lambda s: [(f"{s}/general_journal_{s}.csv", "General Journal"), (f"{s}/ar_invoice_{s}.csv", "AR invoice"),
                          (f"{s}/control_totals_{s}.csv", "Control totals"), (f"{s}/exceptions_{s}.csv", "Exceptions")],
     "archive": None,
     "build": "python -m reports.reconcile ..., reports.bc_export, reports.close_report --month 2026-09"},
]


def headline(page):
    """The page's summary sentence and whether it is flagged (missing data, partial totals)."""
    m = re.search(r'<p class="summary( alert)?">(.*?)</p>', page.read_text(encoding="utf-8"), re.S)
    if not m:
        return "", False
    return unescape(re.sub(r"<[^>]+>", "", m[2])).strip(), bool(m[1])


def card(root, item):
    folder = root / item["folder"]
    pages = sorted(f for f in folder.glob("*.html") if re.fullmatch(item["pattern"], f.stem)) if folder.is_dir() else []
    if not pages:
        return (f'<div class="hub-card empty"><div class="label">{item["title"]}</div>'
                f'<h2>Not built yet</h2><p class="links">Build it with <code>{escape(item["build"])}</code></p></div>'), False
    latest = pages[-1]
    text, alert = headline(latest)
    href = f'{item["folder"]}/{latest.name}'
    links = [f'<a href="{item["folder"]}/{name}">{label}</a>' for name, label in item["extras"](latest.stem)
             if (folder / name).exists()]
    if item["archive"] and (folder / item["archive"][0]).exists():
        links.append(f'<a href="{item["folder"]}/{item["archive"][0]}">{item["archive"][1]} ({len(pages)})</a>')
    elif len(pages) > 1:
        links.append("Earlier: " + ", ".join(f'<a href="{item["folder"]}/{p.name}">{escape(item["period"](p.stem))}</a>'
                                             for p in reversed(pages[:-1])))
    built = datetime.fromtimestamp(latest.stat().st_mtime)
    mock = "mock data" in latest.read_text(encoding="utf-8")
    return (f'<div class="hub-card{" alert" if alert else ""}"><div class="label">{item["title"]}</div>'
            f'<h2><a href="{href}">{escape(item["period"](latest.stem))}</a></h2>'
            f'<p class="headline">{escape(text)}</p>'
            f'<p class="links">{" · ".join(links)}</p>'
            f'<p class="built">{escape(item["what"])} Built {built:%Y-%m-%d %H:%M}.</p></div>'), mock


def build(root=ROOT / "reports"):
    """Write <root>/index.html and return its path."""
    root = Path(root)
    cards, mock = zip(*(card(root, item) for item in SUITE))
    note = ("<p>Pages marked <strong>mock data</strong> are built from the synthetic sample exports; "
            "KPIs marked SIMULATED use simulated internal data.</p>") if any(mock) else ""
    body = (f'<header><h1>E-commerce reports</h1>'
            f'<p>Latest of each report · updated {datetime.now():%Y-%m-%d %H:%M}</p></header>'
            f'<div class="hub-grid">\n' + "\n".join(cards) + '\n</div>'
            f'<section class="foot">{note}<p>Red top rule: the report flags missing data or partial totals.</p></section>')
    path = root / "index.html"
    path.write_text(PAGE.substitute(title="E-commerce reports", css=CSS + HUB_CSS, body=body), encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT / "reports"), help="folder holding pulse/, weekly/, monthly/")
    args = ap.parse_args(argv)
    print(f"wrote {build(args.root)}")


if __name__ == "__main__":
    main()
