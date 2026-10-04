"""Portal for the reporting suite: reports/index.html links to the latest nightly pulse, weekly
dashboard, monthly COO scorecard and month-end close, with their files. Static HTML, opens from disk.

Each card shows the headline sentence of the latest page (its summary line), red when that page
flags missing data, so staff see the state of things before clicking.

    python -m reports.hub [--root reports]     # also run at the end of run_nightly, weekly and monthly
"""
import argparse
import csv
import math
import re
from datetime import date, datetime
from html import escape, unescape
from pathlib import Path

from reports import library
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
/* Revenue by night: plain HTML columns, no script. A 2px gap in the card color separates the segments. */
.trend-head { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:4px 16px; margin-top:14px; }
.trend-head h2.sec { margin:0 0 6px; }
.legend { display:flex; flex-wrap:wrap; gap:4px 16px; font-size:13px; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; }
.trend { padding:14px 16px 10px; overflow:visible; }
.plot { position:relative; margin:18px 0 0 56px; border-bottom:1px solid var(--muted); }
.tick { position:absolute; left:0; right:0; border-top:1px solid #e6e6e8; }
.tick span { position:absolute; right:100%; margin-right:8px; transform:translateY(-50%); font-size:12px;
  color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
.cols { position:absolute; inset:0; display:flex; align-items:flex-end; }
.col { flex:1; display:flex; flex-direction:column; align-items:center; text-decoration:none; }
.col .cap { font-size:12px; font-weight:600; color:var(--ink); margin-bottom:3px; white-space:nowrap; }
.seg { display:block; width:24px; }
.seg:first-of-type { border-radius:4px 4px 0 0; }
.seg + .seg { border-top:2px solid var(--card); }
.col:hover .seg { opacity:.82; }
.xlabels { display:flex; margin:6px 0 0 56px; }
.xlabels div { flex:1; text-align:center; font-size:12px; line-height:1.35; color:var(--muted); padding:0 2px; }
.xlabels b { display:block; color:var(--ink); font-weight:600; }
.xlabels .gap { display:block; color:var(--down); font-weight:600; }
.trend + .links { color:var(--muted); margin:6px 0 0; }
@media print {
  .seg, .legend i { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
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
    {"title": "Daily report · nightly pulse", "what": "Revenue and customers by marketplace for the day that just ended.",
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
    {"title": "Month-end close", "what": "Export files for Business Central, reconciliation and exceptions.",
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


# Marketplace colors for the chart, bottom of the column first. Checked as a set for color-blind
# separation on white; none is the green or red the pages use for change and missing data.
SERIES = [("ShopGoodwill", "#0054A4"), ("Amazon", "#eb6834"), ("eBay", "#1baf7a")]
PLOT_PX = 130


def nights(root, count=8):
    """The last nights from the pulse CSVs beside the pages: (date, {marketplace: dollars}, [marketplaces with no data])."""
    files = sorted(f for f in (root / "pulse").glob("*.csv") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem))
    found = []
    for f in files[-count:]:
        with open(f, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        revenue = {r["Marketplace"]: float(r["Revenue"]) for r in rows if r["Status"] == "ok" and r["Revenue"]}
        gaps = [r["Marketplace"] for r in rows if r["Status"] in ("missing", "stale", "unknown")]
        found.append((f.stem, revenue, gaps))
    return found


def _axis(top):
    """A round step for about three gridlines, and the axis maximum (a whole number of steps)."""
    raw = max(top, 1) / 3
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    return step, step * math.ceil(max(top, 1) / step)


def trend(root):
    """Revenue by night and marketplace, as stacked columns. A marketplace with no data is named under its night,
    never drawn as zero. Each column links to that night's pulse."""
    days = nights(root)
    if len(days) < 2:
        return ""
    totals = [sum(rev.get(name, 0) for name, _ in SERIES) for _, rev, _ in days]
    step, top = _axis(max(totals))
    ticks = "".join(f'<div class="tick" style="bottom:{PLOT_PX * v / top:.0f}px"><span>${v:,.0f}</span></div>'
                    for v in (step * i for i in range(1, round(top / step) + 1)))
    labelled = {len(days) - 1, totals.index(max(totals))}  # the latest night and the best one; the axis reads the rest
    cols, labels = [], []
    for i, ((day, rev, gaps), total) in enumerate(zip(days, totals)):
        d = date.fromisoformat(day)
        when = f"{d:%a}, {d:%b} {d.day}"
        segs = "".join(f'<i class="seg" style="height:{PLOT_PX * rev[name] / top:.1f}px;background:{color}" '
                       f'title="{when} · {name}: ${rev[name]:,.2f}"></i>'
                       for name, color in reversed(SERIES) if rev.get(name))
        cap = f'<span class="cap">${total:,.0f}</span>' if i in labelled else ""
        note = f" (no data: {', '.join(gaps)})" if gaps else ""
        cols.append(f'<a class="col" href="pulse/{day}.html" title="{when}: ${total:,.2f}{escape(note)}">{cap}{segs}</a>')
        gap = f'<span class="gap">No data: {escape(", ".join(gaps))}</span>' if gaps else ""
        labels.append(f'<div><b>{d:%a}</b>{d:%b} {d.day}{gap}</div>')
    legend = "".join(f'<span><i style="background:{color}"></i>{name}</span>' for name, color in SERIES)
    return (f'<div class="trend-head"><h2 class="sec">Revenue by night · last {len(days)} nights</h2>'
            f'<div class="legend">{legend}</div></div>'
            f'<div class="card trend"><div class="plot" style="height:{PLOT_PX}px">{ticks}'
            f'<div class="cols">{"".join(cols)}</div></div><div class="xlabels">{"".join(labels)}</div></div>'
            f'<p class="links">Revenue as on the nightly pulse: sales minus refunds, before marketplace fees. '
            f'A night with a missing file shows only the marketplaces that reported. '
            f'Select a column for that night, or see <a href="pulse/index.html">all days</a>.</p>')


CLOSE_FILES = [("general_journal", "General Journal"), ("ar_invoice", "AR invoice"), ("control_totals", "Control totals"),
               ("exceptions", "Exceptions")]
# The close page's pill colors (reports/close_report.py): OPEN is black, INCOMPLETE and worse are red.
CLOSE_PILL = {"RECONCILED": "ok", "OPEN": "stale"}


def _rows(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _close_row(folder, month):
    """One month for the list page, from the control totals and exceptions the close copied beside its page."""
    control = _rows(folder / month / f"control_totals_{month}.csv")
    exceptions = _rows(folder / month / f"exceptions_{month}.csv")
    pills = "".join(f'<span class="pill {CLOSE_PILL.get(r["Status"], "missing")}">{escape(r["Source"])} {escape(r["Status"])}</span>'
                    for r in control) or '<span class="muted">no control totals</span>'
    review = any(r["Status"] != "RECONCILED" for r in control) or bool(exceptions)
    files = "".join(f'<a href="{month}/{key}_{month}.csv">{name}</a>' for key, name in CLOSE_FILES
                    if (folder / month / f"{key}_{month}.csv").exists())
    return {"cells": [f'<a href="{month}.html">{escape(_month(month))}</a>', pills, f"{len(exceptions)}",
                      "<strong>Not posted</strong><small>export files only</small>", files],
            "find": f'{_month(month)} {month} {" ".join(r["Source"] + " " + r["Status"] for r in control)} not posted',
            "tags": "review" if review else "clean", "exceptions": len(exceptions)}


def close_index(root):
    """<root>/close/index.html, the Month-end Close page: every month closed, newest first, with each source's
    reconciliation status, its exceptions and its export files for Business Central."""
    folder = root / "close"
    folder.mkdir(parents=True, exist_ok=True)
    months = sorted((f.stem for f in folder.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}", f.stem)), reverse=True)
    rows = [_close_row(folder, m) for m in months]
    top = library.tiles([
        ("Latest close", _month(months[0]), "the month that ended last", f"{months[0]}.html"),
        ("Exceptions to work", f'{rows[0]["exceptions"]}', f"in {_month(months[0])}", f"{months[0]}.html"),
        ("Posting status", "Not posted", "export files for Business Central; nothing is sent", None)]) if months else ""
    table = library.finder_table(
        [("Month", "l"), ("Reconciliation by source", "l"), ("Exceptions", "num"), ("Posting", "l"), ("Export files", "files")],
        [("", rows)], [("review", "Needs review"), ("clean", "Reconciled")],
        'Find a month: "September", "2026-09", "incomplete"', noun="close")
    body = (f'<header><h1>Month-end Close</h1><p>Goodwill Michiana e-commerce · {len(months)} month(s) · '
            f'export files for Business Central, not posted</p></header>{top}{table}')
    css = CSS + library.LIBRARY_CSS + ".pill.stale { background:var(--ink); color:#fff; }"
    (folder / "index.html").write_text(PAGE.substitute(title="Month-end Close", css=css, body=body), encoding="utf-8")


def build(root=ROOT / "reports"):
    """Write <root>/index.html (and the close's list of months) and return the portal's path."""
    root = Path(root)
    cards = [card(root, item) for item in SUITE]
    close_index(root)
    body = (f'<header><h1>Latest reports</h1>'
            f'<p>Goodwill Michiana e-commerce · updated {stamp(datetime.now().isoformat())}</p></header>'
            f'{trend(root)}'
            f'<div class="hub-grid">\n' + "\n".join(cards) + '\n</div>'
            f'<p class="simnote"><strong>{DATA_LABEL}.</strong> Every figure on these pages comes from synthetic sample '
            f'files and simulated APIs: {DATA_NOTE}. KPIs marked "Simulated internal data" use a mock of Goodwill\'s '
            f'internal systems. The month-end close writes export files for Business Central: nothing is posted.</p>'
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
