"""COO scorecard page (O2.1, O2.4): renders a KPI file from `python -m recon.kpi` (docs/contracts/kpi.md).

The page does no arithmetic and decides nothing about missing data: every number, status, note,
change and badge comes from the file. Five areas, three KPIs each, in the file's order; the two
top-10 rankings as tables. Simulated KPIs carry the file's `internal_data.label` as a quiet badge.
A pie shows the period's revenue by marketplace (the file's `inputs.by_marketplace` of KPI 1). What the
figures mean sits in a "Notes and Definitions" dropdown at the bottom. Prints on one landscape page
(five area columns; the pie and the notes are screen only). The list page (index.html) also carries the
KPI trend: each area's KPIs over the scorecards on file, by day, week or month.

    python -m reports.scorecard --kpi-file out/kpi/month-2026-09.json   # -> reports/scorecard/month-2026-09.html
    python -m reports.scorecard --period month                          # out/kpi/latest-month.json
"""
import argparse
import json
import re
import shutil
from datetime import date
from html import escape
from pathlib import Path

from reports import charts, library
from reports.pulse import CSS, DATA_LABEL, DATA_NOTE, PAGE, ast, money, notes, stamp
from reports.schema import LABELS

ROOT = Path(__file__).resolve().parent.parent
KPI_DIR = ROOT / "out" / "kpi"
DEST = ROOT / "reports" / "scorecard"

