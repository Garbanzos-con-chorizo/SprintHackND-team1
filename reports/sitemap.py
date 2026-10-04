"""Site map and link check for the report suite: reports/map.html.

Starts at reports/index.html and follows every link. On each page it checks that

- every link (`<a href>`) resolves: to a page or file that exists under reports/, or to an anchor on the page;
- every row expander (`aria-controls`) and info button (`aria-describedby`) points at an element that exists;
- the page has a way home, a link to reports/index.html (the top bar's Home button). The email copies are
  exempt: they are written for Outlook, where a relative link goes nowhere.

Then it writes reports/map.html: the pages as cards, one column per section, the links between sections drawn
as lines, the files each page offers, and every problem found. Pages that exist but that nothing links to are
listed as unlinked. The top bar's Home and Site map links are shown as badges, not lines, so the drawing stays
readable.

    python -m reports.sitemap [--root reports]      # exit 1 when a link or a control is broken
"""
import argparse
import json
import re
from collections import deque
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from reports.theme import CSS, PAGE, accordion, facts

ROOT = Path(__file__).resolve().parent
SECTIONS = {"": "Home", "pulse": "Nightly pulse", "scorecard": "Scorecards", "close": "Month-end close",
            "monthly": "Monthly dashboard"}
FILE_KINDS = {".csv": "CSV", ".json": "JSON", ".pdf": "PDF", ".eml": "Email", ".xlsx": "Excel"}
MAP = "map.html"

MAP_CSS = """
:root { --page:1440px; }
.map { position:relative; display:grid; grid-template-columns:repeat(var(--cols),minmax(200px,1fr)); gap:var(--sp-7);
  margin-top:var(--sp-6); padding:var(--sp-2) 0; }
.map svg.edges { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; overflow:visible; }
.edge { fill:none; stroke:var(--accent); stroke-opacity:.28; stroke-width:1.5; stroke-dasharray:1; stroke-dashoffset:1;
  animation:draw 900ms var(--ease-out) forwards; animation-delay:calc(var(--i, 0) * 25ms + 300ms);
  transition:stroke-opacity var(--t-hover) var(--ease-out), stroke-width var(--t-hover) var(--ease-out); }
@keyframes draw { to { stroke-dashoffset:0; } }
.map.focus .edge { stroke-opacity:.06; }
.map.focus .edge.on { stroke-opacity:.9; stroke-width:2; }
.col h2 { margin-bottom:var(--sp-3); }
.col .count { color:var(--faint); font-weight:var(--fw-regular); }
.node { position:relative; z-index:1; margin-bottom:var(--sp-3); padding:var(--sp-3) var(--sp-4); background:var(--card);
  border:1px solid var(--line); border-radius:var(--radius-sm); box-shadow:var(--shadow);
  transition:opacity .2s ease, transform .2s ease, box-shadow .2s ease; }
.node:hover { transform:translateY(-1px); box-shadow:0 8px 24px rgba(0,0,0,.07); }
.map.focus .node { opacity:.35; }
.map.focus .node.on { opacity:1; }
.node.bad { box-shadow:inset 3px 0 0 var(--bad), var(--shadow); }
.node a.title { display:block; font-weight:var(--fw-semi); color:var(--ink); line-height:1.3; }
.node .path { margin-top:2px; font:12px var(--mono); color:var(--faint); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.node .chips { display:flex; flex-wrap:wrap; gap:4px; margin-top:var(--sp-2); }
.chip { display:inline-block; max-width:100%; height:20px; padding:0 8px; border-radius:980px; font-size:11px; line-height:20px;
  font-weight:var(--fw-medium); background:var(--neutral-bg); color:var(--ink); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
  transition:background-color var(--t-hover) var(--ease-out); }
a.chip:hover { background:var(--accent-tint); text-decoration:none; }
.chip::before { content:""; display:inline-block; width:6px; height:6px; margin-right:5px; border-radius:50%; background:var(--ok); vertical-align:1px; }
.chip.broken { background:var(--bad-bg); color:var(--bad); }
.chip.broken::before { background:var(--bad); }
.chip.home::before, .chip.nohome::before { display:none; }
.chip.nohome { background:var(--bad-bg); color:var(--bad); }
.node .meta { margin-top:6px; font-size:12px; color:var(--muted); }
.node .problems { margin:6px 0 0; padding-left:16px; font-size:12px; color:var(--bad); }
.legend { display:flex; flex-wrap:wrap; gap:var(--sp-2) var(--sp-5); margin-top:var(--sp-3); font-size:12px; color:var(--muted); }
.legend .line { display:inline-block; width:22px; height:0; border-top:2px solid var(--accent); opacity:.5; vertical-align:middle; margin-right:6px; }
table.links td.l, table.links th.l { text-align:left; }
table.links td { white-space:normal; }
table.links .ok { color:var(--ok); font-weight:var(--fw-semi); }
table.links .broken { color:var(--bad); font-weight:var(--fw-semi); }
@media (max-width:900px) { .map { grid-template-columns:1fr; gap:var(--sp-4); } .map svg.edges { display:none; } }
@media print { .map { gap:10pt; } .map svg.edges { display:none; } .node { box-shadow:none; } }
"""

