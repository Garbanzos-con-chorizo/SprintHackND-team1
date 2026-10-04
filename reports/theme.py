"""Design system for the report pages: tokens, base styles, disclosure components, print rules.

Every page inlines this stylesheet and script: the pages open from disk and travel as email
attachments, so there is no external CSS, font or script (SF Pro on Apple devices, Inter where
installed, else Segoe UI). Page modules add their layout on top: scorecard.SCORECARD_CSS,
close_report.CLOSE_CSS, hub.HUB_CSS.

Progressive disclosure: the default view is numbers and status. Definitions and context sit behind
an info button (`info()`, a popover on hover or tap), longer notes in accordions (`accordion()`,
closed by default), and table metadata in expandable rows (`tr.xrow` + `tr.xdetail`). In print the
triggers disappear, detail rows are shown, and the essential notes print as one-line footnotes
(`print_notes()`), so each page still fits one sheet.
"""
from datetime import date, datetime
from html import escape
from string import Template

# Canvas #F5F5F7, white cards, ink #1D1D1F / #6E6E73, soft tinted status pills. Goodwill blue stays
# the one brand colour (links, focus, share bars).
CSS = """
:root {
  --canvas:#F5F5F7; --card:#FFFFFF; --ink:#1D1D1F; --muted:#6E6E73; --faint:#86868B;
  --hair:#F0F0F2; --line:rgba(0,0,0,.06); --line-2:rgba(0,0,0,.1); --hover:#F8F9FA;
  --accent:#0054A4; --accent-tint:rgba(0,84,164,.16);
  --ok:#248A3D; --ok-bg:rgba(52,199,89,.12);
  --bad:#D70015; --bad-bg:rgba(255,59,48,.12);
  --warn:#B25900; --warn-bg:rgba(255,149,0,.12);
  --neutral-bg:rgba(0,0,0,.05);
  --radius:14px; --radius-sm:12px;
  --shadow:0 4px 20px rgba(0,0,0,.03); --shadow-pop:0 12px 32px rgba(0,0,0,.2);
  --font:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text",Inter,"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Consolas,monospace;
  --fs-label:11px; --fs-small:12px; --fs-body:14px; --fs-lead:17px; --fs-title:28px; --fs-metric:26px; --fs-hero:32px;
  --fw-regular:400; --fw-medium:500; --fw-semi:600; --fw-bold:700;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px; --sp-6:24px; --sp-7:32px;
  --page:1200px;
  --ease-out:cubic-bezier(.2,.8,.2,1); --t-press:120ms; --t-hover:200ms; --t-reveal:240ms; --t-enter:560ms;
}
*, *::before, *::after { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; text-size-adjust:100%; }
body { margin:0; background:var(--canvas); color:var(--ink); font-family:var(--font); font-size:var(--fs-body);
  line-height:1.45; letter-spacing:-0.01em; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; }
h1, h2, h3, p, ul, ol, dl, dd { margin:0; }
table { border-collapse:collapse; border-spacing:0; font-variant-numeric:tabular-nums; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
button { font:inherit; color:inherit; }
code { font-family:var(--mono); font-size:.9em; }
strong, b { font-weight:var(--fw-semi); }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; border-radius:6px; }
.muted { color:var(--muted); }
.print-only, .print-notes { display:none; }

/* Small uppercase labels: column heads, field names, card captions */
th, .label, .facts dt { font-size:var(--fs-label); font-weight:var(--fw-semi); letter-spacing:.05em; text-transform:uppercase;
  color:var(--muted); line-height:1.3; }

/* Frosted top bar, page header */
.topbar { position:sticky; top:0; z-index:30; background:rgba(255,255,255,.72); border-bottom:1px solid var(--line);
  -webkit-backdrop-filter:saturate(180%) blur(20px); backdrop-filter:saturate(180%) blur(20px); }
.topbar > div { max-width:var(--page); margin:0 auto; padding:0 var(--sp-6); height:44px; display:flex; align-items:center; gap:10px; }
.topbar .brand { display:flex; align-items:baseline; gap:10px; color:var(--ink); text-decoration:none; }
.topbar b { font-size:13px; font-weight:var(--fw-semi); color:var(--accent); }
.topbar .brand span { font-size:13px; color:var(--muted); }
.topbar .grow { flex:1; }
.topbar .brand::before { content:""; align-self:center; width:8px; height:8px; border-radius:50%; background:var(--accent); }
.crumb { display:flex; align-items:center; gap:10px; font-size:13px; }
.crumb::before { content:"/"; color:var(--line-2); }
.crumb a { color:var(--ink); font-weight:var(--fw-medium); }
.tb-link { font-size:13px; color:var(--muted); transition:color var(--t-hover) var(--ease-out); }
.tb-link:hover, .tb-link[aria-current] { color:var(--ink); }
.home-btn { display:inline-flex; align-items:center; gap:6px; height:28px; padding:0 12px; border-radius:980px;
  transition:transform var(--t-press) var(--ease-out), background-color var(--t-hover) var(--ease-out), box-shadow var(--t-hover) var(--ease-out);
  background:var(--accent); color:#fff; font-size:13px; font-weight:var(--fw-semi); }
.home-btn:hover { text-decoration:none; background:#0062bf; box-shadow:0 4px 14px rgba(0,84,164,.25); }
.home-btn:active { transform:scale(.97); }
.home-btn[aria-current] { background:transparent; color:var(--accent); box-shadow:inset 0 0 0 1px var(--accent-tint); }
.home-btn svg { width:14px; height:14px; }
main { max-width:var(--page); margin:0 auto; padding:var(--sp-7) var(--sp-6) 56px; }
header { display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:var(--sp-1) var(--sp-6); margin-bottom:var(--sp-5); }
header h1 { font-size:var(--fs-title); font-weight:var(--fw-bold); line-height:1.15; letter-spacing:-0.025em; text-wrap:balance; }
header p { font-size:13px; color:var(--muted); }

/* Cards: white floating panels */
.summary, .facts, .banner, .kpi, .card, .panel, details.acc, ul.days {
  background:var(--card); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); }
.summary { padding:var(--sp-4) var(--sp-5); font-size:var(--fs-lead); font-weight:var(--fw-semi); line-height:1.35; letter-spacing:-0.015em; }
.summary::before { content:""; display:inline-block; width:8px; height:8px; margin-right:10px; border-radius:50%;
  background:var(--ok); vertical-align:2px; }
.summary.alert::before { background:var(--bad); }
.banner { margin-top:var(--sp-3); padding:var(--sp-3) var(--sp-5); font-size:13px; }
.banner::before { content:""; display:inline-block; width:8px; height:8px; margin-right:10px; border-radius:50%;
  background:var(--bad); vertical-align:1px; }
.banner > strong:first-child { color:var(--bad); }

/* Facts: one card, label over value */
.facts { display:flex; flex-wrap:wrap; row-gap:var(--sp-3); margin-top:var(--sp-3); padding:var(--sp-4) var(--sp-1); }
.facts > div { flex:1 0 auto; padding:0 var(--sp-4); border-left:1px solid var(--hair); }
.facts > div:first-child { border-left:0; }
.facts dd { margin-top:3px; font-size:15px; font-weight:var(--fw-semi); white-space:nowrap; }
.facts dd.bad { color:var(--bad); }
.facts dd.good { color:var(--ok); }
.facts .tip { left:auto; right:0; min-width:280px; }

/* Stat cards (pulse headline numbers) */
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:var(--sp-3); margin-top:var(--sp-3); }
.kpi { padding:var(--sp-4) var(--sp-5); }
.kpi .value { margin-top:6px; font-size:var(--fs-hero); font-weight:var(--fw-bold); line-height:1.1; letter-spacing:-0.03em; }
.kpi .sub { margin-top:var(--sp-1); font-size:13px; color:var(--muted); }

/* Section titles */
.sec { display:flex; flex-wrap:wrap; align-items:baseline; gap:var(--sp-1) var(--sp-2); margin:40px 0 var(--sp-3);
  font-size:20px; font-weight:var(--fw-semi); letter-spacing:-0.02em; }
.sec .aside { font-size:13px; font-weight:var(--fw-regular); letter-spacing:-0.01em; color:var(--muted); }

/* Tables: no vertical rules, faint row lines, soft hover */
.card { overflow-x:auto; padding:var(--sp-1) 0; }
table { width:100%; min-width:640px; }
th, td { padding:11px var(--sp-4); text-align:right; vertical-align:middle; border-bottom:1px solid var(--hair); white-space:nowrap; }
th { padding-top:var(--sp-3); padding-bottom:9px; background:transparent; }
th:first-child, td:first-child { padding-left:var(--sp-5); }
th:last-child, td:last-child { padding-right:var(--sp-5); }
th:first-child, td:first-child, th.l, td.l, th.status, td.status { text-align:left; }
tbody > tr:hover > td { background:var(--hover); }
tbody > tr:last-child > td { border-bottom:0; }
tr.total > td { font-weight:var(--fw-bold); border-top:1px solid var(--line-2); border-bottom:0; background:transparent; }
td.nodata { text-align:left; color:var(--bad); font-weight:var(--fw-medium); }
td.dash { color:var(--faint); }

/* Expandable rows: the row toggles a detail row under it (script below; detail rows print) */
tr.xrow { cursor:pointer; }
.xbtn { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; margin:0 6px 0 -4px; padding:0;
  border:0; border-radius:50%; background:none; color:var(--faint); font-size:16px; line-height:1; cursor:pointer;
  transition:transform .2s ease, color .2s ease; vertical-align:-1px; }
.xbtn[aria-expanded="true"] { transform:rotate(90deg); color:var(--ink); }
.xpad { display:inline-block; width:20px; }
tr.xdetail > td { padding-top:0; background:var(--hover); text-align:left; white-space:normal; }
tr.xrow:has(+ tr.xdetail:not([hidden])) > td { background:var(--hover); border-bottom-color:transparent; }
dl.kv { display:flex; flex-wrap:wrap; gap:var(--sp-2) var(--sp-6); padding:var(--sp-1) 0 var(--sp-2) 26px; font-size:13px; }
dl.kv dt { font-size:var(--fs-label); font-weight:var(--fw-semi); letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }
dl.kv dd { font-weight:var(--fw-medium); }

/* Status pills (soft tints) and changes */
.pill { display:inline-block; height:20px; padding:0 var(--sp-2); border-radius:980px; font-size:10.5px; font-weight:var(--fw-semi);
  line-height:20px; letter-spacing:.04em; text-transform:uppercase; white-space:nowrap; background:var(--neutral-bg); color:var(--muted); }
.pill.ok { background:var(--ok-bg); color:var(--ok); }
.pill.missing, .pill.stale, .pill.unknown, .pill.bad { background:var(--bad-bg); color:var(--bad); }
.pill.warn { background:var(--warn-bg); color:var(--warn); }
.chg { font-weight:var(--fw-semi); white-space:nowrap; }
.chg.up { color:var(--ok); }
.chg.down { color:var(--bad); }

/* Info button and its popover (hover or tap; Escape closes) */
.has-tip { position:relative; }
.info { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; margin-left:3px; padding:0;
  border:0; border-radius:50%; background:none; color:var(--faint); cursor:help; vertical-align:-3px; }
.info:hover, .info:focus-visible { color:var(--accent); }
.info svg { width:14px; height:14px; display:block; }
.tip { position:absolute; z-index:40; top:calc(100% + 8px); left:0; right:0; min-width:220px; padding:10px 12px;
  background:rgba(29,29,31,.86); -webkit-backdrop-filter:blur(12px) saturate(160%); backdrop-filter:blur(12px) saturate(160%);
  color:#F5F5F7; border-radius:var(--radius-sm); box-shadow:var(--shadow-pop); font-size:12px; font-weight:var(--fw-regular);
  line-height:1.45; letter-spacing:0; text-transform:none; text-align:left; white-space:normal;
  opacity:0; visibility:hidden; transform:translateY(-4px) scale(.98); transform-origin:top left;
  transition:opacity var(--t-reveal) var(--ease-out), transform var(--t-reveal) var(--ease-out), visibility var(--t-reveal); }
.tip::before { content:""; position:absolute; left:0; right:0; top:-10px; height:10px; }
.info:hover ~ .tip, .info:focus ~ .tip, .tip:hover { opacity:1; visibility:visible; transform:none; }
.tip .k { display:block; margin-top:7px; font-size:10px; font-weight:var(--fw-semi); letter-spacing:.06em; text-transform:uppercase;
  color:rgba(245,245,247,.6); }
.tip .k:first-child { margin-top:0; }
.tip .v { display:block; }

/* Accordions: white, 12px corners, chevron, closed by default */
details.acc { margin-top:var(--sp-3); border-radius:var(--radius-sm); }
details.acc > summary { display:flex; align-items:center; gap:10px; padding:14px var(--sp-5); list-style:none; cursor:pointer;
  font-weight:var(--fw-semi); }
details.acc > summary::-webkit-details-marker { display:none; }
details.acc > summary::after { content:"\\203A"; margin-left:auto; font-size:20px; line-height:1; color:var(--faint);
  transition:transform .2s ease; }
details.acc[open] > summary::after { transform:rotate(90deg); }
details.acc > summary .meta { font-weight:var(--fw-regular); color:var(--muted); }
details.acc > summary:hover { background:var(--hover); border-radius:var(--radius-sm); }
.acc-body { padding:0 var(--sp-5) var(--sp-4); font-size:13px; color:var(--muted); }
.acc-body p + p { margin-top:var(--sp-2); }
.acc-body dl { display:grid; grid-template-columns:max-content 1fr; gap:6px var(--sp-6); }
.acc-body dt { font-weight:var(--fw-semi); color:var(--ink); }
.acc-body .card { box-shadow:none; border:0; padding:0; margin:0 calc(-1 * var(--sp-5)); }

/* Navigation, archive lists */
.nav { margin-top:var(--sp-6); font-size:13px; color:var(--muted); }
ul.days { list-style:none; padding:var(--sp-1) 0; overflow:hidden; }
ul.days li + li { border-top:1px solid var(--hair); }
ul.days a { display:flex; justify-content:space-between; padding:14px var(--sp-5); font-weight:var(--fw-medium); color:var(--ink); }
ul.days a::after { content:"\\203A"; color:var(--faint); }
ul.days a:hover { background:var(--hover); text-decoration:none; }

/* Links without their own style grow an underline from the left */
:where(main) a:where(:not([class])) { background:linear-gradient(currentColor,currentColor) left bottom / 0 1px no-repeat;
  transition:background-size var(--t-hover) var(--ease-out); }
:where(main) a:where(:not([class])):hover { background-size:100% 1px; text-decoration:none; }

/* Hover: cards that lead somewhere lift; controls press; rows and chevrons answer */
.hub-card, .file, .node, ul.days a { transition:transform var(--t-hover) var(--ease-out), box-shadow var(--t-hover) var(--ease-out), background-color var(--t-hover) var(--ease-out); }
.hub-card:hover, .file:hover { transform:translateY(-2px); box-shadow:0 10px 30px rgba(0,0,0,.06); }
ul.days a::after { transition:transform var(--t-hover) var(--ease-out); }
ul.days a:hover::after { transform:translateX(3px); }
.xbtn:active, details > summary:active, .file:active { transform:scale(.98); }
.info { transition:color var(--t-hover) var(--ease-out), transform var(--t-press) var(--ease-out); }
.info:hover { transform:scale(1.1); }
tbody > tr > td { transition:background-color var(--t-hover) var(--ease-out); }
details.acc > summary { transition:background-color var(--t-hover) var(--ease-out); }

/* Reveals: opened content settles in */
details[open] > .acc-body, details[open] > p, tr.xdetail:not([hidden]) dl.kv { animation:settle var(--t-reveal) var(--ease-out); }
@keyframes settle { from { opacity:0; transform:translateY(-4px); } }

/* Entrance: the page's blocks rise once, one after another */
main > *, .areas > *, .hub-grid > *, .kpis > *, .files > * { animation:rise var(--t-enter) var(--ease-out) both; }
main > :nth-child(2), .areas > :nth-child(2), .hub-grid > :nth-child(2), .kpis > :nth-child(2), .files > :nth-child(2) { animation-delay:50ms; }
main > :nth-child(3), .areas > :nth-child(3), .hub-grid > :nth-child(3), .kpis > :nth-child(3), .files > :nth-child(3) { animation-delay:100ms; }
main > :nth-child(4), .areas > :nth-child(4), .hub-grid > :nth-child(4), .kpis > :nth-child(4), .files > :nth-child(4) { animation-delay:150ms; }
main > :nth-child(5), .areas > :nth-child(5), .hub-grid > :nth-child(5) { animation-delay:200ms; }
main > :nth-child(6), .areas > :nth-child(6) { animation-delay:250ms; }
main > :nth-child(n+7) { animation-delay:300ms; }
@keyframes rise { from { opacity:0; transform:translateY(12px); } }

/* Lamps: a red lamp breathes slowly; green and grey stay still */
.summary.alert::before, .banner::before, .lamp.bad { animation:breathe 2.4s ease-in-out infinite; }
@keyframes breathe { 50% { opacity:.35; } }
.lamp { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--faint); vertical-align:1px; }
.lamp.ok { background:var(--ok); }
.lamp.bad { background:var(--bad); }
.lamp.warn { background:var(--warn); }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms !important; animation-delay:0s !important; animation-iteration-count:1 !important;
    transition-duration:.01ms !important; scroll-behavior:auto !important; }
}

@media (max-width:640px) {
  main { padding:var(--sp-5) var(--sp-4) 40px; }
  .topbar > div { padding:0 var(--sp-4); }
  header h1 { font-size:24px; }
  .facts > div { flex-basis:45%; }
  .facts > div:nth-child(odd) { border-left:0; }
  .acc-body dl { grid-template-columns:1fr; }
}

@media print {
  @page { size:letter portrait; margin:0.45in; }
  :root { --page:none; }
  html, body { background:#fff; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  body { font-size:8.5pt; }
  th, .label, .facts dt, dl.kv dt { font-size:6.5pt; }
  .topbar { position:static; background:none; -webkit-backdrop-filter:none; backdrop-filter:none; border-bottom:0.5pt solid #d2d2d7; }
  .topbar > div { height:auto; padding:0 0 3pt; }
  .topbar b, .topbar span { font-size:7.5pt; }
  main { padding:6pt 0 0; }
  header { margin-bottom:5pt; }
  header h1 { font-size:15pt; }
  header p { font-size:7.5pt; }
  .summary, .facts, .banner, .kpi, .card, .panel, ul.days { box-shadow:none; border-color:#d2d2d7; border-radius:8px; }
  .summary { padding:4pt 8pt; font-size:10pt; }
  .facts { margin-top:4pt; padding:4pt 0; row-gap:3pt; }
  .facts > div { padding:0 8pt; }
  .facts dd { font-size:8.5pt; margin-top:1pt; }
  .banner { margin-top:4pt; padding:3pt 8pt; font-size:8pt; }
  .kpis { margin-top:5pt; gap:5pt; }
  .kpi { padding:5pt 8pt; }
  .kpi .value { font-size:15pt; margin-top:2pt; }
  .kpi .sub { font-size:7pt; }
  .sec { margin:9pt 0 3pt; font-size:10pt; }
  .card { overflow:visible; padding:1pt 0; }
  table { min-width:0; }
  th, td { padding:3pt 6pt; }
  th:first-child, td:first-child { padding-left:8pt; }
  th:last-child, td:last-child { padding-right:8pt; }
  .pill { height:auto; line-height:9pt; padding:0 4pt; font-size:6pt; }
  tr.xdetail { display:table-row !important; }
  tr.xdetail > td { background:none; padding-bottom:3pt; }
  dl.kv { padding:0 0 0 2pt; gap:1pt 10pt; font-size:7pt; }
  tbody > tr:hover > td { background:none; }
  *, *::before, *::after { animation:none !important; transition:none !important; }
  .info, .xbtn, .xpad, .tip, details.acc, .nav, .noprint, .crumb, .tb-link { display:none !important; }
  .print-only { display:block; }
  .print-notes { display:block; margin-top:5pt; padding-top:3pt; border-top:0.5pt solid #d2d2d7; font-size:6.5pt; line-height:1.3; color:#515154; }
  .print-notes p { margin:0; }
  .print-notes sup, sup.fn { font-size:5.5pt; }
  header, .summary, .facts, .banner, .kpi, tr, .print-notes p { break-inside:avoid; }
  thead { display:table-header-group; }
  .sec { break-after:avoid; }
  a { color:inherit; }
}
@media screen { sup.fn { display:none; } }
"""