SCORECARD_CSS = """
:root { --page:1320px; }
.coverage { margin:12px 0 0; }
.areas { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; margin:16px 0 0; }
/* The area that holds the two top-10 tables gets two columns, so the tables fit without scrolling. */
@media (min-width:900px) { .area.wide { grid-column:span 2; } }
.area h2 { font-size:14px; color:var(--primary); text-transform:uppercase; letter-spacing:.05em; margin:0 0 6px;
  border-bottom:2px solid var(--primary); padding-bottom:4px; }
.tile { border:1px solid var(--line); border-radius:var(--radius); padding:10px 12px; margin:0 0 8px; background:var(--card);
  box-shadow:var(--shadow); position:relative; }
.tile .name { font-size:14px; font-weight:700; color:var(--ink); line-height:1.3; padding-right:22px; }
/* The (i) button and its pop-out. On screen the prior value and the note live there; print shows them in the tile. */
.info { position:absolute; top:8px; right:8px; width:20px; height:20px; padding:0; border-radius:50%;
  border:1px solid var(--primary); background:var(--card); color:var(--primary); cursor:pointer;
  font:italic 700 13px/18px Georgia,"Times New Roman",serif; }
.info::before { content:""; position:absolute; inset:-8px; }
.info:hover, .info:focus-visible { background:var(--primary); color:#fff; }
.about { width:300px; max-width:calc(100vw - 32px); padding:12px 14px; border:1px solid var(--line); border-radius:var(--radius);
  background:var(--card); color:var(--ink); font-size:14px; line-height:1.45; box-shadow:0 8px 28px rgba(35,31,32,.22); }
.about-name { font-weight:700; margin-bottom:4px; }
.about p { margin:6px 0 0; }
@supports (top:anchor(bottom)) {
  .about { position:absolute; inset:auto; margin:6px 0 0; top:anchor(bottom); left:anchor(left);
    position-try-fallbacks:flip-inline, flip-block, flip-block flip-inline; }
}
.tile .change .prior, .tile .note, .tile.partial .change .pp { display:none; }
.flag { font-size:12px; font-weight:700; color:var(--down); margin-top:3px; }
.tile .value { font-size:24px; font-weight:700; font-variant-numeric:tabular-nums; margin:2px 0; line-height:1.25; }
.tile .value .per { font-size:13px; font-weight:400; color:var(--muted); white-space:nowrap; }
.tile .pillar { font-size:11px; font-weight:700; color:var(--primary); text-transform:uppercase; letter-spacing:.05em; }
.parts { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin:4px 0; }
.part { border:1px solid var(--line); border-radius:var(--radius); padding:4px 6px; }
.part .pname { font-size:12px; color:var(--muted); }
.part .pval { font-size:18px; font-weight:700; font-variant-numeric:tabular-nums; }
.part .pval.none { font-size:13px; color:var(--muted); font-weight:600; }
.part .pof { font-size:12px; color:var(--muted); }
.links a + a { margin-left:10px; }
.tile .value.none { font-size:15px; color:var(--muted); font-weight:600; }
.tile .change { font-size:13px; margin:2px 0; }
.tile .chg:not(.up):not(.down) { border-color:var(--line); }
.tile .note { font-size:13px; color:var(--muted); margin:4px 0 0; }
.tile.partial { border-left:4px solid var(--down); }
.tile.no_data { background:var(--nodata); }
.tile .meta { font-size:12px; color:var(--muted); margin-top:4px; }
/* The simulated badge: its own line under the KPI name, in the same dashed ink as the page's note. */
.sim { display:block; width:fit-content; font-size:11px; font-weight:600; color:var(--ink); border:1px dashed var(--ink);
  border-radius:var(--radius); padding:0 6px; margin:3px 0 2px; letter-spacing:.02em; }
table.rank { min-width:0; width:100%; margin-top:4px; }
table.rank th, table.rank td { padding:3px 4px; font-size:13px; }
table.rank th:nth-child(2), table.rank td:nth-child(2) { text-align:left; }
details.notes dt { margin-top:6px; }
/* The pie: the period's revenue by marketplace. */
.mix { max-width:620px; padding:12px 16px; margin:16px 0 0; overflow:visible; }
.mix h2.sec { margin:0 0 6px; }
/* The KPI trend on the list page: an area and a period type to choose, one small line per KPI. */
.explorer { padding:14px 16px; margin:4px 0 0; overflow:visible; }
.ex-head { display:flex; flex-wrap:wrap; align-items:center; gap:8px 18px; }
.ex-head h2.sec { margin:0 auto 0 0; }
.ex-pick { display:flex; flex-wrap:wrap; gap:6px; }
.pick { font:inherit; font-size:14px; padding:5px 12px; border:1px solid var(--line); border-radius:999px;
  background:var(--card); color:var(--ink); cursor:pointer; }
.pick[aria-pressed="true"] { background:var(--primary); border-color:var(--primary); color:#fff; font-weight:600; }
.pick:disabled { opacity:.45; cursor:default; }
.pick:focus-visible { outline:2px solid var(--primary); outline-offset:1px; }
.ex-set { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin-top:14px; }
@media (max-width:800px) { .ex-set { grid-template-columns:1fr; } }
.ex-kpi { border:1px solid var(--line); border-radius:var(--radius); padding:10px 12px; }
.ex-kpi .name { font-size:14px; font-weight:700; }
.ex-kpi .value { font-size:22px; font-weight:700; font-variant-numeric:tabular-nums; line-height:1.3; }
.ex-kpi .value .per { font-size:13px; font-weight:400; color:var(--muted); }
.ex-kpi .value.none { font-size:15px; color:var(--muted); font-weight:600; }
.ex-kpi .change { font-size:13px; min-height:1.6em; }
.ex-kpi .chg:not(.up):not(.down) { border-color:var(--line); }
.ex-none { margin:14px 0 0; color:var(--muted); }
@media print {
  @page { size:letter landscape; margin:0.35in; }
  body { font-size:8pt; }
  header h1 { font-size:13pt; }
  header p { font-size:7.5pt; }
  .area.wide { grid-column:auto; }
  .summary { font-size:9pt; padding:4px 8px; margin-top:6px; }
  .coverage, .simnote { font-size:7.5pt; margin-top:4px; padding:3px 6px; }
  .areas { grid-template-columns:repeat(5,1fr); gap:6px; margin-top:6px; }
  .area h2 { font-size:8pt; margin-bottom:3px; padding-bottom:2px; }
  .tile { padding:4px 6px; margin-bottom:4px; break-inside:avoid; }
  .tile .name { font-size:7.5pt; }
  .tile .value { font-size:12pt; }
  .tile .value.none { font-size:9pt; }
  .tile .pillar { font-size:6pt; }
  .parts { gap:3px; margin:2px 0; }
  .part { padding:1px 3px; }
  .part .pname, .part .pof { font-size:6pt; }
  .part .pval { font-size:10pt; }
  .part .pval.none { font-size:8pt; }
  .links { display:none; }
  .tile .change, .tile .note, .tile .meta { font-size:6.5pt; margin-top:1px; }
  .tile .change .prior, .tile.partial .change .pp { display:inline; }
  .tile .note { display:block; }
  .info, .about, .flag { display:none !important; }
  .tile .name { padding-right:0; }
  .sim { display:inline-block; font-size:6pt; font-weight:400; padding:0 3px; margin:0 0 0 4px; vertical-align:middle; }
  table.rank th, table.rank td { font-size:6.5pt; padding:0 2px; line-height:1.25; }
  table.rank td:nth-child(2) { max-width:1.1in; overflow:hidden; text-overflow:ellipsis; }
  .gapnote { display:none; }
  table.rank .share { display:none; }
  details.notes, .nav, .mix, .explorer, .actions { display:none; }
  .tile, .sim, .chg { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
}
"""

