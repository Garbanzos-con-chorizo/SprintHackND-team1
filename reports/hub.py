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

from reports.pulse import CSS, DATA_LABEL, DATA_NOTE, PAGE, stamp

ROOT = Path(__file__).resolve().parent.parent

HUB_CSS = """
.hub-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(420px,100%),1fr)); gap:14px; margin:18px 0 0; }
.hub-card { background:var(--card); border:1px solid var(--line); border-left:5px solid var(--primary);
  border-radius:var(--radius); padding:16px 20px; box-shadow:var(--shadow); }
.hub-card.alert { border-left-color:var(--down); }
.hub-card.empty { border-left-color:var(--line); }
.hub-card .label { color:var(--primary); font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.hub-card h2 { font-size:22px; margin:2px 0 8px; }
.hub-card h2 a { color:var(--ink); }
.hub-card .headline { margin:0 0 10px; font-weight:600; }
.hub-card .links, .hub-card .built { font-size:14px; color:var(--muted); margin:4px 0 0; }
.hub-card .links { line-height:1.8; }
@media print {
  @page { size:letter portrait; margin:0.5in; }
  .hub-grid { grid-template-columns:repeat(2,1fr); gap:8px; }
  .hub-card { padding:8px 10px; break-inside:avoid; }
  .hub-card h2 { font-size:12pt; }
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
    {"title": "Weekly dashboard", "what": "The week's 15 KPIs in five areas, from the KPI file.",
     "folder": "scorecard", "pattern": r"week-\d{4}-W\d{2}", "period": lambda s: _week(s[5:]),
     "extras": lambda s: [(f"{s}.csv", "KPI table (CSV)"), (f"{s}.pdf", "PDF"), (f"{s}.json", "KPI file")],
     "archive": ("index.html", "All scorecards"),
     "build": "python -m recon.kpi --week 2026-W38, then python -m reports.weekly --week 2026-W38"},
    {"title": "COO scorecard (monthly)", "what": "Goodwill's 15 KPIs in five areas, from the KPI file.",
     "folder": "scorecard", "pattern": r"month-\d{4}-\d{2}", "period": lambda s: _month(s[6:]),
     "extras": lambda s: [(f"{s}.csv", "KPI table (CSV)"), (f"{s}.pdf", "PDF"), (f"{s}.json", "KPI file"),
                          (f"../monthly/{s[6:]}.csv", "Daily CSV"),
                          (f"../monthly/index.html?month={s[6:]}", "Daily table", f"../monthly/{s[6:]}.json")],
     "archive": ("index.html", "All scorecards"),
     "switch": [("day", "Day"), ("week", "Week to date"), ("month", "Month to date")],
     "previous": "Previous month",
     "build": "python -m recon.kpi --month 2026-09, then python -m reports.monthly --month 2026-09"},
    {"title": "Month-end close", "what": "Business Central import files, reconciliation and exceptions.",
     "folder": "close", "pattern": r"\d{4}-\d{2}", "period": _month,
     "extras": lambda s: [(f"{s}/general_journal_{s}.csv", "General Journal"), (f"{s}/ar_invoice_{s}.csv", "AR invoice"),
                          (f"{s}/control_totals_{s}.csv", "Control totals"), (f"{s}/exceptions_{s}.csv", "Exceptions"),
                          (f"{s}/close_status_{s}.json", "Run status"), (f"{s}/runs.csv", "Run history")],
     "archive": None,
     "build": "python -m reports.close --inbox data/sample/messy_month/inbox --month 2026-09"},
]


def headline(page):
    """The page's summary sentence and whether it is flagged (missing data, partial totals)."""
    m = re.search(r'<p class="summary( alert)?">(.*?)</p>', page.read_text(encoding="utf-8"), re.S)
    if not m:
        return "", False
    return unescape(re.sub(r"<[^>]+>", "", m[2])).strip(), bool(m[1])


def _period_link(item, folder, kind, label):
    """The newest page of one period type (day, week or month) for the portal's period switch."""
    found = sorted(f for f in folder.glob(f"{kind}-*.html") if re.fullmatch(rf"{kind}-[\dW-]+", f.stem))
    if not found:
        return f'<span class="muted">{label} (not built)</span>'
    return f'<a href="{item["folder"]}/{found[-1].name}">{label}</a>'