# Expandable rows and Escape for popovers. Written without "$" (this text goes through string.Template).
SCRIPT = """<script>
document.addEventListener("click", function (e) {
  if (e.target.closest("a")) return;
  var row = e.target.closest("tr.xrow"), btn = e.target.closest(".xbtn") || (row && row.querySelector(".xbtn"));
  if (!btn) return;
  var detail = document.getElementById(btn.getAttribute("aria-controls"));
  var open = btn.getAttribute("aria-expanded") !== "true";
  btn.setAttribute("aria-expanded", String(open));
  if (detail) detail.hidden = !open;
});
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape" && document.activeElement && document.activeElement.classList.contains("info")) document.activeElement.blur();
});
</script>"""

# Every page's shell. `root` is the way back to reports/ from the page: "../" for the pages in a
# subfolder (pulse/, scorecard/, close/), "" for the home page and the site map. The top bar carries
# the Home button and the site map link on every page.
HOME_ICON = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 7.4 8 2.8l5.5 4.6M4 6.3v6.9h3V9.6h2v3.6h3V6.3" '
             'fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


class Page:
    TEMPLATE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>$css</style>
</head>
<body>
<nav class="topbar" aria-label="Reports"><div>
  <a class="brand" href="${root}index.html"><b>Goodwill Michiana</b><span>E-commerce reporting</span></a>$crumb
  <span class="grow"></span>
  <a class="tb-link" href="${root}map.html"$map_current>Site map</a>
  <a class="home-btn" href="${root}index.html"$home_current>""" + HOME_ICON + """<span>Home</span></a>