DELTA_REASON = {"no_prior_period": "no prior period", "current_no_data": "", "not_applicable": ""}


def fmt(value, unit, per=None):
    """A KPI value in its unit; `per` is appended outside (see value_html)."""
    if value is None:
        return None
    if unit == "cents":
        return money(round(value))
    if unit == "ratio":
        return f"{value * 100:.1f}%"
    if unit == "count":
        return f"{round(value):,}"
    if unit == "days":
        return f"{value:,.1f} days"
    return f"{value:,.1f}"


def delta_text(k):
    d = k["delta"] or {}
    if d.get("value") is None:
        why = DELTA_REASON.get(d.get("reason"), "")
        return f'<span class="muted">{why}</span>' if why else ""
    v, unit = d["value"], k["unit"]
    if unit == "ratio":
        shown = f"{v * 100:+.1f} pts"
    elif unit == "cents":
        shown = ("+" if v > 0 else "") + money(round(v))
    elif unit == "count":
        shown = f"{round(v):+,}"
    else:
        shown = f"{v:+,.1f}"
    if d.get("pct") is not None and unit != "ratio":
        shown += f" ({d['pct']:+.1f}%)"
    better = (v > 0) == (k["good_direction"] == "up")
    cls = "" if v == 0 else (" up" if better else " down")
    partial = ' <span class="muted pp">(partial period)</span>' if d.get("reason") == "partial_period" else ""
    return f'<span class="chg{cls}">{escape(shown)}</span>{partial}'


def note_html(note):
    """The note, with the missing-day sentence the coverage banner already states marked so print can drop it."""
    parts = re.split(r"(?<=\.) ", note)
    return " ".join(f'<span class="gapnote">{escape(p)}</span>' if " has no data on " in p else escape(p) for p in parts)


def parts_html(parts, unit):
    """Sell-through's two boxes (kpi.md, "Sell-through in two boxes"); a null value shows "No data"."""
    boxes = []
    for p in parts:
        shown = fmt(p["value"], unit)
        val = f'<div class="pval">{escape(shown)}</div>' if shown is not None else '<div class="pval none">No data</div>'
        of = (f'<div class="pof">{p["sold"]:,} of {p["available"]:,}</div>'
              if p.get("sold") is not None and p.get("available") is not None else "")
        boxes.append(f'<div class="part"><div class="pname">{escape(p["name"])}</div>{val}{of}</div>')
    return f'<div class="parts">{"".join(boxes)}</div>'


