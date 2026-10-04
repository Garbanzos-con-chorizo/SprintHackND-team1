"""Portal for the reporting suite: reports/index.html links to the latest nightly pulse, weekly
dashboard and monthly COO scorecard, with their CSVs and archives. Static HTML, opens from disk.

Each card shows the headline sentence of the latest page (its summary line), red when that page
flags missing data, so staff see the state of things before clicking.

    python -m reports.hub [--root reports]     # also run at the end of run_nightly, weekly and monthly
"""
import argparse
import re
from datetime import date, datetime
from html import escape, unescape
from pathlib import Path

from reports.pulse import CSS, PAGE

ROOT = Path(__file__).resolve().parent.parent

HUB_CSS = """
.hub-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; margin:18px 0 0; }
.hub-card { background:var(--card); border:1px solid var(--line); border-left:5px solid var(--primary);
  border-radius:10px; padding:16px 18px; }
.hub-card.alert { border-left-color:var(--down); }
.hub-card.empty { border-left-color:var(--line); }
.hub-card .label { color:var(--primary); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.hub-card h2 { font-size:19px; margin:4px 0 8px; }
.hub-card h2 a { color:var(--ink); }
.hub-card .headline { margin:0 0 10px; font-weight:600; }
.hub-card .links, .hub-card .built { font-size:13px; color:var(--muted); margin:4px 0 0; }
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
    {"title": "Monthly COO scorecard", "what": "The month's totals and the five KPI groups.",
     "folder": "monthly", "pattern": r"\d{4}-\d{2}-scorecard", "period": _month,
     "extras": lambda s: [(f"{s[:7]}-kpis.csv", "KPI CSV"), (f"{s[:7]}.csv", "Daily CSV")],
     "archive": None,
     "build": "python -m reports.monthly --month 2026-09"},
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
            "numbers with a yellow badge are simulated internal data.</p>") if any(mock) else ""
    body = (f'<header><h1>Goodwill Michiana e-commerce reports</h1>'
            f'<p>Latest reports · updated {datetime.now():%Y-%m-%d %H:%M} · static pages, open from this folder</p></header>'
            f'<div class="hub-grid">\n' + "\n".join(cards) + '\n</div>'
            f'<section class="foot">{note}<p>A red edge means that report flags missing data or partial totals.</p></section>')
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