</div></nav>
<main>
$body
</main>
""" + SCRIPT + """
</body>
</html>
""")

    def substitute(self, title, css, body, root="../", current="", section=None):
        """`current` is "home" or "map" on those two pages (marks the top-bar link as the page you are on);
        `section` is (label, href) for the crumb after the brand, e.g. ("Scorecards", "index.html")."""
        mark = ' aria-current="page"'
        crumb = (f'<span class="crumb"><a href="{section[1]}">{section[0]}</a></span>' if section else "")
        return self.TEMPLATE.substitute(title=title, css=css, body=body, root=root, crumb=crumb,
                                        home_current=mark if current == "home" else "",
                                        map_current=mark if current == "map" else "")


PAGE = Page()

INFO_ICON = ('<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.6" fill="none" stroke="currentColor" '
             'stroke-width="1.3"/><path d="M8 7.3v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
             '<circle cx="8" cy="4.9" r="0.95" fill="currentColor"/></svg>')

DOWNLOAD_ICON = ('<svg width="11" height="11" viewBox="0 0 10 10" aria-hidden="true"><path d="M5 0v6.5M2 3.8 5 6.8 8 3.8'
                 'M0.5 9.3h9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>')

# Email copy: Outlook desktop renders with Word, which ignores <style> variables, grid and
# border-radius. So: nested tables, every style inline on the element, web-safe fonts, hex colors.
E = {"primary": "#0054A4", "ink": "#231F20", "bg": "#ffffff", "up": "#1B8755", "down": "#D9381E",
     "muted": "#6C757D", "line": "#DEE2E6", "tint": "#F8F9FA"}
EMAIL_FONT = "font-family:Arial,Helvetica,sans-serif;"


def info(tip_id, label, pairs):
    """An info button and its popover. `pairs` are (heading, value_html); empty values are skipped.
    Place it inside an element with class "has-tip": the popover spans that element's width."""
    body = "".join(f'<span class="k">{escape(k)}</span><span class="v">{v}</span>' for k, v in pairs if v)
    return (f'<button type="button" class="info" aria-label="About {escape(label)}" aria-describedby="{tip_id}">'
            f'{INFO_ICON}</button><span class="tip" role="tooltip" id="{tip_id}">{body}</span>')