def card(root, item):
    folder = root / item["folder"]
    pages = sorted(f for f in folder.glob("*.html") if re.fullmatch(item["pattern"], f.stem)) if folder.is_dir() else []
    if not pages:
        return (f'<div class="hub-card empty"><div class="label">{item["title"]}</div>'
                f'<h2>Not built yet</h2><p class="links">Build it with <code>{escape(item["build"])}</code></p></div>')
    latest = pages[-1]
    text, alert = headline(latest)
    href = f'{item["folder"]}/{latest.name}'
    # An extra is (file, label) or (link, label, the file that must exist for the link to work).
    links = [f'<a href="{item["folder"]}/{name}">{label}</a>' for name, label, *needs in item["extras"](latest.stem)
             if (folder / (needs[0] if needs else name)).exists()]
    if item["archive"] and (folder / item["archive"][0]).exists():
        links.append(f'<a href="{item["folder"]}/{item["archive"][0]}">{item["archive"][1]} ({len(pages)})</a>')
    elif len(pages) > 1:
        links.append("Earlier: " + ", ".join(f'<a href="{item["folder"]}/{p.name}">{escape(item["period"](p.stem))}</a>'
                                             for p in reversed(pages[:-1])))
    if item.get("previous") and len(pages) > 1:
        before = pages[-2]
        links.insert(0, f'{item["previous"]}: <a href="{item["folder"]}/{before.name}">{escape(item["period"](before.stem))}</a>')
    if item.get("switch"):
        links.insert(0, "Period: " + " · ".join(_period_link(item, folder, kind, label) for kind, label in item["switch"]))
    built = datetime.fromtimestamp(latest.stat().st_mtime)
    return (f'<div class="hub-card{" alert" if alert else ""}"><div class="label">{item["title"]}</div>'
            f'<h2><a href="{href}">{escape(item["period"](latest.stem))}</a></h2>'
            f'<p class="headline">{escape(text)}</p>'
            f'<p class="links">{" · ".join(links)}</p>'
            f'<p class="built">{escape(item["what"])} Built {stamp(built.isoformat())}.</p></div>')


def close_index(root):
    """<root>/close/index.html, the months closed (newest first): where the top bar's "Month-end close" lands."""
    folder = root / "close"
    folder.mkdir(parents=True, exist_ok=True)
    months = sorted((f.stem for f in folder.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}", f.stem)), reverse=True)
    items = "\n".join(f'  <li><a href="{m}.html">{escape(_month(m))}{" <span class=\"muted\">(latest)</span>" if i == 0 else ""}'
                      f'</a></li>' for i, m in enumerate(months))
    body = (f'<header><h1>Month-end close</h1><p>Goodwill Michiana e-commerce · {len(months)} month(s) · '
            f'Business Central import files, not posted</p></header>'
            f'<ul class="days">\n{items or '  <li><a class="muted">None yet</a></li>'}\n</ul>')
    (folder / "index.html").write_text(PAGE.substitute(title="Month-end close", css=CSS, body=body), encoding="utf-8")


def build(root=ROOT / "reports"):
    """Write <root>/index.html (and the close's list of months) and return the portal's path."""
    root = Path(root)
    cards = [card(root, item) for item in SUITE]
    close_index(root)
    body = (f'<header><h1>Latest reports</h1>'
            f'<p>Goodwill Michiana e-commerce · updated {stamp(datetime.now().isoformat())}</p></header>'
            f'<div class="hub-grid">\n' + "\n".join(cards) + '\n</div>'
            f'<p class="simnote"><strong>{DATA_LABEL}.</strong> Every figure on these pages comes from synthetic sample '
            f'files and simulated APIs: {DATA_NOTE}. KPIs marked "Simulated internal data" use a mock of Goodwill\'s '
            f'internal systems. The month-end close writes Business Central import files: nothing is posted.</p>'
            f'<section class="foot"><p>Red edge: the report flags missing data or partial totals.</p></section>')
    path = root / "index.html"
    path.write_text(PAGE.substitute(title="E-commerce reports", css=CSS + HUB_CSS, body=body, root=""), encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT / "reports"), help="folder holding pulse/, weekly/, monthly/")
    args = ap.parse_args(argv)
    print(f"wrote {build(args.root)}")


if __name__ == "__main__":
    main()
