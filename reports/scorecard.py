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

from reports.pulse import money
from reports.theme import CSS, PAGE, facts, span, stamp

ROOT = Path(__file__).resolve().parent.parent
KPI_DIR = ROOT / "out" / "kpi"
DEST = ROOT / "reports" / "scorecard"

SCORECARD_CSS = """
:root { --page:1520px; }
.simnote { margin:var(--sp-3) 0 0; font-size:var(--fs-small); color:var(--muted); }

/* Five areas. Wide screens and print: one aligned grid, a column per area (Category + Customer
   takes two so its rankings sit side by side), tile rows lined up across areas via subgrid. */
.areas { display:grid; grid-template-columns:minmax(0,1fr); gap:var(--sp-5); margin:var(--sp-5) 0 0; }
.area { display:grid; gap:1px; min-width:0; background:var(--rule); border:var(--bd); }
.area > h2 { padding:var(--sp-3) var(--sp-5); background:var(--blue); color:#fff; font-size:var(--fs-label);
  font-weight:var(--fw-bold); letter-spacing:.08em; text-transform:uppercase; line-height:1.3; }
.area.wide > h2, .area.wide > .tile:not(.ranking) { grid-column:1 / -1; }
@media (min-width:720px) {
  .areas { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .area.wide { grid-column:1 / -1; grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (min-width:1180px), print {
  .areas { grid-template-columns:var(--tracks); grid-template-rows:auto repeat(var(--rows),auto);
    gap:1px; background:var(--rule); border:var(--bd); }
  .area { grid-row:1 / -1; grid-template-rows:subgrid; background:transparent; border:0; }
  .area.wide { grid-column:span 2; grid-template-columns:subgrid; }
  .area.wide > .tile.ranking { grid-row:span var(--span); }
}

/* KPI tile: name and pillar, the value, change vs the prior period, badges, note */
.tile { min-width:0; padding:var(--sp-4) var(--sp-5) var(--sp-5); background:var(--bg); }
.tile.no_data { background:var(--bg-1); }
.tile.partial { border-left:3px solid var(--red); padding-left:calc(var(--sp-5) - 3px); }
.tile .name { font-size:var(--fs-small); font-weight:var(--fw-bold); line-height:1.3; }
.tile .pillar { color:var(--muted); padding-right:var(--sp-1); }
.tile .value { margin-top:var(--sp-2); font-size:var(--fs-metric); font-weight:var(--fw-bold); line-height:1.1; letter-spacing:-0.02em; }
.tile .value .per { font-size:var(--fs-small); font-weight:var(--fw-regular); letter-spacing:-0.01em; color:var(--muted); }
.tile .value.none { font-size:var(--fs-lead); font-weight:var(--fw-semi); letter-spacing:-0.01em; color:var(--muted); }
.tile .change { margin-top:var(--sp-1); font-size:var(--fs-small); color:var(--muted); }
.tile .tags { display:flex; flex-wrap:wrap; align-items:center; gap:var(--sp-2) var(--sp-3); margin-top:var(--sp-3); }
.tile .note { margin-top:var(--sp-3); font-size:var(--fs-small); color:var(--muted); line-height:1.35; }
.tile .pillar, .sim, .flag { font-size:9.5px; font-weight:var(--fw-semi); letter-spacing:.06em; text-transform:uppercase; line-height:15px; }
.sim, .flag { display:inline-block; padding:0 var(--sp-2); white-space:nowrap; border:1px solid; }
.sim { color:var(--ink-2); background:var(--bg-2); border-color:var(--rule); }
.flag { color:var(--red); background:var(--bg); border-color:currentColor; }

/* Top-10 rankings: compact ledger, the amount cell carries a bar scaled to the leader */
table.rank { min-width:0; margin-top:var(--sp-3); }
table.rank th, table.rank td { padding:3px var(--sp-3); font-size:var(--fs-small); border-bottom-color:var(--bg-2); }
table.rank th { font-size:9.5px; border-bottom:1px solid var(--ink); }
table.rank th:first-child, table.rank td:first-child { padding-left:0; text-align:right; color:var(--muted); width:1.6em; }
table.rank .cat { text-align:left; width:100%; max-width:0; overflow:hidden; text-overflow:ellipsis; }
table.rank td.cat { background:linear-gradient(var(--blue-bar),var(--blue-bar)) left bottom / var(--w) 3px no-repeat; }
table.rank tbody tr:first-child td { font-weight:var(--fw-semi); }
details.defs { margin-top:var(--sp-5); font-size:var(--fs-small); color:var(--ink-2); }
details.defs summary { cursor:pointer; font-weight:var(--fw-semi); color:var(--blue); margin-bottom:var(--sp-3); }
@media print {
  @page { size:letter landscape; margin:0.35in; }
  body { font-size:8pt; }
  .simnote { font-size:7pt; margin-top:3pt; }
  .areas { margin-top:6pt; }
  .area > h2 { padding:3pt 7pt; font-size:7pt; }
  .tile { padding:5pt 7pt 6pt; }
  .tile.partial { padding-left:calc(7pt - 3px); }
  .tile .name { font-size:8pt; }
  .tile .pillar, .sim, .flag { font-size:5.8pt; line-height:9pt; }
  .sim, .flag { padding:0 2.5pt; }
  .tile .value { font-size:16pt; margin-top:2pt; }
  .tile .value .per { font-size:7pt; }
  .tile .value.none { font-size:10pt; }
  .tile .change, .tile .note { font-size:7pt; margin-top:2pt; }
  .tile .tags { margin-top:3pt; gap:2pt 4pt; }
  table.rank { margin-top:3pt; }
  table.rank th, table.rank td { font-size:7pt; padding:1.2pt 3pt; }
  table.rank th { font-size:6pt; }
  .gapnote, details.defs { display:none; }
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
    arrow = "" if v == 0 else ("▲ " if v > 0 else "▼ ")
    partial = ' <span class="muted">(partial period)</span>' if d.get("reason") == "partial_period" else ""
    return f'<span class="chg{cls}">{arrow}{escape(shown)}</span>{partial}'


def note_html(note):
    """The note, with the missing-day sentence the coverage banner already states marked so print can drop it."""
    parts = re.split(r"(?<=\.) ", note)
    return " ".join(f'<span class="gapnote">{escape(p)}</span>' if " has no data on " in p else escape(p) for p in parts)


def pct_cell(x, places):
    return "-" if x is None else f"{x * 100:.{places}f}%"


def ranking_table(k):
    """A top-10 ranking as a compact table; the rule under each category is scaled to the first row."""
    rows = k["rows"] or []
    if not rows:
        return '<div class="value none">No data</div>'
    has_ratio = any(r.get("ratio") is not None for r in rows)
    top = max(r["value"] or 0 for r in rows) or 1
    body = []
    for r in rows:
        name = escape(r["label"])
        bar = max(r["value"] or 0, 0) / top * 100
        ratio = f'<td>{pct_cell(r.get("ratio"), 0)}</td>' if has_ratio else ""
        body.append(f'<tr><td>{r["rank"]}</td><td class="cat" title="{name}" style="--w:{bar:.0f}%">{name}</td>'
                    f'<td>{fmt(r["value"], k["unit"]) or "-"}</td>'
                    f'<td class="share">{pct_cell(r.get("share"), 1)}</td>{ratio}</tr>')
    head = ('<tr><th>#</th><th class="cat">Category</th><th>Amount</th><th class="share">Share</th>'
            + ("<th>Margin</th>" if has_ratio else "") + "</tr>")
    return f'<table class="rank striped"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table>'


def tile(k, prior_label, sim_label, pillars):
    status = k["status"]
    pillar = pillars.get(k.get("pillar"))
    head = f'<div class="name">{escape(k["name"])}</div>'
    tags = ((f'<span class="pillar">{escape(pillar)}</span>' if pillar else "")
            + ('<span class="flag">Partial</span>' if status == "partial" else "")
            + (f'<span class="sim">{escape(sim_label)}</span>' if k["simulated"] else ""))
    tags = f'<div class="tags">{tags}</div>' if tags else ""
    if k["kind"] == "ranking":
        main, change = tags + ranking_table(k), ""
    else:
        shown = fmt(k["value"], k["unit"])
        if shown is None:
            main = '<div class="value none">No data</div>'
        else:
            per = f' <span class="per">per {escape(k["per"])}</span>' if k.get("per") else ""
            main = f'<div class="value">{escape(shown)}{per}</div>'
        prior = fmt(k["prior_value"], k["unit"])
        delta = delta_text(k)
        versus = f' <span class="muted">vs {escape(prior_label)}: {escape(prior)}</span>' if prior is not None else ""
        change = f'<div class="change">{delta}{versus}</div>' if (delta or prior) else ""
        change += tags
    note = f'<div class="note">{note_html(k["note"])}</div>' if k.get("note") else ""
    kind = " ranking" if k["kind"] == "ranking" else ""
    return (f'<div class="tile {status}{kind}" title="{escape(k["definition"])}">'
            f'{head}{main}{change}{note}</div>')


def areas_html(kf, sim_label):
    """The five areas as one grid. An area holding rankings is two tracks wide; the CSS lines the
    tile rows up across areas, so the grid is told how many tile rows there are (--rows)."""
    pillars = {p["id"]: p["name"] for p in kf.get("pillars") or []}
    prior = kf["prior_period"]["label"]
    groups = [(a, [k for k in kf["kpis"] if k["area"] == a["id"]]) for a in kf["areas"]]
    wide = {a["id"]: any(k["kind"] == "ranking" for k in ks) for a, ks in groups}
    scalars = {a["id"]: sum(k["kind"] != "ranking" for k in ks) for a, ks in groups}
    rows = max([len(ks) for a, ks in groups if not wide[a["id"]]]
               + [scalars[a["id"]] + 1 for a, _ in groups if wide[a["id"]]] + [1])
    tracks = " ".join("minmax(0,1.7fr) minmax(0,1.7fr)" if wide[a["id"]] else "minmax(0,1fr)" for a, _ in groups)
    sections = []
    for a, ks in groups:
        attrs = f' class="area wide" style="--span:{rows - scalars[a["id"]]}"' if wide[a["id"]] else ' class="area"'
        sections.append(f'<section{attrs}><h2>{escape(a["name"])}</h2>'
                        + "".join(tile(k, prior, sim_label, pillars) for k in ks) + "</section>")
    return f'<div class="areas" style="--tracks:{tracks};--rows:{rows}">\n' + "\n".join(sections) + "\n</div>"


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


def facts_html(kf):
    period, prior, cov, internal = kf["period"], kf["prior_period"], kf["coverage"], kf.get("internal_data")
    counts = [(sum(k["status"] == s for k in kf["kpis"]), name) for s, name in
              (("ok", "ok"), ("partial", "partial"), ("no_data", "no data"))]
    not_stored = "" if prior.get("available", True) else ' <span class="muted">(not stored)</span>'
    return facts([
        ("Period", escape(span(period["start"], period["through"])), ""),
        ("Compared with", escape(prior["label"]) + not_stored, ""),
        ("Marketplace data", f'{cov["days_complete"]} of {cov["days_expected"]} days complete',
         "good" if cov["complete"] else "bad"),
        ("KPI status", " · ".join(f"{n} {name}" for n, name in counts if n), ""),
        ("Internal data", escape(f'{internal["label"]}, as of {internal["as_of"]}') if internal else "None stored",
         "" if internal else "bad"),
    ])


def render(kf):
    period = kf["period"]
    sim_label = (kf.get("internal_data") or {}).get("label") or "Simulated internal data"
    text, alert = headline(kf)
    cov = kf["coverage"]
    coverage = ""
    if cov["gaps"]:
        gaps = ", ".join(f'{g["marketplace"]} {g["date"]} ({g["status"]})' for g in cov["gaps"][:12])
        more = f" and {len(cov['gaps']) - 12} more" if len(cov["gaps"]) > 12 else ""
        coverage = (f'<div class="banner coverage"><strong>Data missing:</strong> {escape(gaps)}{more}. '
                    f'KPIs that use these days are marked partial.</div>')
    simulated = sum(k["simulated"] for k in kf["kpis"])
    simnote = (f'<p class="simnote">{simulated} of {len(kf["kpis"])} KPIs use {escape(sim_label.lower())} '
               f'(badged). {escape(kf["definitions"].get("simulated", ""))}</p>') if simulated else ""
    if not kf.get("internal_data"):
        simnote = '<p class="simnote">No internal data stored for this period: KPIs that need it show "No data".</p>'
    defs = "".join(f"<div><dt>{escape(k['name'])}</dt><dd>{escape(k['definition'])}</dd></div>" for k in kf["kpis"])
    top_defs = " ".join(escape(v) for v in kf["definitions"].values())
    cadence = {"day": "Daily", "week": "Weekly", "month": "Monthly"}.get(period["type"], period["type"].title())
    body = (f'<header><h1>COO scorecard: {escape(period["label"])}</h1>'
            f'<p>{cadence} · {len(kf["kpis"])} KPIs in {len(kf["areas"])} areas · '
            f'generated {escape(stamp(kf["generated_at"]))}</p></header>'
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>'
            f'{facts_html(kf)}{coverage}{simnote}\n'
            f'{areas_html(kf, sim_label)}\n'
            f'<section class="foot"><p>{top_defs}</p></section>'
            f'<details class="defs"><summary>KPI definitions</summary><dl>{defs}</dl></details>'
            f'<p class="nav"><a href="index.html">All scorecards</a> · <a href="../index.html">Reports</a></p>')
    return PAGE.substitute(title=f"COO scorecard {period['id']}", css=CSS + SCORECARD_CSS, body=body)


def render_index(dest):
    pages = sorted((f for f in dest.glob("*.html") if re.fullmatch(r"(day|week|month)-[\dW-]+", f.stem)),
                   key=lambda f: f.stem, reverse=True)
    items = "\n".join(f'  <li><a href="{f.name}">{escape(f.stem)}</a></li>' for f in pages)
    body = (f'<header><h1>COO scorecards</h1><p>{len(pages)} page(s)</p></header>'
            f'<ul class="days">\n{items or "<li>None yet</li>"}\n</ul><p class="nav"><a href="../index.html">Reports</a></p>')
    return PAGE.substitute(title="COO scorecards", css=CSS + SCORECARD_CSS, body=body)


def build(kpi_file, dest=DEST):
    """Render one KPI file; keep a copy of the JSON next to the page. Returns the page path."""
    kf = json.loads(Path(kpi_file).read_text(encoding="utf-8"))
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    name = f"{kf['period']['type']}-{kf['period']['id']}"
    page = dest / f"{name}.html"
    page.write_text(render(kf), encoding="utf-8")
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