def about_html(k, prior_label, prior, sim_label, sim_def):
    """The (i) button of a tile and what it opens: the definition, the prior period's value, the note and what
    "simulated" means. It needs no script: the browser opens and closes a `popover`."""
    ref = "about-" + re.sub(r"[^a-z0-9]+", "-", k["id"].lower())
    lines = [f'<p>{escape(k["definition"])}</p>']
    if prior is not None:
        lines.append(f'<p><b>{escape(prior_label)}:</b> {escape(prior)}</p>')
    if (k.get("delta") or {}).get("reason") == "partial_period":
        lines.append("<p><b>Change:</b> compared over a partial period.</p>")
    if k.get("note"):
        lines.append(f'<p><b>Note:</b> {escape(k["note"])}</p>')
    if k["simulated"]:
        lines.append(f'<p><b>{escape(sim_label)}.</b> {escape(sim_def)}</p>')
    # The anchor name ties the pop-out to its own button, so it opens beside the tile and not in a page corner.
    return (f'<button class="info" type="button" popovertarget="{ref}" style="anchor-name:--{ref}" '
            f'aria-label="About {escape(k["name"])}">i</button>'
            f'<div class="about" id="{ref}" popover style="position-anchor:--{ref}">'
            f'<div class="about-name">{escape(k["name"])}</div>{"".join(lines)}</div>')


def tile(k, prior_label, sim_label, pillars=None, sim_def=""):
    """One KPI. On screen the tile shows the value and its change; the prior value and the note are behind the
    (i) button. In print (the PDF) there is no button, so both are printed in the tile."""
    badge = f'<span class="sim">{escape(sim_label)}</span>' if k["simulated"] else ""
    status = k["status"]
    prior = None
    if k["kind"] == "ranking":
        rows = k["rows"] or []
        if rows:
            has_ratio = any(r.get("ratio") is not None for r in rows)
            body = "".join(
                f'<tr><td>{r["rank"]}</td><td>{escape(r["label"])}</td><td>{fmt(r["value"], k["unit"])}</td>'
                f'<td class="share">{r["share"] * 100:.1f}%</td>'
                + (f'<td>{r["ratio"] * 100:.0f}%</td>' if has_ratio else "") + "</tr>" for r in rows)
            head = ('<tr><th>#</th><th>Category</th><th>Amount</th><th class="share">Share</th>'
                    + ("<th>Margin</th>" if has_ratio else "") + "</tr>")
            main = f'<table class="rank"><thead>{head}</thead><tbody>{body}</tbody></table>'
        else:
            main = '<div class="value none">No data</div>'
        change = ""
    else:
        shown = fmt(k["value"], k["unit"])
        if k.get("parts"):
            main = parts_html(k["parts"], k["unit"])
        elif shown is None:
            main = '<div class="value none">No data</div>'
        else:
            per = f' <span class="per">per {escape(k["per"])}</span>' if k.get("per") else ""
            main = f'<div class="value">{escape(shown)}{per}</div>'
        prior = fmt(k["prior_value"], k["unit"])
        delta = delta_text(k)
        change = (f'<div class="change">{delta}' + (f' <span class="muted prior">vs {escape(prior_label)}: {escape(prior)}</span>'
                                                     if prior is not None else "") + "</div>") if (delta or prior) else ""
    note = f'<div class="note">{note_html(k["note"])}</div>' if k.get("note") else ""
    flag = '<div class="flag">Partial data</div>' if status == "partial" else ""
    pillar = (pillars or {}).get(k.get("pillar"))
    tag = f'<div class="pillar">{escape(pillar)}</div>' if pillar else ""
    return (f'<div class="tile {status}">{about_html(k, prior_label, prior, sim_label, sim_def)}{tag}'
            f'<div class="name">{escape(k["name"])}{badge}</div>{main}{change}{flag}{note}</div>')


def headline(kf):
    """One sentence for the portal: revenue, its change, and what is missing."""
    by_id = {k["id"]: k for k in kf["kpis"]}
    rev, growth = by_id.get("fin.revenue"), by_id.get("fin.revenue_growth")
    text = "Total e-commerce revenue " + (money(rev["value"]) if rev and rev["value"] is not None else "no data")
    if growth and growth["value"] is not None:
        text += f", {'up' if growth['value'] >= 0 else 'down'} {abs(growth['value']) * 100:.1f}% vs {kf['prior_period']['label']}"
    no_data = sum(k["status"] == "no_data" for k in kf["kpis"])
    partial = sum(k["status"] == "partial" for k in kf["kpis"])
    if no_data:
        text += f"; {no_data} of {len(kf['kpis'])} KPIs have no data"
    if partial:
        text += f"; {partial} partial"
    if not kf["coverage"]["complete"]:
        text += f"; marketplace data missing on {len({g['date'] for g in kf['coverage']['gaps']})} day(s)"
    return text + ".", not kf["coverage"]["complete"]


