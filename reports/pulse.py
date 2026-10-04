"""Render the nightly pulse JSON as an HTML page with a one-line summary (tasks P-O2, P-O3).

Reads out/pulse/<date>.json (shape: docs/pitch/gemini/pulse_proposal.md) and writes
reports/pulse/<date>.html, <date>.csv (same layout as the monthly CSV,
see reports/schema.py), <date>.email.html (inline styles for Outlook), <date>.xlsx (every table of the
day in one Excel file, reports/day_workbook.py) and index.html.
Standard library only, except the Excel file (openpyxl, already an engine dependency).

    python -m reports.pulse --date 2026-10-02 [--src out/pulse] [--dest reports/pulse]
"""
import argparse
import csv
import json
import re
from datetime import date, datetime
from html import escape, unescape
from pathlib import Path
from string import Template

from reports import a11y, library
from reports.schema import day_record, write_csv

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["shopgoodwill", "amazon", "ebay", "other"]
LABELS = {"shopgoodwill": "ShopGoodwill", "amazon": "Amazon", "ebay": "eBay", "other": "Other"}
# Statuses and delta reasons from docs/contracts/pulse.md (schema_version 1).
NO_DATA = {
    "missing": "No data: file not received",
    "stale": "No data: file received, but no orders for this day",
    "unknown": "No data: file status unknown",
    "not_configured": "Not tracked yet",
}
PILL = {"ok": "OK", "missing": "Missing", "stale": "Stale", "unknown": "Unknown", "not_configured": "Not tracked"}
BY_ORDER = "Counted by order: this marketplace's export has no unique buyer id"
REASONS = {
    "current_not_ok": "no data today",
    "prior_unavailable": "no data for the prior day",
    "coverage_changed": "not comparable: different marketplaces reported each day",
    "prior_zero": "prior day revenue was $0",
}