# Draws a curve for each link between sections, from the right of one card to the left of the other;
# hovering a card lights up its lines and the cards it connects to.
MAP_JS = """<script>
(function () {
  var map = document.querySelector(".map"), svg = map && map.querySelector("svg.edges");
  if (!svg) return;
  var edges = JSON.parse(document.getElementById("map-edges").textContent);
  function node(id) { return document.getElementById(id); }
  function draw() {
    var box = map.getBoundingClientRect();
    svg.innerHTML = "";
    edges.forEach(function (e, i) {
      var a = node(e[0]), b = node(e[1]);
      if (!a || !b) return;
      var ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      var x1 = ra.right - box.left, y1 = ra.top + ra.height / 2 - box.top;
      var x2 = rb.left - box.left, y2 = rb.top + rb.height / 2 - box.top;
      if (x2 < x1) { x1 = ra.left - box.left; x2 = rb.right - box.left; }
      var dx = Math.max(40, Math.abs(x2 - x1) / 2) * (x2 >= x1 ? 1 : -1);
      var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", "M" + x1 + " " + y1 + " C" + (x1 + dx) + " " + y1 + " " + (x2 - dx) + " " + y2 + " " + x2 + " " + y2);
      p.setAttribute("class", "edge");
      p.setAttribute("pathLength", "1");
      p.dataset.a = e[0]; p.dataset.b = e[1];
      p.style.setProperty("--i", i);
      svg.appendChild(p);
    });
  }
  function focus(id) {
    map.classList.toggle("focus", !!id);
    map.querySelectorAll(".node").forEach(function (n) { n.classList.remove("on"); });
    svg.querySelectorAll(".edge").forEach(function (p) {
      var on = id && (p.dataset.a === id || p.dataset.b === id);
      p.classList.toggle("on", !!on);
      if (on) { node(p.dataset.a).classList.add("on"); node(p.dataset.b).classList.add("on"); }
    });
    if (id) node(id).classList.add("on");
  }
  map.querySelectorAll(".node").forEach(function (n) {
    n.addEventListener("mouseenter", function () { focus(n.id); });
    n.addEventListener("mouseleave", function () { focus(null); });
    n.addEventListener("focusin", function () { focus(n.id); });
    n.addEventListener("focusout", function () { focus(null); });
  });
  draw();
  window.addEventListener("resize", draw);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
})();
</script>"""


class PageParser(HTMLParser):
    """Links (href and text), element ids, the buttons that point at an element, and the title/h1."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.controls = [], set(), []
        self.title = self.h1 = ""
        self._href, self._text, self._in, self._buf = None, [], None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href") is not None:
            self._href, self._text = a["href"], []
        if tag == "button":
            for attr in ("aria-controls", "aria-describedby"):
                if a.get(attr):
                    self.controls.append((attr, a[attr], a.get("aria-label", "")))
        if tag in ("title", "h1") and not getattr(self, tag):
            self._in, self._buf = tag, []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)
        if self._in:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
        if tag == self._in:
            setattr(self, tag, " ".join("".join(self._buf).split()))
            self._in = None


def section(rel):
    return rel.split("/")[0] if "/" in rel else ""


def check_page(path, root):
    """One page's links and controls, with what is wrong on it."""
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    rel = path.relative_to(root).as_posix()
    page = {"path": rel, "title": parser.h1 or parser.title or rel, "links": [], "problems": [], "home": False,
            "email": rel.endswith(".email.html"), "controls": len(parser.controls)}
    for href, text in parser.links:
        parts = urlsplit(href)
        if parts.scheme or parts.netloc:
            page["links"].append({"href": href, "text": text, "target": href, "kind": "external", "ok": True})
            continue
        if not parts.path:
            ok = unquote(parts.fragment) in parser.ids
            page["links"].append({"href": href, "text": text, "target": f"{rel}{href}", "kind": "anchor", "ok": ok})
            if not ok:
                page["problems"].append(f"Anchor {href} is not on the page")
            continue
        target = (path.parent / unquote(parts.path)).resolve()
        inside = target == root or root in target.parents
        trel = target.relative_to(root).as_posix() if inside else href
        ok = inside and (target.is_file() or trel == MAP)  # the map is the page this command writes
        kind = "page" if target.suffix == ".html" else FILE_KINDS.get(target.suffix, target.suffix.lstrip(".").upper() or "file")
        page["links"].append({"href": href, "text": text, "target": trel, "kind": kind, "ok": ok})
        if not ok:
            page["problems"].append(f"Broken link “{text or href}” to {href}")
        elif trel == "index.html":
            page["home"] = True
    for attr, ref, label in parser.controls:
        if ref not in parser.ids:
            page["problems"].append(f"Button “{label or attr}” points at #{ref}, which is not on the page")
    if not page["home"] and not page["email"]:
        page["problems"].append("No way back to the home page")
    return page


