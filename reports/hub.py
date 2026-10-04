"""Portal for the reporting suite: reports/index.html links to the latest nightly pulse, weekly and
monthly COO scorecards and month-end close, with their files. Static HTML, opens from disk.

Each card shows the headline sentence of the latest page (its summary line), red when that page
flags missing data, so staff see the state of things before clicking. Under the cards, the nightly
store (Victor's SQLite database, read by reports.store_view): days loaded, partial days, runs and
the daily revenue trend as stored. Building the portal also refreshes the scorecard pages' period
switch and download links (reports.scorecard.refresh), since PDF and CSV exports land after the page.

    python -m reports.hub [--root reports]     # also run at the end of run_nightly, weekly and monthly
"""
import argparse
import json
import re
from datetime import date, datetime
from html import escape, unescape
from pathlib import Path

from reports import scorecard, store_view
from reports.pulse import money
from reports.theme import CSS, PAGE, accordion, info, print_notes, span, stamp

ROOT = Path(__file__).resolve().parent.parent

HUB_CSS = """
/* One card per report: what it is (info button), the latest period, its headline, its files */
.hub-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:var(--sp-3); }
.hub-card { display:flex; flex-direction:column; gap:var(--sp-2); padding:var(--sp-5); background:var(--card);
  border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); }
.hub-card.empty { background:transparent; box-shadow:none; border-style:dashed; border-color:var(--line-2); }
.hub-card .label { display:flex; align-items:center; gap:6px; }
.hub-card .label::before { content:""; width:8px; height:8px; border-radius:50%; background:var(--ok); }
.hub-card.alert .label::before { background:var(--bad); }
.hub-card.empty .label::before { background:var(--faint); }
.hub-card h2 { font-size:22px; font-weight:var(--fw-bold); line-height:1.2; letter-spacing:-0.025em; }
.hub-card h2 a { color:var(--ink); }
.hub-card .headline { font-size:13px; line-height:1.45; color:var(--muted); }
.hub-card .links { display:flex; flex-wrap:wrap; gap:6px; margin-top:auto; padding-top:var(--sp-2); }
.hub-card .links a { padding:3px 10px; border-radius:980px; background:var(--neutral-bg); color:var(--ink); font-size:var(--fs-small); }
.hub-card .links a:hover { background:var(--accent-tint); text-decoration:none; }
.hub-card .built { font-size:var(--fs-small); color:var(--faint); }
.hub-card code { font-size:11px; color:var(--muted); }

/* The nightly store: facts, the daily revenue trend, recent runs */
.store { margin-top:var(--sp-3); padding:var(--sp-5); background:var(--card); border:1px solid var(--line);
  border-radius:var(--radius); box-shadow:var(--shadow); }
.store-hd { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:var(--sp-1) var(--sp-4); }
.store-hd h2 { font-size:20px; font-weight:var(--fw-semi); letter-spacing:-0.02em; }
.store .facts { margin-top:var(--sp-3); padding:0; border:0; box-shadow:none; }
.store .facts > div:first-child { padding-left:0; }
.trend { margin-top:var(--sp-5); }
.trend-hd { display:flex; flex-wrap:wrap; justify-content:space-between; gap:var(--sp-1) var(--sp-4); font-size:var(--fs-small); color:var(--muted); }
.trend-hd b { color:var(--ink); font-weight:var(--fw-semi); }
.key { display:inline-block; width:8px; height:8px; margin:0 5px 0 0; border-radius:2px; }
.trend svg { display:block; width:100%; height:138px; margin-top:var(--sp-2); overflow:visible; }
.trend .bar { fill:var(--accent); }
.trend .bar.partial { fill:var(--bad); }
.trend .hit { fill:transparent; }
.trend g:hover .bar { opacity:.75; }
.trend .base { stroke:var(--line-2); stroke-width:1; vector-effect:non-scaling-stroke; }
.trend .ax { fill:var(--faint); font-size:11px; }
.store details.acc { box-shadow:none; border:0; margin-top:var(--sp-3); }
.store details.acc > summary { padding-left:0; padding-right:0; }
.store details.acc > summary:hover { background:none; }
.store .acc-body { padding:0; }
@media print {
  @page { size:letter portrait; margin:0.5in; }
  .store { margin-top:6pt; padding:6pt 8pt; box-shadow:none; border-color:#d2d2d7; border-radius:8px; break-inside:avoid; }
  .store-hd h2 { font-size:10pt; }
  .store .facts { margin-top:3pt; }
  .trend { margin-top:4pt; }
  .trend-hd { font-size:7pt; }
  .trend svg { height:60pt; margin-top:2pt; }
  .trend .ax { font-size:7pt; }
  .hub-grid { grid-template-columns:repeat(2,1fr); gap:6pt; }
  .hub-card { padding:6pt 8pt; gap:3pt; box-shadow:none; border-color:#d2d2d7; border-radius:8px; break-inside:avoid; }
  .hub-card h2 { font-size:11pt; }
  .hub-card .headline { font-size:7.5pt; }
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
    {"title": "Weekly scorecard", "what": "Goodwill's 15 KPIs for the ISO week, from the week's KPI file.",
     "folder": "scorecard", "pattern": r"week-\d{4}-W\d{2}", "period": lambda s: _week(s[5:]),
     "extras": lambda s: [(f"{s}.pdf", "PDF"), (f"../weekly/{s[5:]}.csv", "CSV"), (f"{s}.json", "KPI file")],
     "archive": ("index.html", "All weeks"),
     "build": "python -m reports.weekly --week 2026-W40"},
    {"title": "COO scorecard (monthly)", "what": "Goodwill's 15 KPIs in five areas, from the month's KPI file.",
     "folder": "scorecard", "pattern": r"month-\d{4}-\d{2}", "period": lambda s: _month(s[6:]),
     "extras": lambda s: [(f"{s}.pdf", "PDF"), (f"{s}.csv", "CSV"), (f"{s}.json", "KPI file"),
                          (f"../monthly/{s[6:]}.csv", "Daily CSV")],
     "archive": ("index.html", "All months"),
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


def complete(page):
    """False for a scorecard whose KPI file covers only part of its period (a month to date), so the card
    shows the last finished week or month; other pages count as complete."""
    copy = page.with_suffix(".json")
    if not copy.exists():
        return True
    period = json.loads(copy.read_text(encoding="utf-8")).get("period") or {}
    return period.get("through", "") >= period.get("end", "")


def card(root, item):
    folder = root / item["folder"]
    pages = sorted(f for f in folder.glob("*.html") if re.fullmatch(item["pattern"], f.stem)) if folder.is_dir() else []
    tip_id = f'tip-{item["folder"]}'
    about = info(tip_id, item["title"], [("What it is", escape(item["what"])), ("Rebuild", f'<code>{escape(item["build"])}</code>')])
    if not pages:
        return (f'<div class="hub-card empty"><div class="label has-tip">{item["title"]}{about}</div>'
                f'<h2>Not built yet</h2><p class="built">Build it with <code>{escape(item["build"])}</code></p></div>'), False
    latest = next((p for p in reversed(pages) if complete(p)), pages[-1])
    text, alert = headline(latest)
    href = f'{item["folder"]}/{latest.name}'
    links = [f'<a href="{item["folder"]}/{name}">{label}</a>' for name, label in item["extras"](latest.stem)
             if (folder / name).exists()]
    if item["archive"] and (folder / item["archive"][0]).exists():
        links.append(f'<a href="{item["folder"]}/{item["archive"][0]}">{item["archive"][1]} ({len(pages)})</a>')
    elif len(pages) > 1:
        links += [f'<a href="{item["folder"]}/{p.name}">{escape(item["period"](p.stem))}</a>' for p in reversed(pages[:-1])]
    built = datetime.fromtimestamp(latest.stat().st_mtime)
    mock = "mock data" in latest.read_text(encoding="utf-8")
    return (f'<div class="hub-card{" alert" if alert else ""}"><div class="label has-tip">{item["title"]}{about}</div>'
            f'<h2><a href="{href}">{escape(item["period"](latest.stem))}</a></h2>'
            f'<p class="headline">{escape(text)}</p>'
            f'<p class="links">{"".join(links)}</p>'
            f'<p class="built">Built {built:%b} {built.day}, {built:%H:%M}</p></div>'), mock


def trend_svg(trend):
    """Daily revenue as stored (v_daily: the marketplaces that were ok), one bar per day; a partial day
    is drawn in the alert colour and named in the header. Hover a bar for its date and amount."""
    days = [t for t in trend if t["revenue_cents"] is not None]
    if not days:
        return ""
    w, h, gap = 700, 120, 2
    top = max(t["revenue_cents"] for t in days) or 1
    bw = (w - gap * (len(trend) - 1)) / len(trend)
    bars = []
    for i, t in enumerate(trend):
        if t["revenue_cents"] is None:
            continue
        x, bh = i * (bw + gap), max(t["revenue_cents"] / top * (h - 4), 1)
        y, r = h - bh, min(4, bw / 2, bh)
        tip = f'{span(t["date"], t["date"])}: {money(t["revenue_cents"])}'
        tip += " (partial: a marketplace had no data)" if t["partial"] else ""
        bars.append(f'<g><title>{escape(tip)}</title><rect class="hit" x="{x:.1f}" y="0" width="{bw + gap:.1f}" height="{h}"/>'
                    f'<path class="bar{" partial" if t["partial"] else ""}" d="M{x:.1f},{h}V{y + r:.1f}'
                    f'Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f}H{x + bw - r:.1f}Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f}V{h}Z"/></g>')
    first, last = trend[0]["date"], trend[-1]["date"]
    label = f"Daily revenue, {span(first, last)}; highest day {money(top)}"
    return (f'<svg viewBox="0 0 {w} {h + 18}" role="img" aria-label="{escape(label)}" preserveAspectRatio="none">'
            + "".join(bars) + f'<line class="base" x1="0" x2="{w}" y1="{h + .5}" y2="{h + .5}"/></svg>'
            f'<div class="trend-hd"><span>{escape(span(first, first))}</span><span>{escape(span(last, last))}</span></div>')


def store_html(s):
    """The nightly store card: what is loaded, what is simulated, the trend, the last runs."""
    if s is None:
        return ('<div class="store"><div class="store-hd"><h2>Nightly store</h2><span class="muted">Not built yet: '
                '<code>python -m engine.store backfill --inbox data/sample/clean_month/inbox --from 2026-09-01 '
                '--to 2026-09-30</code></span></div></div>')
    simulated = s["internal_sources"] == ["mock"]
    internal = (f'{s["internal_days"]} days' + (' <span class="pill warn">Simulated</span>' if simulated else "")
                if s["internal_days"] else "None")
    periods = " · ".join(f'{s["kpi_periods"][t]} {t}{"s" if s["kpi_periods"][t] != 1 else ""}'
                         for t in ("day", "week", "month") if s["kpi_periods"].get(t))
    partial = len(s["partial"])
    loaded = f'{s["days"]}' + (f' <span class="muted">{escape(span(s["first"], s["last"]))}</span>' if s["days"] else "")
    facts_html = "".join(f"<div><dt>{name}</dt><dd{cls}>{value}</dd></div>" for name, value, cls in [
        ("Days loaded", loaded, ""),
        ("Complete days", f'{s["days"] - partial} of {s["days"]}', ' class="bad"' if partial else ' class="good"'),
        ("Transactions", f'{s["transactions"]:,}', ""),
        ("Internal data", internal, ""),
        ("KPI history", periods or "None", ""),
        ("Failed runs", f'{s["failed_runs"]}', ' class="bad"' if s["failed_runs"] else ""),
    ])
    trend, chart = s["trend"], ""
    if trend:
        flagged = [t["date"] for t in trend if t["partial"]]
        key = (f'<span><span class="key" style="background:var(--bad)"></span>Partial day: '
               f'{escape(", ".join(span(d, d) for d in flagged))}</span>' if flagged else "")
        chart = (f'<div class="trend"><div class="trend-hd"><span><b>Daily revenue</b> · last {len(trend)} days loaded, '
                 f'marketplaces with data</span>{key}</div>{trend_svg(trend)}</div>')
    rows = "".join(f'<tr><td>{escape(r["command"])}</td><td class="l">{escape(r["date"] or r["message"])}</td>'
                   f'<td class="l">{escape(stamp(r["started"]))}</td><td>{r["rows"]:,}</td>'
                   f'<td class="status"><span class="pill {"ok" if r["result"] == "ok" else "bad"}">{escape(r["result"])}</span></td></tr>'
                   for r in s["runs"])
    runs = accordion("Recent runs", f'<div class="card"><table><thead><tr><th>Command</th><th class="l">For</th>'
                     f'<th class="l">Started</th><th>Rows</th><th class="status">Result</th></tr></thead><tbody>{rows}</tbody>'
                     f'</table></div>', f'the last {len(s["runs"])}, from the runs table') if rows else ""
    return (f'<div class="store"><div class="store-hd"><h2>Nightly store</h2><span class="muted">SQLite '
            f'<code>{escape(s["path"].name)}</code>, what the pages and KPIs are built from</span></div>'
            f'<dl class="facts">{facts_html}</dl>{chart}{runs}</div>')


def build(root=ROOT / "reports", db=None):
    """Write <root>/index.html and return its path. `db` is the store (default: ECOM_DB, else out/store/ecom.db)."""
    root = Path(root)
    scorecard.refresh(root / "scorecard")
    cards, mock = zip(*(card(root, item) for item in SUITE))
    about = ("<p>Pages marked <strong>mock data</strong> are built from the synthetic sample exports; "
             "KPIs marked SIMULATED use simulated internal data.</p>" if any(mock) else "")
    about += "<p>A red dot means the report flags missing data or partial totals; green means its data is complete.</p>"
    now = datetime.now()
    body = (f'<header><h1>E-commerce reports</h1>'
            f'<p>Latest of each report · updated {now:%b} {now.day}, {now:%H:%M}</p></header>'
            f'<div class="hub-grid">\n' + "\n".join(cards) + '\n</div>'
            + store_html(store_view.summary(db))
            + accordion("About these reports", about, "mock data, status dots")
            + print_notes(["Red dot: the report flags missing data or partial totals."]))
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