# Goodwill palette: blue #0054A4 and black #231F20 on white. Greys are tints of the black.
# Green and red mark change and missing data only; green is too light for text on white
# (about 2:1), so it is a badge background under black text; red passes as text (about 5.6:1).
CSS = """
:root { --primary:#0054A4; --ink:#231F20; --bg:#f5f6f8; --card:#fff; --up:#9DBB68; --down:#CC1F40;
  --muted:#5c5859; --line:#d3d2d2; --nodata:#eff0f2; --radius:6px; --page:1100px;
  --shadow:0 1px 2px rgba(35,31,32,.07); }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif; }
/* The bar every page shares: where you are in the suite, and what the data is. */
.topbar { background:var(--primary); color:#fff; }
.topbar-in { max-width:var(--page); margin:0 auto; padding:10px 16px; display:flex; flex-wrap:wrap;
  align-items:center; gap:6px 22px; }
.topbar .brand { color:#fff; font-weight:700; text-decoration:none; margin-right:auto; }
.topbar nav { display:flex; flex-wrap:wrap; gap:4px 18px; }
.topbar nav a { color:#fff; text-decoration:none; font-size:14px; padding:3px 0; border-bottom:2px solid transparent; }
.topbar nav a:hover, .topbar nav a.here { border-bottom-color:#fff; }
.topbar nav a.here { font-weight:700; }
.datalabel { background:#fff; color:var(--ink); font-size:12px; font-weight:700; letter-spacing:.04em;
  text-transform:uppercase; padding:3px 10px; border-radius:999px; white-space:nowrap; }
main { max-width:var(--page); margin:0 auto; padding:20px 16px 32px; }
header h1 { margin:0; font-size:26px; line-height:1.2; }
header p { margin:4px 0 0; font-size:14px; color:var(--muted); }
.summary { background:var(--card); border:1px solid var(--line); border-left:5px solid var(--primary);
  border-radius:var(--radius); padding:12px 16px; margin:16px 0 0; font-size:18px; font-weight:600;
  box-shadow:var(--shadow); }
.summary.alert { border-left-color:var(--down); }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:16px 0; }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px;
  box-shadow:var(--shadow); }
.kpi .label { color:var(--primary); font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.kpi .value { font-size:26px; font-weight:700; margin-top:2px; font-variant-numeric:tabular-nums; }
.kpi .sub { font-size:14px; margin-top:4px; }
.banner { background:var(--card); border:1px solid var(--line); border-left:5px solid var(--down); border-radius:var(--radius);
  padding:10px 14px; margin:0 0 16px; font-size:15px; box-shadow:var(--shadow); }
.card { background:var(--card); border:1px solid var(--line); border-radius:var(--radius); overflow-x:auto;
  box-shadow:var(--shadow); }
table { width:100%; border-collapse:collapse; min-width:720px; font-size:15px; }
th, td { padding:10px 12px; text-align:right; border-bottom:1px solid var(--line);
  font-variant-numeric:tabular-nums; white-space:nowrap; }
th { font-size:13px; color:var(--primary); font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
tbody tr:last-child td { border-bottom:none; }
th:first-child, td:first-child, td.status, th.status { text-align:left; }
tr.total td { font-weight:700; border-top:2px solid var(--primary); border-bottom:none; }
td.nodata { text-align:left; background:var(--nodata); color:var(--down); font-weight:600; }
td.nodata.quiet { color:var(--muted); font-weight:400; font-style:italic; }
.pill { display:inline-block; font-size:12px; font-weight:700; padding:2px 9px; border-radius:var(--radius); }
.pill.ok { background:var(--up); color:var(--ink); }
.pill.missing, .pill.stale, .pill.unknown { background:var(--down); color:#fff; }
.pill.not_configured { border:1px solid var(--line); color:var(--muted); }
.chg { display:inline-block; padding:1px 8px; border-radius:var(--radius); font-weight:600; }
.chg.up { background:var(--up); color:var(--ink); }
.chg.down { background:var(--down); color:#fff; }
.muted { color:var(--muted); }
small.note { display:block; color:var(--muted); font-size:13px; font-weight:400; white-space:normal;
  max-width:220px; margin-left:auto; margin-top:2px; }
h2.sec, section.foot h2 { font-size:13px; color:var(--primary); text-transform:uppercase; letter-spacing:.05em;
  margin:20px 0 6px; }
section.foot { margin-top:20px; font-size:14px; color:var(--muted); }
/* What is simulated or synthetic on a page: the same dashed box everywhere. */
.simnote { margin:12px 0 0; font-size:13px; border:1px dashed var(--ink); padding:8px 12px; border-radius:var(--radius); }
.nav, .links, .downloads { font-size:14px; }
dl { display:grid; grid-template-columns:max-content 1fr; gap:4px 16px; margin:0; }
dt { font-weight:600; color:var(--ink); }
dd { margin:0; }
a { color:var(--primary); }
ul.days { list-style:none; padding:0; margin:12px 0 16px; }
ul.days li { background:var(--card); border:1px solid var(--line); border-radius:var(--radius); margin-bottom:8px;
  box-shadow:var(--shadow); }
ul.days a { display:block; padding:12px 16px; text-decoration:none; font-weight:600; }
.chg, .pill { border:1px solid transparent; }
/* Buttons, the same on every page; .dl is a file to download. */
.btn { display:inline-block; font:inherit; font-size:15px; font-weight:600; line-height:1.3; padding:8px 14px;
  border-radius:var(--radius); cursor:pointer; text-decoration:none; border:1px solid var(--primary);
  background:var(--primary); color:#fff; }
.btn:hover { background:#00468a; }
.btn.quiet { background:var(--card); color:var(--primary); }
.btn.quiet:hover { background:#eaf1f9; }
.btn.small { font-size:13px; padding:4px 10px; }
.btn.dl::before { content:"↓"; font-weight:700; margin-right:6px; }
.btn:disabled { opacity:.5; cursor:default; }
.btn:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
.actions { display:flex; flex-wrap:wrap; align-items:center; gap:8px 10px; margin:16px 0 0; }
/* The asterisk after a label or a figure, and the notes it opens at the bottom of the page. */
a.ast { color:var(--primary); font-weight:700; text-decoration:none; padding:0 1px 0 2px; cursor:help; }
details.notes { margin:24px 0 0; background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  font-size:14px; color:var(--muted); }
details.notes > summary { cursor:pointer; padding:10px 14px; font-weight:700; color:var(--primary); }
details.notes > .in { padding:0 14px 12px; }
details.notes h3 { font-size:13px; color:var(--primary); text-transform:uppercase; letter-spacing:.05em; margin:14px 0 4px; }
details.notes p { margin:6px 0; }
details.notes ul { margin:6px 0; padding-left:20px; }
.pagefoot { width:calc(100% - 32px); max-width:calc(var(--page) - 32px); margin:0 auto; padding:14px 0 28px;
  border-top:1px solid var(--line);
  font-size:13px; color:var(--muted); }
@media print {
  @page { size:letter; margin:0.5in; }
  body { background:#fff; font-size:10.5pt; }
  main { max-width:none; padding:0; }
  /* The bar prints as one line: the name and the data label, no links. */
  .topbar { background:none; color:var(--ink); border-bottom:1px solid var(--ink); margin-bottom:6px; }
  .topbar-in { max-width:none; padding:0 0 3px; }
  .topbar .brand { color:var(--ink); font-size:8pt; }
  .topbar nav, .pagefoot, .actions { display:none; }
  .datalabel { border:1px solid var(--ink); font-size:6.5pt; padding:0 6px; }
  header h1 { font-size:15pt; }
  .summary, .kpi, .card, .banner, ul.days li { box-shadow:none; }
  /* Keep brand colors when the browser allows it... */
  .summary, .pill, .chg, .banner, td.nodata { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  /* ...and borders that still read correctly if backgrounds are dropped. */
  .chg.up, .pill.ok { border-color:var(--ink); }
  .chg.down, .pill.missing, .pill.stale, .pill.unknown { border-color:var(--down); }
  .kpi, .card, .summary, .banner { border-color:var(--muted); }
  .card { overflow:visible; }
  table { min-width:0; font-size:9.5pt; }
  th, td { padding:6px 8px; }
  .kpis { grid-template-columns:repeat(4,1fr); }
  header, .summary, .kpis, .kpi, .banner, tr, dl { break-inside:avoid; }
  thead { display:table-header-group; }
  section.foot h2 { break-after:avoid; }
  .nav { display:none; }
}
"""