def crawl(root=ROOT):
    """Every page reachable from index.html, checked; and the pages nothing links to."""
    root = Path(root).resolve()
    start = root / "index.html"
    pages, queue, seen = {}, deque([start]), {start}
    while queue:
        path = queue.popleft()
        if not path.is_file() or path == root / MAP:  # the map is checked after it is written (build)
            continue
        page = check_page(path, root)
        pages[page["path"]] = page
        for link in page["links"]:
            if link["kind"] == "page" and link["ok"]:
                target = (root / link["target"]).resolve()
                if target not in seen and target.is_file():
                    seen.add(target)
                    queue.append(target)
    unlinked = sorted(f.relative_to(root).as_posix() for f in root.rglob("*.html")
                      if f.resolve() not in seen and "tests" not in f.parts)
    return pages, unlinked


def node_id(rel):
    return "n-" + re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-")


def node_html(page, pages):
    files = [] if page["path"] == MAP else [link for link in page["links"] if link["kind"] not in ("page", "anchor", "external")]
    emails = [] if page["path"] == MAP else [link for link in page["links"] if link["kind"] == "page" and link["ok"]
                                             and pages.get(link["target"], {}).get("email")]
    seen, chips = set(), []
    for link in files + emails:
        if link["target"] in seen:
            continue
        seen.add(link["target"])
        text = link["text"] if link["text"] and len(link["text"]) <= 24 else link["target"].rsplit("/", 1)[-1]
        label = "Email copy" if link in emails else text or link["kind"]
        chips.append(f'<a class="chip{"" if link["ok"] else " broken"}" href="{escape(link["target"])}" '
                     f'title="{escape(link["target"])}">{escape(label)}</a>')
    home = '<span class="chip home">⌂ Home button</span>' if page["home"] else '<span class="chip nohome">No Home button</span>'
    out = {link["target"] for link in page["links"] if link["kind"] == "page"} - {page["path"], "index.html", MAP}
    problems = "".join(f"<li>{escape(p)}</li>" for p in page["problems"])
    return (f'<article class="node{" bad" if page["problems"] else ""}" id="{node_id(page["path"])}" tabindex="-1">'
            f'<a class="title" href="{escape(page["path"])}">{escape(page["title"])}</a>'
            f'<div class="path">{escape(page["path"])}</div>'
            f'<div class="chips">{home}{"".join(chips)}</div>'
            f'<div class="meta">Links to {len(out)} page(s) · {page["controls"]} button(s) checked</div>'
            + (f'<ul class="problems">{problems}</ul>' if problems else "") + "</article>")


