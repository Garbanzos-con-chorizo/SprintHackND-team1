"""Design system for the report pages: tokens, base styles, shared components, print rules.

Every page inlines this one stylesheet: the pages open from disk and travel as email attachments,
so there is no external CSS or web font (Inter where installed, else the system UI font). Page
modules add their own layout on top: scorecard.SCORECARD_CSS, close_report.CLOSE_CSS,
hub.HUB_CSS, kpi.KPI_CSS. Square corners, 1-2px rules, tabular figures everywhere.
"""
from datetime import date, datetime
from html import escape
from string import Template

# Brand: Goodwill blue #0054A4 and charcoal #231F20; neutrals #F8F9FA / #F1F3F5 / #DEE2E6.
# Red #D9381E, green #1B8755 and grey #6C757D each pass AA as text on white (about 4.5-4.7:1),
# so changes and statuses are coloured text on white, never filled badges.
CSS = """
:root {
  --blue:#0054A4; --blue-dk:#003D78; --blue-tint:#EAF1F8; --blue-bar:#9DBCE0;
  --ink:#231F20; --ink-2:#495057; --muted:#6C757D;
  --bg:#FFFFFF; --bg-1:#F8F9FA; --bg-2:#F1F3F5;
  --rule:#DEE2E6; --rule-dk:#ADB5BD;
  --red:#D9381E; --green:#1B8755;
  --bd:1px solid var(--rule); --bd-dk:1px solid var(--rule-dk); --bd-blue:2px solid var(--blue);
  --font:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  --mono:ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
  --fw-regular:400; --fw-semi:600; --fw-bold:700;
  --fs-label:10.5px; --fs-small:11.5px; --fs-body:13px; --fs-lead:14px; --fs-title:20px; --fs-metric:22px;
  --sp-1:2px; --sp-2:4px; --sp-3:6px; --sp-4:8px; --sp-5:12px; --sp-6:16px; --sp-7:24px;
  --page:1200px;
}
*, *::before, *::after { box-sizing:border-box; border-radius:0; }
html { -webkit-text-size-adjust:100%; text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--font); font-size:var(--fs-body);
  line-height:1.4; letter-spacing:-0.01em; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; }
h1, h2, h3, p, ul, dl, dd { margin:0; }
table { border-collapse:collapse; border-spacing:0; font-variant-numeric:tabular-nums; }
a { color:var(--blue); text-decoration:none; }
a:hover { text-decoration:underline; }
code { font-family:var(--mono); font-size:.92em; background:var(--bg-2); padding:0 var(--sp-1); }
strong, b { font-weight:var(--fw-bold); }
.muted { color:var(--muted); }

/* Micro labels: one style for column heads, field names, section titles and status pills */
th, .label, .facts dt, .sec, section.foot h2, .pill, .tag {
  font-size:var(--fs-label); font-weight:var(--fw-bold); letter-spacing:.06em; text-transform:uppercase; line-height:1.3; }

/* Brand bar, page header, headline */
.brandbar { background:var(--blue); color:#fff; }
.brandbar > div { max-width:var(--page); margin:0 auto; padding:0 var(--sp-6); height:28px;
  display:flex; align-items:center; gap:var(--sp-4); }
.brandbar b { font-size:var(--fs-label); letter-spacing:.09em; text-transform:uppercase; }
.brandbar span { font-size:var(--fs-small); padding-left:var(--sp-4); border-left:1px solid rgba(255,255,255,.45); }
main { max-width:var(--page); margin:0 auto; padding:var(--sp-6) var(--sp-6) var(--sp-7); }
header { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:var(--sp-2) var(--sp-6);
  padding:0 0 var(--sp-4); border-bottom:var(--bd-blue); }
header h1 { font-size:var(--fs-title); font-weight:var(--fw-bold); line-height:1.2; letter-spacing:-0.02em; }
header p { font-size:var(--fs-small); color:var(--muted); }
.summary { margin:var(--sp-5) 0 0; padding:var(--sp-4) var(--sp-5); background:var(--bg-1); border:var(--bd);
  border-left:3px solid var(--blue); font-size:var(--fs-lead); font-weight:var(--fw-semi); line-height:1.35; }
.summary.alert { border-left-color:var(--red); }

/* Facts strip: label over value, cells divided by 1px rules */
.facts { display:flex; flex-wrap:wrap; gap:1px; margin:var(--sp-4) 0 0; background:var(--rule); border:var(--bd); }
.facts > div { flex:1 0 auto; padding:var(--sp-3) var(--sp-5); background:var(--bg); }
.facts dt { color:var(--muted); }
.facts dd { margin-top:1px; font-weight:var(--fw-semi); white-space:nowrap; }
.facts dd.bad { color:var(--red); }
.facts dd.good { color:var(--green); }

/* Alert banner: white, a red rule on the left, the lead phrase in red */
.banner { margin:var(--sp-4) 0 0; padding:var(--sp-3) var(--sp-5); background:var(--bg); border:var(--bd);
  border-left:3px solid var(--red); }
.banner > strong:first-child { color:var(--red); }

/* Stat strip (pulse headline numbers) */
.kpis { display:flex; flex-wrap:wrap; gap:1px; margin:var(--sp-5) 0 0; background:var(--rule); border:var(--bd); }
.kpi { flex:1 1 170px; padding:var(--sp-4) var(--sp-5); background:var(--bg); }
.kpi .label { color:var(--blue); }
.kpi .value { margin-top:var(--sp-1); font-size:var(--fs-metric); font-weight:var(--fw-bold); line-height:1.15; letter-spacing:-0.02em; }
.kpi .sub { margin-top:var(--sp-1); font-size:var(--fs-small); color:var(--ink-2); }

/* Section titles */
.sec { display:flex; flex-wrap:wrap; align-items:baseline; gap:var(--sp-2) var(--sp-4); margin:var(--sp-7) 0 var(--sp-3); color:var(--ink); }
.sec .aside { font-size:var(--fs-small); font-weight:var(--fw-regular); letter-spacing:-0.01em; text-transform:none; color:var(--muted); }

/* Tables: no outer box; a blue rule under the head, hairlines between rows */
.card { overflow-x:auto; margin-top:var(--sp-4); }
table { width:100%; min-width:720px; }
th, td { padding:var(--sp-3) var(--sp-4); text-align:right; vertical-align:top; border-bottom:var(--bd); white-space:nowrap; }
th { vertical-align:bottom; color:var(--blue); background:var(--bg); border-bottom:var(--bd-blue); }
th:first-child, td:first-child, th.l, td.l, th.status, td.status { text-align:left; }
table.striped > tbody > tr:nth-child(even) > td { background-color:var(--bg-1); }
tbody > tr:hover > td { background-color:var(--blue-tint); }
tr.total > td { font-weight:var(--fw-bold); background:var(--bg); border-top:1px solid var(--ink); border-bottom:3px double var(--ink); }
td.nodata { text-align:left; color:var(--red); font-weight:var(--fw-semi); }
td.nodata.quiet { color:var(--muted); font-weight:var(--fw-regular); font-style:italic; }
td small.note { display:block; max-width:220px; margin:1px 0 0 auto; white-space:normal; color:var(--muted);
  font-size:var(--fs-small); font-weight:var(--fw-regular); }
.kpi small.note { display:block; color:var(--muted); font-size:var(--fs-small); }

/* Status pills and changes */
.pill { display:inline-block; padding:0 var(--sp-3); line-height:16px; white-space:nowrap; color:var(--ink-2);
  background:var(--bg); border:1px solid currentColor; }
.pill.ok { color:var(--green); }
.pill.missing, .pill.stale, .pill.unknown, .pill.bad { color:var(--red); }
.pill.not_configured { color:var(--muted); border-color:var(--rule); }
.chg { font-weight:var(--fw-semi); white-space:nowrap; }
.chg.up { color:var(--green); }
.chg.down { color:var(--red); }

/* Footnotes, definitions, navigation */
section.foot { margin:var(--sp-7) 0 0; padding:var(--sp-4) 0 0; border-top:var(--bd); font-size:var(--fs-small); color:var(--ink-2); }
section.foot h2 { margin:var(--sp-5) 0 var(--sp-2); color:var(--blue); }
section.foot h2:first-child { margin-top:0; }
section.foot p { margin:0 0 var(--sp-2); max-width:120ch; }
section.foot dl, details.defs dl { display:grid; grid-template-columns:max-content 1fr; gap:var(--sp-1) var(--sp-6); }
section.foot dt, details.defs dt { font-weight:var(--fw-semi); color:var(--ink); }
.nav { margin:var(--sp-5) 0 0; font-size:var(--fs-small); color:var(--muted); }

/* Archive lists (all days, all weeks, all scorecards) */
ul.days { list-style:none; padding:0; margin:var(--sp-5) 0 0; border:var(--bd); }
ul.days li { border-top:var(--bd); }
ul.days li:first-child { border-top:0; }
ul.days li:nth-child(even) { background:var(--bg-1); }
ul.days a { display:block; padding:var(--sp-4) var(--sp-5); font-weight:var(--fw-semi); color:var(--ink); }
ul.days a:hover { background:var(--blue-tint); text-decoration:none; }

@media (max-width:640px) {
  main { padding:var(--sp-5) var(--sp-6) var(--sp-7); }
  .brandbar span { display:none; }
  section.foot dl, details.defs dl { grid-template-columns:1fr; }
  section.foot dd, details.defs dd { margin-bottom:var(--sp-3); }
}

@media print {
  @page { size:letter portrait; margin:0.45in; }
  :root { --page:none; }
  html, body { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  body { font-size:8.5pt; }
  th, .label, .facts dt, .sec, section.foot h2, .pill, .tag { font-size:6.5pt; }
  .brandbar > div { height:auto; padding:2pt 6pt; }
  .brandbar b { font-size:6.5pt; }
  .brandbar span { font-size:7pt; }
  main { padding:6pt 0 0; }
  header { padding-bottom:4pt; }
  header h1 { font-size:14pt; }
  header p { font-size:7.5pt; }
  .summary { margin-top:6pt; padding:4pt 8pt; font-size:9.5pt; }
  .facts { margin-top:5pt; }
  .facts > div { padding:2pt 6pt; }
  .banner { margin-top:5pt; padding:3pt 8pt; }
  .kpis { margin-top:6pt; }
  .kpi { padding:4pt 8pt; }
  .kpi .value { font-size:14pt; }
  .kpi .sub, td small.note { font-size:7pt; }
  .sec { margin:9pt 0 3pt; }
  .card { overflow:visible; margin-top:2pt; }
  table { min-width:0; }
  th, td { padding:2.5pt 5pt; }
  .pill { line-height:10pt; padding:0 3pt; }
  section.foot { margin-top:8pt; padding-top:4pt; font-size:7pt; }
  section.foot h2 { margin:4pt 0 1pt; }
  section.foot dl { gap:0 8pt; }
  header, .summary, .facts, .banner, .kpis, tr, dl > div { break-inside:avoid; }
  thead { display:table-header-group; }
  .sec, section.foot h2 { break-after:avoid; }
  a { color:inherit; }
  .nav, .noprint { display:none !important; }
}
"""

PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>$css</style>
</head>
<body>
<div class="brandbar"><div><b>Goodwill Michiana</b><span>E-commerce reporting</span></div></div>
<main>
$body
</main>
</body>
</html>
""")

# Email copy: Outlook desktop renders with Word, which ignores <style> variables, grid and
# border-radius. So: nested tables, every style inline on the element, web-safe fonts, hex colors.
E = {"primary": "#0054A4", "ink": "#231F20", "bg": "#ffffff", "up": "#1B8755", "down": "#D9381E",
     "muted": "#6C757D", "line": "#DEE2E6", "tint": "#F8F9FA"}
EMAIL_FONT = "font-family:Arial,Helvetica,sans-serif;"


def facts(items):
    """A facts strip from (label, value_html, tone) items; tone is "", "bad" or "good"."""
    cells = "".join(f'<div><dt>{escape(name)}</dt><dd class="{tone}">{value}</dd></div>' if tone
                    else f"<div><dt>{escape(name)}</dt><dd>{value}</dd></div>" for name, value, tone in items)
    return f'<dl class="facts">{cells}</dl>'


def span(start, through):
    """'Sep 1 - 30, 2026' style date range for headers and facts."""
    a, b = date.fromisoformat(start), date.fromisoformat(through)
    if a == b:
        return f"{a:%b} {a.day}, {a.year}"
    if (a.year, a.month) == (b.year, b.month):
        return f"{a:%b} {a.day} – {b.day}, {b.year}"
    if a.year == b.year:
        return f"{a:%b} {a.day} – {b:%b} {b.day}, {b.year}"
    return f"{a:%b} {a.day}, {a.year} – {b:%b} {b.day}, {b.year}"


def stamp(iso):
    """A generated_at timestamp as 'Oct 3, 2026 21:40' (the raw text if it does not parse)."""
    try:
        t = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return f"{t:%b} {t.day}, {t.year} {t:%H:%M}"