def render(kf, dest=DEST):
    period, prior = kf["period"], kf["prior_period"]
    sim_label = (kf.get("internal_data") or {}).get("label") or "Simulated internal data"
    pillars = {p["id"]: p["name"] for p in kf.get("pillars", [])}
    by_area = {a["id"]: [k for k in kf["kpis"] if k["area"] == a["id"]] for a in kf["areas"]}
    areas = "\n".join(
        f'<section class="area{" wide" if any(k["kind"] == "ranking" for k in by_area[a["id"]]) else ""}">'
        f'<h2>{escape(a["name"])}</h2>'
        + "".join(tile(k, prior["label"], sim_label, pillars, kf["definitions"].get("simulated", ""))
                  for k in by_area[a["id"]]) + "</section>"
        for a in kf["areas"])
    text, alert = headline(kf)
    cov = kf["coverage"]
    coverage = ""
    if cov["gaps"]:
        gaps = ", ".join(f'{g["marketplace"]} {g["date"]} ({g["status"]})' for g in cov["gaps"][:12])
        more = f" and {len(cov['gaps']) - 12} more" if len(cov["gaps"]) > 12 else ""
        coverage = (f'<div class="banner coverage"><strong>Data missing:</strong> {escape(gaps)}{more}. '
                    f'KPIs that use these days are marked partial.</div>')
    simulated = sum(k["simulated"] for k in kf["kpis"])
    sim_def = kf["definitions"].get("simulated", "")
    data = f"<strong>{DATA_LABEL}.</strong>"
    simnote = (f'<p class="simnote">{data} {simulated} of {len(kf["kpis"])} KPIs use {escape(sim_label.lower())} '
               f'(marked){ast(sim_def)}</p>') if simulated else f'<p class="simnote">{data}</p>'
    internal = kf.get("internal_data")
    if not internal:
        simnote = f'<p class="simnote">{data} No internal data stored for this period: KPIs that need it show "No data".</p>'
    defs = "".join(f"<dt>{escape(k['name'])}</dt><dd>{escape(k['definition'])}</dd>" for k in kf["kpis"])
    top_defs = " ".join(escape(v) for v in kf["definitions"].values())
    name = f'{period["type"]}-{period["id"]}'
    files = "".join(f'<a class="btn{cls} dl" href="{name}.{ext}">{label}</a>' for ext, label, cls in
                    (("pdf", "PDF", ""), ("csv", "KPI Table (CSV)", " quiet"), ("json", "KPI File", " quiet"))
                    if (dest / f"{name}.{ext}").exists())
    about = notes([
        ("", f'<p><strong>{DATA_LABEL}:</strong> {DATA_NOTE}. Generated {escape(stamp(kf["generated_at"]))}.</p><p>{top_defs}</p>'
             '<p>The (i) on a KPI opens its definition, the prior period\'s value and any note.</p>'),
        ("KPI Definitions", f"<dl>{defs}</dl>")])
    body = (f'<header><h1>COO Scorecard: {escape(period["label"])}</h1>'
            f'<p>{escape(period["start"])} to {escape(period["through"])} · compared with {escape(prior["label"])}</p></header>'
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>{coverage}{simnote}'
            f'{marketplace_pie(kf)}'
            f'<div class="areas">\n{areas}\n</div>'
            f'<div class="actions">{files}<a class="btn quiet" href="index.html">All Scorecards</a></div>{about}')
    return PAGE.substitute(title=f"COO Scorecard {period['id']}", css=CSS + charts.CHART_CSS + SCORECARD_CSS, body=body)