def render(pages, unlinked):
    nodes = {rel: p for rel, p in pages.items() if not p["email"]}
    columns = {}
    for rel in sorted(nodes, key=lambda r: (r.count("/"), r != "index.html", r)):
        columns.setdefault(section(rel), []).append(rel)
    order = [s for s in SECTIONS if s in columns] + sorted(s for s in columns if s not in SECTIONS)
    edges = sorted({(node_id(rel), node_id(link["target"])) for rel, p in nodes.items() for link in p["links"]
                    if link["kind"] == "page" and link["ok"] and link["target"] in nodes and rel != MAP
                    and section(link["target"]) != section(rel) and section(link["target"]) != ""})
    cols = "".join(f'<section class="col"><h2 class="label">{escape(SECTIONS.get(s, s.title()))} '
                   f'<span class="count">{len(columns[s])}</span></h2>'
                   + "".join(node_html(pages[rel], pages) for rel in columns[s]) + "</section>" for s in order)
    links = [link for p in pages.values() for link in p["links"]]
    checked = [link for link in links if link["kind"] != "external"]
    broken = sum(not link["ok"] for link in checked)
    problems = sum(len(p["problems"]) for p in pages.values())
    controls = sum(p["controls"] for p in pages.values())
    homeless = [p["path"] for p in nodes.values() if not p["home"]]
    text = (f"All {len(checked)} links and {controls} buttons work, and every page has a Home button."
            if not problems else f"{problems} problem(s) found across {sum(bool(p['problems']) for p in pages.values())} page(s).")
    summary = facts([
        ("Pages", f"{len(nodes)} pages · {len(pages) - len(nodes)} email copies", ""),
        ("Links checked", f"{len(checked)} · {broken} broken", "bad" if broken else "good"),
        ("Buttons checked", f"{controls}", ""),
        ("Home button", f"{len(nodes) - len(homeless)} of {len(nodes)} pages", "bad" if homeless else "good"),
        ("Unlinked pages", f"{len(unlinked)}", "bad" if unlinked else ""),
    ])
    issues = "".join(f"<li><a href=\"{escape(p['path'])}\">{escape(p['path'])}</a>: {escape(x)}</li>"
                     for p in pages.values() for x in p["problems"])
    issues = f'<div class="banner"><strong>Problems:</strong><ul>{issues}</ul></div>' if issues else ""
    orphans = (f'<div class="banner"><strong>Not linked from anywhere:</strong> '
               + ", ".join(f'<a href="{escape(u)}">{escape(u)}</a>' for u in unlinked) + "</div>") if unlinked else ""
    rows = "".join(f'<tr><td class="l"><a href="{escape(p["path"])}">{escape(p["path"])}</a></td>'
                   f'<td class="l">{escape(link["text"] or "-")}</td><td class="l"><code>{escape(link["target"])}</code></td>'
                   f'<td class="l">{escape(link["kind"])}</td>'
                   f'<td class="status {"ok" if link["ok"] else "broken"}">{"OK" if link["ok"] else "Broken"}</td></tr>'
                   for p in pages.values() for link in p["links"])
    table = ('<div class="card"><table class="links"><thead><tr><th class="l">Page</th><th class="l">Link</th>'
             f'<th class="l">Goes to</th><th class="l">Kind</th><th class="status">Status</th></tr></thead><tbody>{rows}</tbody></table></div>')
    body = (f'<header><h1>Site map</h1><p>Every page of the report suite and how they connect · checked when built</p></header>'
            f'<p class="summary{" alert" if problems else ""}">{escape(text)}</p>{summary}{issues}{orphans}'
            f'<div class="legend"><span><span class="line"></span>link between sections</span>'
            f'<span>⌂ Home button: the page links back here</span><span>Chips: the files a page offers (green: the file exists)</span>'
            f'<span>Hover a card to light up its connections</span></div>'
            f'<div class="map" style="--cols:{len(order)}"><svg class="edges" aria-hidden="true"></svg>{cols}</div>'
            f'<script type="application/json" id="map-edges">{json.dumps(edges)}</script>'
            + accordion("Every link, checked", table, f"{len(links)} links on {len(pages)} pages")
            + MAP_JS)
    return PAGE.substitute(title="Site map", css=CSS + MAP_CSS, body=body, root="", current="map")


def build(root=ROOT):
    """Check the suite and write <root>/map.html; returns (path, pages, unlinked)."""
    root = Path(root).resolve()
    pages, unlinked = crawl(root)
    path = root / MAP
    unlinked = [u for u in unlinked if u != MAP]
    path.write_text(render(pages, unlinked), encoding="utf-8")
    pages[MAP] = check_page(path, root)  # the map's own links, now that it exists
    path.write_text(render(pages, unlinked), encoding="utf-8")  # again, with the map's own card
    pages[MAP] = check_page(path, root)
    return path, pages, unlinked


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT), help="the reports folder (with index.html)")
    args = ap.parse_args(argv)
    path, pages, unlinked = build(args.root)
    problems = [(p["path"], x) for p in pages.values() for x in p["problems"]]
    links = sum(len(p["links"]) for p in pages.values())
    print(f"wrote {path}: {len(pages)} pages, {links} links, {len(problems)} problem(s), {len(unlinked)} unlinked page(s)")
    for rel, problem in problems:
        print(f"  {rel}: {problem}")
    for rel in unlinked:
        print(f"  unlinked: {rel}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
