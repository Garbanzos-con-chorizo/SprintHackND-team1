"""The list pages (Daily Reports, COO Scorecards, Month-end Close): a place to find a report, not a file listing.

Each list page is a row of headline tiles, a finder (a search box and a few filter buttons) and one table with a
row per report: its key figures, the state of its data and its files. The three pages build their rows from the
files beside the reports and call `tiles` and `finder_table` here, so they look and behave the same.

The finder is the only script in the generated pages: about twenty lines, inline, no dependency. It hides rows; it
loads nothing and computes nothing. Without it the page is still the full table.
"""
from html import escape

LIBRARY_CSS = """
.finder { display:flex; flex-wrap:wrap; align-items:center; gap:10px 14px; margin:16px 0 10px; }
.finder input { flex:1 1 260px; max-width:420px; font:inherit; padding:8px 12px; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--card); color:var(--ink); }
.finder input:focus-visible, .chip:focus-visible { outline:2px solid var(--primary); outline-offset:1px; }
.chips { display:flex; flex-wrap:wrap; gap:6px; }
.chip { font:inherit; font-size:14px; padding:5px 12px; border:1px solid var(--line); border-radius:999px;
  background:var(--card); color:var(--ink); cursor:pointer; }
.chip[aria-pressed="true"] { background:var(--primary); border-color:var(--primary); color:#fff; font-weight:600; }
.finder .count { margin-left:auto; font-size:14px; color:var(--muted); }
.kpi .value a { color:var(--ink); text-decoration:none; }
.kpi .value a:hover { text-decoration:underline; }
table.lib td { white-space:normal; vertical-align:top; }
table.lib .num { white-space:nowrap; text-align:right; }
table.lib .l, table.lib th.say, table.lib th.files { text-align:left; }
table.lib td:first-child { white-space:nowrap; }
table.lib td:first-child a { font-weight:700; }
table.lib td strong { white-space:nowrap; }
table.lib td small { display:block; color:var(--muted); font-size:13px; font-weight:400; }
table.lib tr.group td { background:var(--bg); color:var(--primary); font-size:13px; font-weight:700;
  text-transform:uppercase; letter-spacing:.05em; padding:6px 12px; }
table.lib td.say { text-align:left; color:var(--muted); font-size:14px; min-width:220px; max-width:380px; }
table.lib td.files { text-align:left; white-space:nowrap; font-size:14px; }
table.lib td.files a + a { margin-left:10px; }
table.lib td .pill { white-space:nowrap; margin:0 4px 3px 0; }
table.lib tbody tr[data-find]:hover td { background:#f8f9fb; }
.nomatch { color:var(--muted); margin:12px 0 0; }
[hidden] { display:none !important; }
@media print { .finder { display:none; } }
"""

# Hides the rows that don't match the search words and the chosen filter, and a group heading with no row left.
SCRIPT = """<script>
(function () {
  var box = document.querySelector(".finder input"), chips = [].slice.call(document.querySelectorAll(".chip"));
  var rows = [].slice.call(document.querySelectorAll("table.lib tr[data-find]")), tag = "";
  function run() {
    var words = box.value.toLowerCase().split(/\\s+/).filter(Boolean), shown = 0;
    rows.forEach(function (r) {
      var ok = (!tag || (" " + r.dataset.tags + " ").indexOf(" " + tag + " ") >= 0) &&
        words.every(function (w) { return r.dataset.find.indexOf(w) >= 0; });
      r.hidden = !ok;
      shown += ok ? 1 : 0;
    });
    [].forEach.call(document.querySelectorAll("table.lib tr.group"), function (g) {
      var any = false;
      for (var s = g.nextElementSibling; s && !s.classList.contains("group"); s = s.nextElementSibling) any = any || !s.hidden;
      g.hidden = !any;
    });
    document.querySelector(".finder .count").textContent = shown + " of " + rows.length;
    document.querySelector(".nomatch").hidden = shown > 0;
  }
  box.addEventListener("input", run);
  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      tag = c.dataset.tag;
      chips.forEach(function (x) { x.setAttribute("aria-pressed", x === c ? "true" : "false"); });
      run();
    });
  });
})();
</script>"""


def tiles(items):
    """The headline tiles: (label, value, the line under it, link or None). Text is escaped here."""
    def one(label, value, sub, href):
        shown = f'<a href="{escape(href)}">{escape(value)}</a>' if href else escape(value)
        return (f'<div class="kpi"><div class="label">{escape(label)}</div><div class="value">{shown}</div>'
                f'<div class="sub muted">{escape(sub)}</div></div>')
    return '<div class="kpis">' + "".join(one(*item) for item in items) + "</div>"


def finder_table(columns, groups, filters, hint, noun="report"):
    """The finder and the table.

    columns: (heading, class) with class "num" (right, one line) or "l" (left).
    groups: (heading, rows); a row is {"cells": [html per column], "find": words to search, "tags": "a b"}.
    filters: (tag, label) for the filter buttons; each shows how many rows carry its tag.
    """
    rows = [r for _, found in groups for r in found]
    if not rows:
        return f'<p class="nomatch">No {noun} yet.</p>'
    chips = [f'<button class="chip" type="button" data-tag="" aria-pressed="true">All {len(rows)}</button>']
    for tag, label in filters:
        count = sum(tag in r.get("tags", "").split() for r in rows)
        if count:
            chips.append(f'<button class="chip" type="button" data-tag="{tag}" aria-pressed="false">{escape(label)} {count}</button>')
    head = "".join(f'<th class="{cls}">{escape(name)}</th>' for name, cls in columns)
    body = []
    for heading, found in groups:
        if heading and found:
            body.append(f'<tr class="group"><td colspan="{len(columns)}">{escape(heading)}</td></tr>')
        for r in found:
            cells = "".join(f'<td class="{cls}">{cell}</td>' for (_, cls), cell in zip(columns, r["cells"]))
            body.append(f'<tr data-find="{escape(r["find"].lower())}" data-tags="{escape(r.get("tags", ""))}">{cells}</tr>')
    return (f'<div class="finder"><input type="search" placeholder="{escape(hint)}" aria-label="Find a {noun}">'
            f'<div class="chips">{"".join(chips)}</div><span class="count">{len(rows)} of {len(rows)}</span></div>'
            f'<div class="card"><table class="lib"><thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(body)
            + f'\n</tbody></table></div><p class="nomatch" hidden>No {noun} matches. Clear the search or choose All.</p>'
            + SCRIPT)