def marketplace_pie(kf):
    """The period's revenue by marketplace as a pie, from KPI 1's `inputs.by_marketplace` (kpi.md v0.7); "" for a
    file without it or without revenue. Marketplace revenue comes from the files, so it carries no simulated badge."""
    revenue = next((k for k in kf["kpis"] if k["id"] == "fin.revenue"), None)
    by = ((revenue or {}).get("inputs") or {}).get("by_marketplace")
    if not by or revenue["value"] is None:
        return ""
    slices = [(LABELS.get(m, m.title()), charts.COLORS.get(LABELS.get(m, ""), charts.COLORS["Other"]), cents / 100)
              for m, cents in by.items()]
    drawn = charts.pie(slices, f"${revenue['value'] / 100:,.0f}", "revenue")
    tip = "Sales minus refunds, before marketplace fees, on the days each marketplace has data"
    return f'<div class="card mix"><h2 class="sec">Revenue by Marketplace{ast(tip)}</h2>{drawn}</div>' if drawn else ""


def _index_row(page):
    """One scorecard for the list page, from the KPI file kept next to it; just its name and link if that is gone."""
    try:
        kf = json.loads(page.with_suffix(".json").read_text(encoding="utf-8"))
        period, by_id = kf["period"], {k["id"]: k for k in kf["kpis"]}
    except (OSError, ValueError, KeyError):
        return {"cells": [f'<a href="{page.name}">{escape(page.stem)}</a>', "", "-", "", "", ""], "find": page.stem,
                "tags": page.stem.split("-")[0], "label": page.stem, "revenue": "-"}
    rev, growth = by_id.get("fin.revenue"), by_id.get("fin.revenue_growth")
    revenue = money(round(rev["value"])) if rev and rev["value"] is not None else "-"
    if growth and growth["value"] is not None:
        g = growth["value"] * 100
        change = (f'<span class="chg {"up" if g > 0 else "down" if g < 0 else ""}">{g:+.1f}%</span>'
                  f'<small>vs {escape(kf["prior_period"]["label"])}</small>')
    else:
        change = '<span class="muted">n/a</span>'
    gaps = kf["coverage"]["gaps"]
    partial = sum(k["status"] in ("partial", "no_data") for k in kf["kpis"])
    data = (f'<span class="pill missing">Data missing on {len({g["date"] for g in gaps})} day(s)</span>' if gaps
            else '<span class="pill ok">Complete</span>')
    data += f"<small>{partial} of {len(kf['kpis'])} KPIs partial or without data</small>" if partial else ""
    files = "".join(f'<a href="{page.stem}.{ext}">{name}</a>' for ext, name in (("csv", "CSV"), ("pdf", "PDF"), ("json", "KPI file"))
                    if page.with_suffix(f".{ext}").exists())
    return {"cells": [f'<a href="{page.name}">{escape(period["label"])}</a>',
                      f'{escape(period["start"])} to {escape(period["through"])}', revenue, change, data, files],
            "find": f'{period["label"]} {period["type"]} {period["id"]} {period["start"]} {period["through"]} '
                    f'{"missing partial" if gaps else "complete"}',
            "tags": period["type"], "label": period["label"], "revenue": revenue}


KINDS = (("day", "Days"), ("week", "Weeks"), ("month", "Months"))
SHOWN = {"day": 31, "week": 12, "month": 12}  # how many periods a trend line holds at most, newest last

# The explorer's script only shows the chosen set and marks the chosen buttons: every line is already in the page.
EXPLORER_SCRIPT = """<script>
(function () {
  var box = document.getElementById("trend");
  if (!box) return;
  var picks = [].slice.call(box.querySelectorAll(".pick")), sets = [].slice.call(box.querySelectorAll(".ex-set"));
  var chosen = { area: box.dataset.area, kind: box.dataset.kind };
  function show() {
    sets.forEach(function (s) { s.hidden = s.dataset.area !== chosen.area || s.dataset.kind !== chosen.kind; });
    picks.forEach(function (b) { b.setAttribute("aria-pressed", chosen[b.dataset.pick] === b.dataset.value ? "true" : "false"); });
  }
  picks.forEach(function (b) {
    b.addEventListener("click", function () { chosen[b.dataset.pick] = b.dataset.value; show(); });
  });
  show();
})();
</script>"""


