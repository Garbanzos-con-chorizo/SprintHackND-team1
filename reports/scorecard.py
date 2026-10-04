"""COO scorecard page (O2.1, O2.4): renders a KPI file from `python -m recon.kpi` (docs/contracts/kpi.md).

The page does no arithmetic and decides nothing about missing data: every number, status, note,
change and badge comes from the file. Five areas, three KPIs each, in the file's order; the two
top-10 rankings as tables. Simulated KPIs carry the file's `internal_data.label` as a quiet badge.
Prints on one landscape page (five area columns).

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

from reports.pulse import CSS, DATA_LABEL, DATA_NOTE, PAGE, money, stamp

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
  box-shadow:var(--shadow); }
.tile .name { font-size:14px; font-weight:700; color:var(--ink); line-height:1.3; }
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
.tile .change .prior { display:block; margin-top:2px; }
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
details.defs { margin-top:20px; font-size:14px; color:var(--muted); }
details.defs dt { margin-top:6px; }
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
  .tile .change .prior { display:inline; }
  .sim { display:inline-block; font-size:6pt; font-weight:400; padding:0 3px; margin:0 0 0 4px; vertical-align:middle; }
  table.rank th, table.rank td { font-size:6.5pt; padding:0 2px; line-height:1.25; }
  table.rank td:nth-child(2) { max-width:1.1in; overflow:hidden; text-overflow:ellipsis; }
  .gapnote { display:none; }
  table.rank .share { display:none; }
  details.defs, .nav { display:none; }
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
    partial = ' <span class="muted">(partial period)</span>' if d.get("reason") == "partial_period" else ""
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


def tile(k, prior_label, sim_label, pillars=None):
    badge = f'<span class="sim">{escape(sim_label)}</span>' if k["simulated"] else ""
    status = k["status"]
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
    pillar = (pillars or {}).get(k.get("pillar"))
    tag = f'<div class="pillar">{escape(pillar)}</div>' if pillar else ""
    return (f'<div class="tile {status}" title="{escape(k["definition"])}">{tag}'
            f'<div class="name">{escape(k["name"])}{badge}</div>{main}{change}{note}</div>')


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
        text += f"; marketplace data missing on {len(kf['coverage']['gaps'])} day(s)"
    return text + ".", not kf["coverage"]["complete"]


def render(kf, dest=DEST):
    period, prior = kf["period"], kf["prior_period"]
    sim_label = (kf.get("internal_data") or {}).get("label") or "Simulated internal data"
    pillars = {p["id"]: p["name"] for p in kf.get("pillars", [])}
    by_area = {a["id"]: [k for k in kf["kpis"] if k["area"] == a["id"]] for a in kf["areas"]}
    areas = "\n".join(
        f'<section class="area{" wide" if any(k["kind"] == "ranking" for k in by_area[a["id"]]) else ""}">'
        f'<h2>{escape(a["name"])}</h2>'
        + "".join(tile(k, prior["label"], sim_label, pillars) for k in by_area[a["id"]]) + "</section>"
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
    data = f"<strong>{DATA_LABEL}:</strong> {DATA_NOTE}."
    simnote = (f'<p class="simnote">{data} {simulated} of {len(kf["kpis"])} KPIs use {escape(sim_label.lower())} '
               f'(marked). {escape(kf["definitions"].get("simulated", ""))}</p>') if simulated else f'<p class="simnote">{data}</p>'
    internal = kf.get("internal_data")
    if not internal:
        simnote = f'<p class="simnote">{data} No internal data stored for this period: KPIs that need it show "No data".</p>'
    defs = "".join(f"<dt>{escape(k['name'])}</dt><dd>{escape(k['definition'])}</dd>" for k in kf["kpis"])
    top_defs = " ".join(escape(v) for v in kf["definitions"].values())
    files = "".join(f'<a href="{period["type"]}-{period["id"]}.{ext}">{label}</a>' for ext, label in
                    (("csv", "KPI table (CSV)"), ("pdf", "PDF"), ("json", "KPI file")) if (dest / f"{period['type']}-{period['id']}.{ext}").exists())
    downloads = f'<p class="links">Download: {files}</p>' if files else ""
    body = (f'<header><h1>COO scorecard: {escape(period["label"])}</h1>'
            f'<p>Goodwill Michiana e-commerce · {escape(period["start"])} to {escape(period["through"])} · '
            f'compared with {escape(prior["label"])} · generated {escape(stamp(kf["generated_at"]))}</p></header>'
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>{coverage}{simnote}'
            f'<div class="areas">\n{areas}\n</div>'
            f'<section class="foot"><p>{top_defs}</p></section>'
            f'<details class="defs"><summary>KPI definitions</summary><dl>{defs}</dl></details>'
            f'{downloads}<p class="nav"><a href="index.html">All scorecards</a> · <a href="../index.html">Reports</a></p>')
    return PAGE.substitute(title=f"COO scorecard {period['id']}", css=CSS + SCORECARD_CSS, body=body)


def _period_label(page):
    """The period's name from the KPI file kept next to the page ("September 2026"); the file name if it is gone."""
    try:
        return json.loads(page.with_suffix(".json").read_text(encoding="utf-8"))["period"]["label"]
    except (OSError, ValueError, KeyError):
        return page.stem


def render_index(dest):
    pages = sorted((f for f in dest.glob("*.html") if re.fullmatch(r"(day|week|month)-[\dW-]+", f.stem)),
                   key=lambda f: f.stem, reverse=True)
    groups = ""
    for kind, title in (("month", "Months"), ("week", "Weeks"), ("day", "Days")):
        items = "\n".join(f'  <li><a href="{f.name}">{escape(_period_label(f))}</a></li>'
                          for f in pages if f.stem.startswith(kind + "-"))
        if items:
            groups += f'<h2 class="sec">{title}</h2>\n<ul class="days">\n{items}\n</ul>\n'
    body = (f'<header><h1>COO scorecards</h1><p>Goodwill Michiana e-commerce · {len(pages)} page(s)</p></header>'
            f'{groups or "<ul class=\"days\"><li>None yet</li></ul>"}<p class="nav"><a href="../index.html">Reports</a></p>')
    return PAGE.substitute(title="COO scorecards", css=CSS + SCORECARD_CSS, body=body)


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