# Motion, from the report-design skill (o/ui-map): modest and honest. Blocks rise in once, cards that
# lead somewhere lift on hover, controls answer a press, pop-outs and opened details settle in, the
# portal's bars grow from the baseline, the charts' slices sweep in and their lines draw. Mostly transform
# and opacity move (plus colour and shadow on hover, the pie's stroke, the line's clip); numbers never animate, so a screenshot or PDF can't catch a wrong value. Everything stops for
# prefers-reduced-motion and in print.
MOTION_CSS = """
:root { --ease-out:cubic-bezier(.2,.8,.2,1); --t-press:120ms; --t-hover:200ms; --t-reveal:220ms; --t-enter:520ms;
  --lift:0 10px 26px rgba(35,31,32,.12); }
main > *, .kpis > *, .hub-grid > *, .areas > * { animation:rise var(--t-enter) var(--ease-out) both; }
main > :nth-child(2), .kpis > :nth-child(2), .hub-grid > :nth-child(2), .areas > :nth-child(2) { animation-delay:50ms; }
main > :nth-child(3), .kpis > :nth-child(3), .hub-grid > :nth-child(3), .areas > :nth-child(3) { animation-delay:100ms; }
main > :nth-child(4), .kpis > :nth-child(4), .hub-grid > :nth-child(4), .areas > :nth-child(4) { animation-delay:150ms; }
main > :nth-child(5), .hub-grid > :nth-child(5), .areas > :nth-child(5) { animation-delay:200ms; }
main > :nth-child(n+6) { animation-delay:250ms; }
@keyframes rise { from { opacity:0; transform:translateY(10px); } }

.hub-card, ul.days li, .kpi, .tile, .summary { transition:transform var(--t-hover) var(--ease-out), box-shadow var(--t-hover) var(--ease-out); }
.hub-card:hover, ul.days li:hover { transform:translateY(-2px); box-shadow:var(--lift); }
.kpi:hover, .tile:hover { box-shadow:0 6px 18px rgba(35,31,32,.09); }
ul.days a { transition:color var(--t-hover) var(--ease-out); }
.topbar nav a { transition:border-color var(--t-hover) var(--ease-out); }
.topbar .brand { transition:opacity var(--t-hover) var(--ease-out); }
.topbar .brand:hover { opacity:.85; }
tbody > tr > td { transition:background-color var(--t-hover) var(--ease-out); }
.card tbody > tr:hover > td:not(.nodata) { background-color:#f7f8fa; }
.info, .chip, .btn, .col .seg { transition:background-color var(--t-hover) var(--ease-out), color var(--t-hover) var(--ease-out),
  transform var(--t-press) var(--ease-out), opacity var(--t-hover) var(--ease-out); }
.info:hover { transform:scale(1.08); }
.info:active, .chip:active, .btn:active:not(:disabled) { transform:scale(.96); }

.about[popover] { opacity:0; transform:translateY(-4px) scale(.98); transform-origin:top left;
  transition:opacity var(--t-reveal) var(--ease-out), transform var(--t-reveal) var(--ease-out),
    overlay var(--t-reveal) allow-discrete, display var(--t-reveal) allow-discrete; }
.about[popover]:popover-open { opacity:1; transform:none; }
@starting-style { .about[popover]:popover-open { opacity:0; transform:translateY(-4px) scale(.98); } }
details[open] > :not(summary) { animation:settle var(--t-reveal) var(--ease-out); }
@keyframes settle { from { opacity:0; transform:translateY(-4px); } }

.col .seg { transform-origin:50% 100%; animation:grow 700ms var(--ease-out) both 250ms; }
@keyframes grow { from { transform:scaleY(0); } }

/* The charts (reports/charts.py): a donut's slices sweep in clockwise one after another; the trend line
   wipes in from the left and its dots pop in after it; a hovered slice thickens, a hovered dot grows. */
.pie circle { animation:sweep 800ms var(--ease-out) both 200ms;
  transition:opacity var(--t-hover) var(--ease-out), stroke-width var(--t-hover) var(--ease-out); }
.pie circle:nth-of-type(2) { animation-delay:320ms; }
.pie circle:nth-of-type(3) { animation-delay:440ms; }
.pie circle:nth-of-type(n+4) { animation-delay:560ms; }
.pie circle:hover { stroke-width:9.5; }
@keyframes sweep { from { stroke-dasharray:0 100; } }
.pie text { animation:rise var(--t-enter) var(--ease-out) both 500ms; }
.pielegend li { transition:background-color var(--t-hover) var(--ease-out); }
.pielegend li:hover { background:#f7f8fa; }
svg.line .path { animation:wipe 900ms var(--ease-out) both 250ms; }
@keyframes wipe { from { clip-path:inset(0 100% 0 0); } to { clip-path:inset(0 0 0 0); } }
svg.line .dot { transform-box:fill-box; transform-origin:center; animation:pop 320ms var(--ease-out) both 900ms;
  transition:transform var(--t-hover) var(--ease-out); }
svg.line a:hover .dot, svg.line a:focus .dot { transform:scale(1.35); }
@keyframes pop { from { opacity:0; transform:scale(.4); } }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms !important; animation-delay:0s !important; animation-iteration-count:1 !important;
    transition-duration:.01ms !important; scroll-behavior:auto !important; }
}
@media print { *, *::before, *::after { animation:none !important; transition:none !important; } }
"""
CSS += MOTION_CSS