def _short(period):
    """A period as it fits under a small chart: "Oct 3", "W40", "Sep 2026"."""
    start = date.fromisoformat(period["start"])
    if period["type"] == "day":
        return f"{start:%b} {start.day}"
    return period["id"].split("-")[-1] if period["type"] == "week" else f"{start:%b %Y}"


def _trend_card(k, found):
    """One KPI over the scorecards on file: its latest value and change (the newest file's own), and the line."""
    points, latest = [], None
    for stem, kf in found:
        cur = next((x for x in kf["kpis"] if x["id"] == k["id"]), None)
        value = cur["value"] if cur else None
        shown = fmt(value, k["unit"]) or "No data"
        partial = bool(cur) and cur["status"] == "partial"
        points.append((_short(kf["period"]), value, f'{kf["period"]["label"]}: {shown}{" (partial data)" if partial else ""}',
                       f"{stem}.html", partial))
        latest = (cur, kf)
    cur, kf = latest
    shown = fmt(cur["value"], k["unit"]) if cur else None
    per = f' <span class="per">per {escape(k["per"])}</span>' if k.get("per") else ""
    value = f'<div class="value">{escape(shown)}{per}</div>' if shown is not None else '<div class="value none">No data</div>'
    delta = delta_text(cur) if cur else ""
    change = f'{delta} <span class="muted">vs {escape(kf["prior_period"]["label"])}</span>' if delta and "chg" in delta else delta
    badge = f'<span class="sim">{escape((kf.get("internal_data") or {}).get("label") or "Simulated internal data")}</span>' if k["simulated"] else ""
    return (f'<div class="ex-kpi"><div class="name">{escape(k["name"])}{badge}</div>{value}<div class="change">{change}</div>'
            f'{charts.line(points, lambda v: fmt(v, k["unit"]))}</div>')


def explorer(dest):
    """The KPI trend of the list page: choose an area (Financial, Productivity, Inventory, Sales, ...) and days,
    weeks or months, and see each of the area's KPIs over the scorecards on file. Every value is a KPI file's own:
    nothing is computed here. A partial period is a hollow dot; a period with no data breaks the line."""
    on_file = {kind: [] for kind, _ in KINDS}
    for f in sorted(dest.glob("*.json")):
        m = re.fullmatch(r"(day|week|month)-[\dW-]+", f.stem)
        if not m or not f.with_suffix(".html").exists():
            continue
        try:
            kf = json.loads(f.read_text(encoding="utf-8"))
            kf["period"]["start"], kf["kpis"], kf["areas"]
        except (OSError, ValueError, KeyError):
            continue
        on_file[m[1]].append((f.stem, kf))
    newest = next((found[-1][1] for found in (on_file["month"], on_file["week"], on_file["day"]) if found), None)
    if newest is None:
        return ""
    areas = [a for a in newest["areas"] if any(k["area"] == a["id"] and k["kind"] == "scalar" for k in newest["kpis"])]
    first_kind = max(KINDS, key=lambda kn: len(on_file[kn[0]]))[0]
    sets = []
    for kind, _ in KINDS:
        found = on_file[kind][-SHOWN[kind]:]
        for a in areas:
            cards = "".join(_trend_card(k, found) for k in newest["kpis"] if k["area"] == a["id"] and k["kind"] == "scalar") if found else ""
            hidden = "" if (kind == first_kind and a is areas[0]) else " hidden"
            sets.append(f'<div class="ex-set" data-kind="{kind}" data-area="{escape(a["id"])}"{hidden}>'
                        + (cards or '<p class="ex-none">No scorecard of this kind on file yet.</p>') + "</div>")

    def picks(what, options, chosen):
        return "".join(f'<button class="pick" type="button" data-pick="{what}" data-value="{escape(value)}" '
                       f'aria-pressed="{"true" if value == chosen else "false"}">{escape(name)}</button>'
                       for value, name in options)

    tip = "Each KPI as its scorecards state it; a hollow dot is partial data, a gap is no data. Select a dot to open that scorecard"
    return (f'<section class="card explorer" id="trend" data-kind="{first_kind}" data-area="{escape(areas[0]["id"])}">'
            f'<div class="ex-head"><h2 class="sec">KPI Trend{ast(tip)}</h2>'
            f'<div class="ex-pick" role="group" aria-label="KPI area">{picks("area", [(a["id"], a["name"]) for a in areas], areas[0]["id"])}</div>'
            f'<div class="ex-pick" role="group" aria-label="Period">{picks("kind", KINDS, first_kind)}</div></div>'
            f'{"".join(sets)}</section>{EXPLORER_SCRIPT}')


