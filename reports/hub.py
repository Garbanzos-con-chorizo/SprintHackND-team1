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

from reports import charts, library
from reports.pulse import CSS, DATA_LABEL, DATA_NOTE, PAGE, ast, notes, stamp

ROOT = Path(__file__).resolve().parent.parent

HUB_CSS = """
/* One card per report, set well apart: a colored band names it, red when its latest page flags missing data. */
.hub-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(420px,100%),1fr)); gap:28px; margin:28px 0 0; }
.hub-card { background:var(--card); border:1px solid #b9bcc2; border-radius:10px; overflow:hidden;
  box-shadow:0 3px 10px rgba(35,31,32,.10); }
.hub-card .band { display:flex; align-items:center; justify-content:space-between; gap:10px; background:var(--primary);
  color:#fff; padding:9px 18px; font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; }
.hub-card.alert .band { background:var(--down); }
.hub-card.empty .band { background:var(--muted); }
.hub-card .flagged { background:#fff; color:var(--down); border-radius:999px; padding:1px 10px; font-size:11px; white-space:nowrap; }
.hub-card .in { padding:14px 18px 16px; }
.hub-card h2 { font-size:22px; margin:0 0 6px; }
.hub-card h2 a { color:var(--ink); }
.hub-card .headline { margin:0 0 12px; font-weight:600; }
.hub-card .actions { margin:0; }
.hub-card .links, .hub-card .built { font-size:14px; color:var(--muted); margin:8px 0 0; }
.hub-card .links { line-height:1.8; }
.hub-card details { margin-top:10px; font-size:14px; }
.hub-card details summary { cursor:pointer; color:var(--primary); font-weight:600; }
/* The two charts: revenue by night (wide) and the week's split by marketplace. */
.charts { display:grid; grid-template-columns:minmax(0,1.7fr) minmax(0,1fr); gap:20px; margin:18px 0 0; align-items:stretch; }
@media (max-width:860px) { .charts { grid-template-columns:1fr; } }
.chart { padding:14px 16px 12px; overflow:visible; }
.chart h2.sec { margin:0 0 6px; }
.chart .hint { margin:8px 0 0; font-size:13px; color:var(--muted); }
/* Revenue by night: plain HTML columns, no script. A 2px gap in the card color separates the segments. */
.trend-head { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:4px 16px; }
.trend-head h2.sec { margin:0 0 6px; }
.legend { display:flex; flex-wrap:wrap; gap:4px 16px; font-size:13px; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; }
.trend { padding:14px 16px 12px; overflow:visible; }
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
@media print {
  .seg, .legend i { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  @page { size:letter portrait; margin:0.5in; }
  .hub-grid { grid-template-columns:repeat(2,1fr); gap:10px; margin-top:10px; }
  .hub-card { break-inside:avoid; box-shadow:none; }
  .hub-card .band { padding:4px 10px; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  .hub-card .in { padding:6px 10px; }
  .hub-card h2 { font-size:12pt; }
  .hub-card .links, .hub-card details { display:none; }
  .charts { gap:10px; }
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


# What the portal shows: folder, page name pattern, how to name the period, related files. The first two
# files of a card are buttons; the rest sit under "More".
BUTTONS = 2
SUITE = [
    {"title": "Daily Report · Nightly Pulse", "what": "Revenue and customers by marketplace for the day that just ended.",
     "folder": "pulse", "pattern": r"\d{4}-\d{2}-\d{2}", "period": _long_day,
     "extras": lambda s: [(f"{s}.xlsx", "Full Day (Excel)"), (f"{s}.csv", "CSV"), (f"{s}.email.html", "Email copy")],
     "archive": ("index.html", "All days"),
     "build": "python -m reports.run_nightly --scenario gw_day_clean"},
    {"title": "Weekly Dashboard", "what": "The week's 15 KPIs in five areas, from the KPI file.",
     "folder": "scorecard", "pattern": r"week-\d{4}-W\d{2}", "period": lambda s: _week(s[5:]),
     "extras": lambda s: [(f"{s}.csv", "KPI table (CSV)"), (f"{s}.pdf", "PDF"), (f"{s}.json", "KPI file")],
     "archive": ("index.html", "All scorecards"),
     "build": "python -m recon.kpi --week 2026-W38, then python -m reports.weekly --week 2026-W38"},
    {"title": "COO Scorecard (Monthly)", "what": "Goodwill's 15 KPIs in five areas, from the KPI file.",
     "folder": "scorecard", "pattern": r"month-\d{4}-\d{2}", "period": lambda s: _month(s[6:]),
     "extras": lambda s: [(f"{s}.csv", "KPI table (CSV)"), (f"{s}.pdf", "PDF"), (f"{s}.json", "KPI file"),
                          (f"../monthly/{s[6:]}.csv", "Daily CSV"),
                          (f"../monthly/index.html?month={s[6:]}", "Daily table", f"../monthly/{s[6:]}.json")],
     "archive": ("index.html", "All scorecards"),
     "switch": [("day", "Day"), ("week", "Week to date"), ("month", "Month to date")],
     "previous": "Previous month",
     "build": "python -m recon.kpi --month 2026-09, then python -m reports.monthly --month 2026-09"},
    {"title": "Month-End Close", "what": "Export files for Business Central, reconciliation and exceptions.",
     "folder": "close", "pattern": r"\d{4}-\d{2}", "period": _month,
     "extras": lambda s: [(f"{s}/general_journal_{s}.csv", "General Journal"), (f"{s}/ar_invoice_{s}.csv", "AR invoice"),
                          (f"{s}/control_totals_{s}.csv", "Control totals"), (f"{s}/exceptions_{s}.csv", "Exceptions"),
                          (f"{s}/close_status_{s}.json", "Run status"), (f"{s}/runs.csv", "Run history"),
                          ("index.html#add", "Add missing reports", "index.html")],
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
    """One report's card: the band that names it, the latest period, its headline in a few words, a button to
    open it and one per main file. Everything else (other files, earlier periods, what it is, when it was
    built) is under "More"."""
    folder = root / item["folder"]
    pages = sorted(f for f in folder.glob("*.html") if re.fullmatch(item["pattern"], f.stem)) if folder.is_dir() else []
    if not pages:
        return (f'<div class="hub-card empty"><div class="band"><span>{item["title"]}</span></div><div class="in">'
                f'<h2>Not Built Yet</h2><p class="links">Build it with <code>{escape(item["build"])}</code></p></div></div>')
    latest = pages[-1]
    text, alert = headline(latest)
    href = f'{item["folder"]}/{latest.name}'
    # An extra is (file, label) or (link, label, the file that must exist for the link to work).
    found = [(name, label) for name, label, *needs in item["extras"](latest.stem)
             if (folder / (needs[0] if needs else name)).exists()]
    buttons = "".join(f'<a class="btn quiet small dl" href="{item["folder"]}/{name}">{label}</a>' for name, label in found[:BUTTONS])
    links = [f'<a href="{item["folder"]}/{name}">{label}</a>' for name, label in found[BUTTONS:]]
    if item["archive"] and (folder / item["archive"][0]).exists():
        links.append(f'<a href="{item["folder"]}/{item["archive"][0]}">{item["archive"][1]} ({len(pages)})</a>')
    elif len(pages) > 1:
        links.append("Earlier: " + ", ".join(f'<a href="{item["folder"]}/{p.name}">{escape(item["period"](p.stem))}</a>'
                                             for p in reversed(pages[:-1])))
    if item.get("previous") and len(pages) > 1:
        before = pages[-2]
        links.insert(0, f'{item["previous"]}: <a href="{item["folder"]}/{before.name}">{escape(item["period"](before.stem))}</a>')
    switch = ""
    if item.get("switch"):
        switch = ('<p class="links">Period: ' + " · ".join(_period_link(item, folder, kind, label) for kind, label in item["switch"])
                  + "</p>")
    built = datetime.fromtimestamp(latest.stat().st_mtime)
    short = text.split(";")[0].rstrip(".")  # the first thing the page says; the whole sentence is under "More"
    more = (f'<details><summary>More</summary><p class="links">{escape(text)}</p>'
            + (f'<p class="links">{" · ".join(links)}</p>' if links else "")
            + f'<p class="built">{escape(item["what"])} Built {stamp(built.isoformat())}.</p></details>')
    flagged = '<span class="flagged">Missing Data</span>' if alert else ""
    return (f'<div class="hub-card{" alert" if alert else ""}"><div class="band"><span>{item["title"]}</span>{flagged}</div>'
            f'<div class="in"><h2><a href="{href}">{escape(item["period"](latest.stem))}</a></h2>'
            f'<p class="headline">{escape(short)}</p>'
            f'<div class="actions"><a class="btn small" href="{href}">Open Report</a>{buttons}</div>'
            f'{switch}{more}</div></div>')


# Marketplace colors for the chart, bottom of the column first. Checked as a set for color-blind
# separation on white; none is the green or red the pages use for change and missing data.
SERIES = [(name, charts.COLORS[name]) for name in ("ShopGoodwill", "Amazon", "eBay")]
PLOT_PX = 170


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
    tip = "Sales minus refunds, before marketplace fees; a night with a missing file shows only what reported"
    return (f'<div class="card trend"><div class="trend-head"><h2 class="sec">Revenue by Night · Last {len(days)} Nights{ast(tip)}</h2>'
            f'<div class="legend">{legend}</div></div>'
            f'<div class="plot" style="height:{PLOT_PX}px">{ticks}'
            f'<div class="cols">{"".join(cols)}</div></div><div class="xlabels">{"".join(labels)}</div>'
            f'<p class="hint">Select a bar to open that night\'s report.</p></div>')


def week_pie(root):
    """The latest week's revenue by marketplace, as a pie: the nights on file of the ISO week (Monday to Sunday)
    of the latest night. A marketplace with no data on a night adds nothing for that night; one with no data
    all week is not drawn. "" when there is no night on file."""
    days = nights(root)
    if not days:
        return ""
    latest = date.fromisoformat(days[-1][0])
    year, week, _ = latest.isocalendar()
    monday = date.fromisocalendar(year, week, 1)
    mine = [(day, rev, gaps) for day, rev, gaps in days if date.fromisoformat(day).isocalendar()[:2] == (year, week)]
    totals = {name: sum(rev.get(name, 0) for _, rev, _ in mine) for name, _ in SERIES}
    drawn = charts.pie([(name, color, totals[name]) for name, color in SERIES], f"${sum(totals.values()):,.0f}",
                       f"{len(mine)} night{'s' if len(mine) != 1 else ''}")
    if not drawn:
        return ""
    gaps = sum(bool(g) for _, _, g in mine)
    tip = (f"Nights on file from {monday:%b} {monday.day} to {latest:%b} {latest.day}"
           + (f"; {gaps} with a missing file count only what reported" if gaps else ""))
    return (f'<div class="card chart"><h2 class="sec">Week {week} by Marketplace{ast(tip)}</h2>{drawn}</div>')


CLOSE_FILES = [("general_journal", "General Journal"), ("ar_invoice", "AR Invoice"), ("control_totals", "Control Totals"),
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
    files = "".join(f'<a class="btn small dl" href="{month}/{key}_{month}.csv" download title="Download {name} (CSV)">{name}</a>'
                    for key, name in CLOSE_FILES if (folder / month / f"{key}_{month}.csv").exists())
    return {"cells": [f'<a href="{month}.html">{escape(_month(month))}</a>', pills, f"{len(exceptions)}",
                      "<strong>Not posted</strong><small>export files only</small>", files],
            "find": f'{_month(month)} {month} {" ".join(r["Source"] + " " + r["Status"] for r in control)} not posted',
            "tags": "review" if review else "clean", "exceptions": len(exceptions)}


ADD_CSS = """
.addfiles { padding:14px 16px; margin:0 0 4px; overflow:visible; }
.addfiles h2.sec { margin:0 0 6px; }
.addfiles p, .addfiles ul { margin:6px 0; font-size:15px; }
.addfiles ul { padding-left:20px; }
.addrow { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin:10px 0 4px; }
.addrow input[type=file] { font:inherit; font-size:14px; max-width:100%; }
/* The export files of a month: one button each, in a column that wraps. */
table.lib td.files { white-space:normal; min-width:300px; }
table.lib td.files a.btn { margin:0 6px 6px 0; }
table.lib td.files a + a { margin-left:0; }
#add-state { min-height:1.5em; font-weight:600; }
#add-state.bad { color:var(--down); }
.addfiles .small { font-size:13px; color:var(--muted); }
@media print { .addfiles { display:none; } }
"""

# The panel's script: sends each chosen file to the server, asks it to run the close again, reloads the page.
# The server does the work (reports.close_upload); opened from disk, the panel says it needs the server.
ADD_SCRIPT = """<script>
(function () {
  var box = document.getElementById("add");
  if (!box) return;
  var api = "../api/close/" + box.dataset.month, head = { "X-Reports": "1" };
  var pick = document.getElementById("add-files"), run = document.getElementById("add-run");
  var clear = document.getElementById("add-clear"), state = document.getElementById("add-state");
  function say(text, bad) { state.textContent = text; state.className = bad ? "bad" : ""; }
  function off(text) { pick.disabled = run.disabled = true; clear.hidden = true; say(text); }
  function json(r) { return r.json(); }
  function again() { return fetch(api + "/run", { method: "POST", headers: head }).then(json).then(function (d) {
    if (!d.ok) throw new Error(d.error || (d.log || []).slice(-2).join(" ") || "the close did not run");
    say("Done. Loading the new result...");
    location.reload();
  }); }
  function fail(e) { run.disabled = clear.disabled = false; say("Not done: " + e.message, true); }
  if (location.protocol === "file:") return off("Adding files needs the report server: run python server.py and open http://127.0.0.1:8000/");
  fetch(api + "/uploads").then(json).then(function (d) {
    if (!d.enabled) return off("Adding files is switched off on this server.");
    clear.hidden = !(d.files || []).length;
    if (!clear.hidden) say("Added so far: " + d.files.join(", "));
  }).catch(function () { off("Adding files needs the report server (python server.py)."); });
  run.addEventListener("click", function () {
    var files = [].slice.call(pick.files);
    if (!files.length) return say("Choose the report files first.", true);
    run.disabled = true;
    say("Adding " + files.length + " file(s)...");
    files.reduce(function (before, f) { return before.then(function () {
      return fetch(api + "/uploads/" + encodeURIComponent(f.name), { method: "PUT", headers: head, body: f }).then(json)
        .then(function (d) { if (!d.ok) throw new Error(d.error || d.detail || "the file was not accepted"); });
    }); }, Promise.resolve()).then(function () { say("Running the close again..."); return again(); }).catch(fail);
  });
  clear.addEventListener("click", function () {
    clear.disabled = true;
    say("Removing the added files and running the close again...");
    fetch(api + "/uploads", { method: "DELETE", headers: head }).then(json).then(again).catch(fail);
  });
})();
</script>"""


def add_panel(folder, month):
    """The "add missing reports" panel for the latest month: which reports the close says are missing (from its
    exceptions file), a file picker and a button. The files go to the server, which runs the close again."""
    missing = [e for e in _rows(folder / month / f"exceptions_{month}.csv") if e.get("Kind") == "missing_report"]
    if missing:
        what = ("<p>The close could not check these days, because no report covers them:</p><ul>"
                + "".join(f'<li><strong>{escape(e.get("Source") or "A source")}:</strong> {escape(e.get("Detail") or "")}</li>'
                          for e in missing) + "</ul>")
    else:
        what = f"<p>No report is missing for {escape(_month(month))}. A late file can still be added.</p>"
    return (f'<section class="card addfiles" id="add" data-month="{month}">'
            f'<h2 class="sec">Add Missing Reports · {escape(_month(month))}</h2>{what}'
            f'<p>Download the report from the marketplace and add it here: the close runs again with it and this page '
            f'shows the new result. Nothing is posted.</p>'
            f'<div class="addrow"><input type="file" id="add-files" multiple accept=".csv,.xlsx" aria-label="Report files to add">'
            f'<button class="btn" id="add-run" type="button">Add files and run the close again</button>'
            f'<button class="btn quiet" id="add-clear" type="button" hidden>Remove the added files and run again</button></div>'
            f'<p id="add-state" role="status"></p>'
            f'<p class="small"><strong>{DATA_LABEL}:</strong> in the demo the late reports are the synthetic samples in '
            f'<code>data/sample/messy_month/late/</code>. Added files are kept in <code>out/uploads/{month}/</code>; '
            f'the sample folders are not changed.</p></section>')


def close_index(root):
    """<root>/close/index.html, the Month-end Close page: every month closed, newest first, with each source's
    reconciliation status, its exceptions and its export files for Business Central; and, for the latest month,
    the panel to add the reports that were missing (decision 010)."""
    folder = root / "close"
    folder.mkdir(parents=True, exist_ok=True)
    months = sorted((f.stem for f in folder.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}", f.stem)), reverse=True)
    rows = [_close_row(folder, m) for m in months]
    panel = add_panel(folder, months[0]) + ADD_SCRIPT if months else ""
    top = library.tiles([
        ("Latest Close", _month(months[0]), "", f"{months[0]}.html"),
        ("Exceptions to Work", f'{rows[0]["exceptions"]}', f"in {_month(months[0])}", f"{months[0]}.html"),
        ("Posting Status", "Not posted", "export files only; nothing is sent", None)]) if months else ""
    table = library.finder_table(
        [("Month", "l"), ("Reconciliation by Source", "l"), ("Exceptions", "num"), ("Posting", "l"),
         ("Export Files for Business Central", "files")],
        [("", rows)], [("review", "Needs review"), ("clean", "Reconciled")],
        'Find a month: "September", "2026-09", "incomplete"', noun="close")
    body = (f'<header><h1>Month-End Close</h1><p>{len(months)} month(s) · export files for Business Central, not posted</p>'
            f'</header>{top}{panel}{table}')
    css = CSS + library.LIBRARY_CSS + ADD_CSS + ".pill.stale { background:var(--ink); color:#fff; }"
    (folder / "index.html").write_text(PAGE.substitute(title="Month-End Close", css=css, body=body), encoding="utf-8")


def build(root=ROOT / "reports"):
    """Write <root>/index.html (and the close's list of months) and return the portal's path."""
    root = Path(root)
    close_index(root)
    cards = [card(root, item) for item in SUITE]
    bars, pie = trend(root), week_pie(root)
    band = f'<div class="charts">{bars}{pie}</div>' if bars and pie else bars or pie
    about = notes([
        ("", f'<p><strong>{DATA_LABEL}.</strong> Every figure on these pages comes from synthetic sample files and '
             f'simulated APIs: {DATA_NOTE}. KPIs marked "Simulated internal data" use a mock of Goodwill\'s internal '
             f'systems. The month-end close writes export files for Business Central: nothing is posted.</p>'),
        ("Charts", '<p>Revenue is as on the nightly pulse: sales minus refunds, before marketplace fees. A night with a '
                   'missing file shows only the marketplaces that reported; no data is never drawn as zero. The pie adds '
                   'up the nights on file of the latest week, Monday to Sunday.</p>'),
        ("Cards", '<p>A red band and "Missing Data": the report\'s latest page flags missing data or partial totals. '
                  '"More" on a card holds its other files and earlier periods.</p>')], title="About This Data")
    body = (f'<header><h1>Latest Reports</h1>'
            f'<p>Updated {stamp(datetime.now().isoformat())}</p></header>'
            f'{band}'
            f'<div class="hub-grid">\n' + "\n".join(cards) + f'\n</div>{about}')
    path = root / "index.html"
    path.write_text(PAGE.substitute(title="E-Commerce Reports", css=CSS + charts.CHART_CSS + HUB_CSS, body=body, root=""), encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT / "reports"), help="folder holding pulse/, weekly/, monthly/")
    args = ap.parse_args(argv)
    print(f"wrote {build(args.root)}")


if __name__ == "__main__":
    main()