# On every page, in the top bar and the footer. Everything the suite reads today is synthetic (sample
# files and simulated APIs); change these two when a real Goodwill export is read.
DATA_LABEL = "Synthetic sample data"
DATA_NOTE = "no real Goodwill file has been read"
# The top bar: section, its landing page under reports/, the link text. A page's section is read from its title.
NAV = [("", "index.html", "Overview"), ("pulse", "pulse/index.html", "Daily Reports"),
       ("scorecard", "scorecard/index.html", "COO Scorecards"), ("close", "close/index.html", "Month-End Close")]
SECTIONS = {"nightly pulse": "pulse", "daily reports": "pulse", "coo scorecard": "scorecard", "month-end close": "close"}


def topbar(title, root="../"):
    """The bar every page shares. `root` is the way from the page up to reports/ ("" for the portal)."""
    here = next((key for name, key in SECTIONS.items() if title.lower().startswith(name)), "")
    links = "".join(f'<a href="{root}{href}"{" class=\"here\"" if key == here else ""}>{text}</a>'
                    for key, href, text in NAV)
    return (f'<div class="topbar"><div class="topbar-in"><a class="brand" href="{root}index.html">Goodwill Michiana '
            f'E-Commerce Reports</a><nav>{links}</nav><span class="datalabel">{DATA_LABEL}</span></div></div>')


class _Page(Template):
    """The page shell. `substitute(title=, css=, body=)` as before; the top bar, footer and accessibility
    menu (reports/a11y.py) come with it, and font sizes become rem so the menu's text size reaches them."""

    def substitute(self, *, title, css, body, root="../"):
        return super().substitute(title=title, css=a11y.scalable(css + a11y.CSS), body=body,
                                  topbar=topbar(title, root), label=DATA_LABEL, note=DATA_NOTE,
                                  a11y_script=a11y.SCRIPT, a11y_menu=a11y.MENU)