def accordion(title, body_html, meta=""):
    """A closed-by-default accordion card."""
    meta = f'<span class="meta">{meta}</span>' if meta else ""
    return f'<details class="acc"><summary>{escape(title)}{meta}</summary><div class="acc-body">{body_html}</div></details>'


def expander(detail_id):
    """The chevron button that opens a row's detail row (`<tr class="xdetail" id=... hidden>`)."""
    return (f'<button type="button" class="xbtn" aria-expanded="false" aria-controls="{detail_id}" '
            f'aria-label="Show details">›</button>')


def kv(pairs):
    """Label-over-value pairs for a detail row; empty values are skipped."""
    return '<dl class="kv">' + "".join(f"<div><dt>{escape(k)}</dt><dd>{v}</dd></div>" for k, v in pairs if v) + "</dl>"


def print_notes(lines):
    """Notes that only print: one compact line each, at the foot of the page."""
    lines = [line for line in lines if line]
    return '<div class="print-notes">' + "".join(f"<p>{line}</p>" for line in lines) + "</div>" if lines else ""


def facts(items):
    """A facts card from (label, value_html, tone) or (label, value_html, tone, tip_html) items;
    tone is "", "bad" or "good"; tip_html is an info() button shown after the label."""
    cells = []
    for name, value, tone, *tip in items:
        tip = tip[0] if tip else ""
        cls = ' class="has-tip"' if tip else ""
        dd = f'<dd class="{tone}">' if tone else "<dd>"
        cells.append(f"<div{cls}><dt>{escape(name)}{tip}</dt>{dd}{value}</dd></div>")
    return f'<dl class="facts">{"".join(cells)}</dl>'


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