def render_index(dest):
    """The COO Scorecards page: the KPI trend, and every scorecard on file with its revenue, growth and data state,
    newest first."""
    pages = sorted((f for f in dest.glob("*.html") if re.fullmatch(r"(day|week|month)-[\dW-]+", f.stem)),
                   key=lambda f: f.stem, reverse=True)
    kinds = (("month", "Months", "Latest Month"), ("week", "Weeks", "Latest Week"), ("day", "Days", "Latest Day"))
    groups, top = [], []
    for kind, title, latest in kinds:
        found = [(f, _index_row(f)) for f in pages if f.stem.startswith(kind + "-")]
        groups.append((title, [row for _, row in found]))
        if found:
            page, row = found[0]
            top.append((latest, row["revenue"], f'{row["label"]} · revenue', page.name))
    table = library.finder_table(
        [("Period", "l"), ("Dates", "l"), ("Revenue", "num"), ("Growth", "num"), ("Data", "l"), ("Files", "files")],
        groups, [(kind, title) for kind, title, _ in kinds],
        'Find: "September", "week 40", "Oct 3"', noun="scorecard")
    about = notes([
        ("", f'<p><strong>{DATA_LABEL}:</strong> {DATA_NOTE}. KPIs marked "Simulated internal data" use a mock of '
             f'Goodwill\'s internal systems.</p>'),
        ("KPI Trend", '<p>Each line shows one KPI as the scorecards on file state it, by day, week or month; nothing is '
                      'recomputed here. A hollow dot is a period with partial data and a gap is a period with no data. '
                      'The change beside the latest value is the newest scorecard\'s own, against its prior period. '
                      'The latest week and month are to date until they end.</p>')])
    body = (f'<header><h1>COO Scorecards</h1><p>The 15 KPIs by day, week and month · {len(pages)} scorecard(s)</p></header>'
            f'{library.tiles(top) if top else ""}{explorer(dest)}{table}{about}')
    return PAGE.substitute(title="COO Scorecards", css=CSS + charts.CHART_CSS + SCORECARD_CSS + library.LIBRARY_CSS, body=body)


def build(kpi_file, dest=DEST):
    """Render one KPI file; keep a copy of the JSON next to the page. Returns the page path."""
    kf = json.loads(Path(kpi_file).read_text(encoding="utf-8"))
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    name = f"{kf['period']['type']}-{kf['period']['id']}"
    page = dest / f"{name}.html"
    page.write_text(render(kf, dest), encoding="utf-8")
    shutil.copyfile(kpi_file, dest / f"{name}.json")
    (dest / "index.html").write_text(render_index(dest), encoding="utf-8")
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--kpi-file", help="a KPI file (docs/contracts/kpi.md)")
    g.add_argument("--period", choices=["day", "week", "month"], help="render out/kpi/latest-<period>.json")
    ap.add_argument("--dest", default=str(DEST))
    args = ap.parse_args(argv)
    src = Path(args.kpi_file) if args.kpi_file else KPI_DIR / f"latest-{args.period}.json"
    if not src.exists():
        raise SystemExit(f"no KPI file at {src}; run python -m recon.kpi first")
    page = build(src, args.dest)
    from reports import hub
    hub.build()
    print(f"wrote {page}")


if __name__ == "__main__":
    main()