PAGE = _Page("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>$css</style>
</head>
<body>
$a11y_script
$topbar
$a11y_menu
<main>
$body
</main>
<footer class="pagefoot">Goodwill Michiana E-Commerce Reports · <strong>$label</strong>: $note.</footer>
<script>
/* An asterisk opens the notes at the bottom of the page; so does printing. */
document.addEventListener("click", function (e) {
  var notes = document.getElementById("notes");
  if (notes && e.target.closest && e.target.closest("a.ast")) notes.open = true;
});
window.addEventListener("beforeprint", function () {
  var notes = document.getElementById("notes");
  if (notes) notes.open = true;
});
</script>
</body>
</html>
""")

DAY = Template("""<header>
  <h1>Nightly Pulse: $day_long</h1>
  <p>Compared with $prior_long$mock</p>
</header>
<p class="summary$summary_class">$summary</p>
<div class="kpis">
  <div class="kpi"><div class="label">Enterprise Revenue</div><div class="value">$ent_revenue</div><div class="sub">$ent_delta</div></div>
  <div class="kpi"><div class="label">Orders$ast_orders</div><div class="value">$ent_orders</div></div>
  <div class="kpi"><div class="label">Customers$ast_customers</div><div class="value">$ent_customers</div><div class="sub">$ent_customers_delta</div></div>
  <div class="kpi"><div class="label">Marketplace Fees$ast_fees</div><div class="value">$ent_fees</div></div>
</div>
$banner
<div class="card">
<table>
  <thead><tr>
    <th>Marketplace</th><th class="status">Status</th><th>Revenue</th><th>vs Prior Day</th>
    <th>Orders</th><th>Customers</th><th>Refunds</th><th>Fees</th>
  </tr></thead>
  <tbody>
$rows
  </tbody>
</table>
</div>
<div class="actions">$downloads<a class="btn quiet" href="index.html">All Days</a></div>
$notes""")

INDEX = Template("""<header>
  <h1>Daily Reports</h1>
  <p>$count nightly report(s) · search by date, day or status</p>
</header>
$tiles
$table""")


def money(cents):
    return "-" if cents is None else f"{'-' if cents < 0 else ''}${abs(cents) / 100:,.2f}"


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def ast(tip=""):
    """The asterisk after a label or a figure. Hovering shows `tip`; selecting it opens the notes at the bottom."""
    return f'<a class="ast" href="#notes" title="{escape(tip)}" aria-label="Note: {escape(tip)}">*</a>'


def notes(sections, title="Notes and Definitions"):
    """The dropdown at the bottom of a page: what the figures mean and what is simulated, out of the way of the
    figures themselves. `sections` is (heading or "", html); empty ones are skipped."""
    inner = "".join((f"<h3>{escape(h)}</h3>" if h else "") + html for h, html in sections if html)
    return f'<details class="notes" id="notes"><summary>{escape(title)}</summary><div class="in">{inner}</div></details>'


def label(key, m=None):
    return (m or {}).get("label") or LABELS.get(key, key.title())


def excluded_keys(ent):
    return [x["marketplace"] if isinstance(x, dict) else x for x in ent.get("excluded") or []]


def prior_date(p):
    return p.get("prior_date") or (p["enterprise"].get("delta") or {}).get("prior_date")


def delta_html(d, note=None):
    if not d or d.get("revenue_cents") is None:
        reason = (d or {}).get("reason")
        reason = REASONS.get(reason, reason) or "no comparison"
        return f'<span class="muted" title="{escape(reason)}">n/a</span>{ast(reason)}'
    cents, pct = d["revenue_cents"], d.get("revenue_pct")
    cls, arrow = ("up", "▲") if cents > 0 else ("down", "▼") if cents < 0 else ("", "")
    pct_txt = f" ({pct:+.1f}%)" if pct is not None else ""
    sign = "+" if cents > 0 else ""
    note = note or REASONS.get(d.get("reason"), d.get("reason"))
    note = ast(note) if note else ""
    return f'<span class="chg {cls}">{arrow} {sign}{money(cents)}{pct_txt}</span>{note}'


def count_delta(n):
    if n is None:
        return ""
    cls = "up" if n > 0 else "down" if n < 0 else ""
    return f'<span class="chg {cls}">{n:+d}</span> <span class="muted">vs prior day</span>'


def summary_line(p):
    """P-O3: one templated sentence, e.g. "Revenue up 4.2% vs Friday; ShopGoodwill strongest (61% of revenue)"."""
    markets, ent = p["marketplaces"], p["enterprise"]
    ed = ent.get("delta") or {}
    prior = f"{date.fromisoformat(prior_date(p)):%A}" if prior_date(p) else "the prior day"
    pct = ed.get("revenue_pct")
    if pct is None:
        parts = [f"Revenue {money(ent['revenue_cents'])}, not comparable with {prior}"]
    elif round(pct, 1) == 0:
        parts = [f"Revenue flat vs {prior}"]
    else:
        parts = [f"Revenue {'up' if pct > 0 else 'down'} {abs(pct):.1f}% vs {prior}"]
    if pct is not None and ent.get("excluded"):
        parts[0] += " on comparable marketplaces"
    ok = [k for k in ORDER if markets.get(k, {}).get("status") == "ok"]
    if len(ok) > 1 and ent["revenue_cents"]:
        k = max(ok, key=lambda k: markets[k]["revenue_cents"])
        top = markets[k]
        parts.append(f"{label(k, top)} strongest ({top['revenue_cents'] / ent['revenue_cents']:.0%} of revenue)")
    for k in ORDER:
        m = markets.get(k, {})
        if m.get("status") == "missing":
            parts.append(f"{label(k, m)} file missing")
        elif m.get("status") == "stale":
            parts.append(f"{label(k, m)} file has no orders for this day")
        elif m.get("status") == "unknown":
            parts.append(f"{label(k, m)} file status unknown")
    if ent.get("refunds_cents"):
        parts.append(f"{money(-ent['refunds_cents'])} refunded")
    dups = ((p.get("data_quality") or {}).get("by_kind") or {}).get("duplicate")
    if dups:
        parts.append(f"{dups} duplicate rows removed")
    return "; ".join(parts) + "."


def row_html(key, m):
    name = escape(label(key, m))
    status = m.get("status", "missing")
    pill = f'<span class="pill {status}">{PILL.get(status, escape(status))}</span>'
    if status != "ok":
        return (f'    <tr><td>{name}</td><td class="status">{pill}</td>'
                f'<td class="nodata{" quiet" if status == "not_configured" else ""}" colspan="6">'
                f'{NO_DATA.get(status, "No data")}</td></tr>')
    basis = ast(BY_ORDER) if m.get("customer_basis") == "order" else ""
    return (f'    <tr><td>{name}</td><td class="status">{pill}</td><td>{money(m["revenue_cents"])}</td>'
            f'<td>{delta_html(m.get("delta"))}</td><td>{m["orders"]:,}</td><td>{m["customers"]:,}{basis}</td>'
            f'<td>{money(m["refunds_cents"])}</td><td>{money(m["fees_cents"])}</td></tr>')


def render_day(p, workbook=False):
    """The day's page. `workbook` says the Excel file was written beside it, so the page offers it."""
    markets, ent = p["marketplaces"], p["enterprise"]
    rows = [row_html(k, markets.get(k, {"status": "missing"})) for k in ORDER]
    excluded = [label(k, markets.get(k)) for k in excluded_keys(ent)]
    ed = ent.get("delta") or {}
    same = "same marketplaces on both days" if excluded and ed.get("revenue_cents") is not None else None
    rows.append(
        f'    <tr class="total"><td>Enterprise Total</td><td class="status">'
        f'{"Partial" if excluded else "Complete"}</td><td>{money(ent["revenue_cents"])}</td>'
        f'<td>{delta_html(ed, same)}</td><td>{ent["orders"]:,}</td><td>{ent["customers"]:,}</td>'
        f'<td>{money(ent["refunds_cents"])}</td><td>{money(ent["fees_cents"])}</td></tr>')

    banner = ""
    if excluded:
        names = " and ".join(escape(n) for n in excluded)
        banner = (f'<div class="banner"><strong>{names}: no data for this day.</strong> Enterprise totals '
                  f'exclude {names} and are not a full day.</div>')

    dq = p.get("data_quality") or {}
    if dq.get("warnings_total"):
        parts = ", ".join(f"{escape(k.replace('_', ' '))} rows: {n}" for k, n in sorted(dq.get("by_kind", {}).items()))
        quality = f"{dq['warnings_total']} issue(s) handled automatically: {parts}. Duplicates were counted once."
    else:
        quality = "No issues found in tonight's files."
    if dq.get("rows_rejected"):
        quality += f" {dq['rows_rejected']} row(s) could not be read and were left out."

    defs = "".join(f"<dt>{escape(k.replace('_', ' ').capitalize())}</dt><dd>{escape(v)}</dd>"
                   for k, v in (p.get("definitions") or {}).items())
    by_order = [label(k, markets[k]) for k in ORDER if markets.get(k, {}).get("customer_basis") == "order"]
    tz, made = escape(p.get("timezone", "America/New_York")), escape(stamp(p.get("generated_at", "")))
    points = ["<strong>Orders:</strong> sale orders; refunds are not counted as orders.",
              "<strong>Customers:</strong> the sum across marketplaces."
              + (f" {escape(', '.join(by_order))}: counted by order, because the export gives no unique buyer id, "
                 f"so each order counts as one customer." if by_order else ""),
              "<strong>Marketplace fees:</strong> shown for reference; not deducted from revenue.",
              "<strong>vs prior day:</strong> compared like for like. It reads n/a when a marketplace has no data on "
              "either day; when a file is missing, the enterprise change compares the same marketplaces on both days.",
              f"Times in {tz}" + (f" · generated {made}" if made else "") + "."]
    day = p["business_date"]
    downloads = "".join(
        f'<a class="btn{cls} dl" href="{day}{ext}" download>{name}</a>' for ext, name, cls, there in (
            (".xlsx", "Download Full Day (Excel)", "", workbook), (".csv", "CSV", " quiet", True)) if there)
    downloads += f'<a class="btn quiet" href="{day}.email.html">Email Version</a>'
    body = DAY.substitute(
        summary=escape(summary_line(p)),
        summary_class=" alert" if excluded else "",
        day_long=long_date(day),
        prior_long=long_date(prior_date(p)) if prior_date(p) else "no prior day",
        mock=" · <strong>mock data</strong>" if p.get("mock") else "",
        ent_revenue=money(ent["revenue_cents"]),
        ent_delta=delta_html(ed, same),
        ent_orders=f"{ent['orders']:,}",
        ent_customers_delta=count_delta(ed.get("customers")),
        ent_customers=f"{ent['customers']:,}",
        ent_fees=money(ent["fees_cents"]),
        ast_orders=ast("Sale orders; refunds are not counted"),
        ast_customers=ast("Sum across marketplaces" + ("; some are counted by order" if by_order else "")),
        ast_fees=ast("Not deducted from revenue"),
        banner=banner,
        rows="\n".join(rows),
        downloads=downloads,
        notes=notes([("", "<ul>" + "".join(f"<li>{x}</li>" for x in points) + "</ul>"),
                     ("Data Quality", f"<p>{quality}</p>"), ("Definitions", f"<dl>{defs}</dl>" if defs else "")]),
    )
    return PAGE.substitute(title=f"Nightly Pulse {day}", css=CSS, body=body)


# Email copy: Outlook desktop renders with Word, which ignores <style> variables, grid and
# border-radius. So: nested tables, every style inline on the element, web-safe fonts, hex colors.
E = {"primary": "#0054A4", "ink": "#231F20", "bg": "#ffffff", "up": "#9DBB68", "down": "#CC1F40",
     "muted": "#5c5859", "line": "#d3d2d2"}
EMAIL_FONT = "font-family:Arial,Helvetica,sans-serif;"


def email_delta(d):
    if not d or d.get("revenue_cents") is None:
        return f'<span style="color:{E["muted"]};">n/a</span>'
    cents, pct = d["revenue_cents"], d.get("revenue_pct")
    pct_txt = f" ({pct:+.1f}%)" if pct is not None else ""
    if cents > 0:
        return (f'<span style="background:{E["up"]};color:{E["ink"]};padding:1px 6px;">'
                f'&#9650; +{money(cents)}{pct_txt}</span>')
    if cents < 0:
        return (f'<span style="background:{E["down"]};color:#ffffff;padding:1px 6px;">'
                f'&#9660; {money(cents)}{pct_txt}</span>')
    return f"{money(cents)}{pct_txt}"


def render_email(p):
    markets, ent = p["marketplaces"], p["enterprise"]
    td = f'style="{EMAIL_FONT}font-size:14px;color:{E["ink"]};padding:8px 10px;border-bottom:1px solid {E["line"]};text-align:right;"'
    td_l = td.replace("text-align:right", "text-align:left")
    th = f'style="{EMAIL_FONT}font-size:11px;color:{E["primary"]};padding:8px 10px;text-align:right;border-bottom:2px solid {E["primary"]};"'
    th_l = th.replace("text-align:right", "text-align:left")

    rows = []
    for k in ORDER:
        m = markets.get(k, {"status": "missing"})
        name = escape(label(k, m))
        if m["status"] != "ok":
            color = E["muted"] if m["status"] == "not_configured" else E["down"]
            rows.append(f'<tr><td {td_l}>{name}</td><td {td_l} colspan="5">'
                        f'<b style="color:{color};">{NO_DATA.get(m["status"], "No data")}</b></td></tr>')
            continue
        rows.append(f'<tr><td {td_l}>{name}</td><td {td}>{money(m["revenue_cents"])}</td>'
                    f'<td {td}>{email_delta(m.get("delta"))}</td><td {td}>{m["orders"]:,}</td>'
                    f'<td {td}>{money(m["refunds_cents"])}</td><td {td}>{money(m["fees_cents"])}</td></tr>')
    tot = td.replace("border-bottom:1px solid", "font-weight:bold;border-top:2px solid").replace(
        f'{E["line"]};text', f'{E["primary"]};text')
    rows.append(f'<tr><td {tot.replace("text-align:right", "text-align:left")}>Enterprise Total</td>'
                f'<td {tot}>{money(ent["revenue_cents"])}</td><td {tot}>{email_delta(ent.get("delta"))}</td>'
                f'<td {tot}>{ent["orders"]:,}</td><td {tot}>{money(ent["refunds_cents"])}</td>'
                f'<td {tot}>{money(ent["fees_cents"])}</td></tr>')

    excluded = [label(k, markets.get(k)) for k in excluded_keys(ent)]
    alert = ""
    if excluded:
        names = " and ".join(escape(n) for n in excluded)
        alert = (f'<tr><td style="{EMAIL_FONT}font-size:14px;color:{E["ink"]};background:#fbe8ec;'
                 f'border-left:5px solid {E["down"]};padding:10px 14px;"><b>{names}: no data for this day.</b> '
                 f'Totals exclude {names}.</td></tr>'
                 f'<tr><td style="height:12px;line-height:12px;">&nbsp;</td></tr>')
    defs = "<br>".join(f"<b>{escape(k.replace('_', ' ').capitalize())}:</b> {escape(v)}"
                       for k, v in (p.get("definitions") or {}).items())
    mock = " &middot; mock data" if p.get("mock") else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nightly Pulse {p['business_date']}</title></head>
<body style="margin:0;padding:0;background:{E['bg']};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{E['bg']};">
<tr><td align="center" style="padding:16px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:100%;">
<tr><td style="{EMAIL_FONT}background:{E['primary']};color:#ffffff;padding:16px 20px;">
  <div style="font-size:20px;font-weight:bold;">Nightly Pulse: {long_date(p['business_date'])}</div>
  <div style="font-size:12px;">Goodwill Michiana e-commerce{mock}</div></td></tr>
<tr><td style="height:12px;line-height:12px;">&nbsp;</td></tr>
<tr><td style="{EMAIL_FONT}font-size:16px;font-weight:bold;color:{E['ink']};background:#ffffff;border-left:5px solid {E['down'] if excluded else E['primary']};padding:12px 14px;">{escape(summary_line(p))}</td></tr>
<tr><td style="height:12px;line-height:12px;">&nbsp;</td></tr>
{alert}<tr><td style="background:#ffffff;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><th {th_l}>MARKETPLACE</th><th {th}>REVENUE</th><th {th}>VS PRIOR DAY</th><th {th}>ORDERS</th><th {th}>REFUNDS</th><th {th}>FEES</th></tr>
{chr(10).join(rows)}
</table></td></tr>
<tr><td style="{EMAIL_FONT}font-size:11px;color:{E['muted']};padding:12px 2px;">{defs}</td></tr>
</table></td></tr></table>
</body></html>
"""


def night(dest, day):
    """What the list of days shows for one night, read from the CSV and the page written beside it."""
    found = {"revenue": None, "orders": None, "gaps": [], "summary": ""}
    try:
        with open(dest / f"{day}.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        ok = [r for r in rows if r["Status"] == "ok"]
        found.update(revenue=sum(float(r["Revenue"] or 0) for r in ok) if ok else None,
                     orders=sum(int(r["Orders"] or 0) for r in ok) if ok else None,
                     gaps=[r["Marketplace"] for r in rows if r["Status"] in ("missing", "stale", "unknown")])
        m = re.search(r'<p class="summary[^"]*">(.*?)</p>', (dest / f"{day}.html").read_text(encoding="utf-8"), re.S)
        found["summary"] = unescape(m[1]) if m else ""
    except (OSError, KeyError, ValueError):
        pass  # an older page without its CSV: the row shows the day and its link
    return found


def render_index(dest):
    """The Daily Reports page: every night on file with its figures, newest first, grouped by month."""
    days = sorted((f.stem for f in dest.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem)),
                  reverse=True)
    nights = {d: night(dest, d) for d in days}

    def dollars(v):
        return "-" if v is None else f"${v:,.2f}"

    groups = {}
    for i, d in enumerate(days):
        n, when = nights[d], date.fromisoformat(d)
        data = (f'<span class="pill missing">No data: {escape(", ".join(n["gaps"]))}</span>' if n["gaps"]
                else '<span class="pill ok">Complete</span>')
        files = "".join(f'<a href="{d}{ext}">{name}</a>' for ext, name in
                        ((".xlsx", "Excel"), (".csv", "CSV"), (".email.html", "Email")) if (dest / f"{d}{ext}").exists())
        groups.setdefault(f"{when:%B %Y}", []).append({
            "cells": [f'<a href="{d}.html">{when:%a}, {when:%b} {when.day}</a>{"<small>latest</small>" if i == 0 else ""}',
                      dollars(n["revenue"]), "-" if n["orders"] is None else f'{n["orders"]:,}', data,
                      escape(n["summary"]), files],
            # Every way people type the date: 10/03/2026, 10/3/2026, 10/03/26, 2026-10-03, "Oct 3", "Saturday".
            "find": f'{long_date(d)} {d} {when:%b} {when:%m/%d/%Y} {when.month}/{when.day}/{when.year} {when:%m/%d/%y} '
                    f'{"missing no data " + " ".join(n["gaps"]) if n["gaps"] else "complete"}',
            "tags": "gaps" if n["gaps"] else "complete"})
    top = ""
    if days:
        first, last = date.fromisoformat(days[-1]), date.fromisoformat(days[0])
        gaps = sum(bool(n["gaps"]) for n in nights.values())
        top = library.tiles([
            ("Reports on File", f"{len(days)}", f"{first:%b} {first.day} to {last:%b} {last.day}, {last.year}", None),
            ("Latest Night", dollars(nights[days[0]]["revenue"]), f"{last:%A}, {last:%B} {last.day}", f"{days[0]}.html"),
            ("Nights With Missing Data", f"{gaps}", f"of the {len(days)} on file", None)])
    table = library.finder_table(
        [("Day", "l"), ("Revenue", "num"), ("Orders", "num"), ("Data", "l"), ("That Night", "say"), ("Files", "files")],
        list(groups.items()), [("complete", "Complete"), ("gaps", "Missing data")],
        'Find a day: "10/03/2026", "Oct 3", "Saturday", "missing"', noun="daily report")
    body = INDEX.substitute(count=len(days), tiles=top, table=table)
    return PAGE.substitute(title="Daily Reports", css=CSS + library.LIBRARY_CSS, body=body)


def stamp(iso):
    """A `generated_at` timestamp as people write it: "Oct 4, 2026, 10:17 AM". Anything unreadable is kept as is."""
    try:
        t = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return f"{t:%b} {t.day}, {t.year}, {t.hour % 12 or 12}:{t:%M} {'AM' if t.hour < 12 else 'PM'}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="business date, YYYY-MM-DD")
    ap.add_argument("--src", default=str(ROOT / "out" / "pulse"), help="folder with <date>.json")
    ap.add_argument("--dest", default=str(ROOT / "reports" / "pulse"), help="folder for the HTML")
    args = ap.parse_args(argv)
    src = Path(args.src) / f"{args.date.isoformat()}.json"
    if not src.exists():
        raise SystemExit(f"no pulse file at {src}; run the pulse command (or reports.mock_pulse) first")
    pulse = json.loads(src.read_text(encoding="utf-8"))
    for path in render(pulse, Path(args.dest)):
        print(f"wrote {path}")
    print(summary_line(pulse))


def render(pulse, dest, detail_dir=None):
    """Write the page, CSV, email copy, Excel workbook and index for one pulse; return the paths written.
    `detail_dir` is the engine's output folder for the night (transactions.csv, warnings.json): with it the
    workbook also holds the night's transactions and the rows the engine flagged."""
    from reports import day_workbook
    dest.mkdir(parents=True, exist_ok=True)
    day = pulse["business_date"]
    paths = [dest / f"{day}.html", dest / f"{day}.csv", dest / f"{day}.email.html", dest / "index.html"]
    book = day_workbook.write(dest / f"{day}.xlsx", pulse, detail_dir)
    paths[0].write_text(render_day(pulse, workbook=book), encoding="utf-8")
    write_csv(paths[1], [day_record(pulse)])
    paths[2].write_text(render_email(pulse), encoding="utf-8")
    paths[3].write_text(render_index(dest), encoding="utf-8")
    return paths + ([dest / f"{day}.xlsx"] if book else [])


if __name__ == "__main__":
    main()
