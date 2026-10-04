"""COO scorecard page (O2.1, O2.4): renders a KPI file from `python -m recon.kpi` (docs/contracts/kpi.md).

The page does no arithmetic and decides nothing about missing data: every number, status, note,
change and badge comes from the file. Five areas, three KPIs each, in the file's order; the two
top-10 rankings as tables. Simulated KPIs carry the file's `internal_data.label` as a badge.

Default view: value, change and badges. Each KPI's formula, source, comparison and note sit behind
its info button; the methodology and all definitions are in accordions. In print the notes become
numbered one-line footnotes, and the page fits one landscape sheet (five area columns).

    python -m reports.scorecard --kpi-file out/kpi/month-2026-09.json   # -> reports/scorecard/month-2026-09.html
    python -m reports.scorecard --period month                          # out/kpi/latest-month.json
"""
import argparse
import json
import re
import shutil
from html import escape
from pathlib import Path

from reports.pulse import money
from reports.theme import CSS, PAGE, accordion, facts, info, print_notes, span, stamp

ROOT = Path(__file__).resolve().parent.parent
KPI_DIR = ROOT / "out" / "kpi"
DEST = ROOT / "reports" / "scorecard"

SCORECARD_CSS = """
:root { --page:1520px; --bar:rgba(0,84,164,.32); }

/* Five area cards. Wide screens and print: one grid, a column per area (Category + Customer takes
   two so its rankings sit side by side), tile rows lined up across the cards via subgrid. */
.areas { display:grid; grid-template-columns:minmax(0,1fr); gap:var(--sp-3); margin-top:var(--sp-5); }
.area { display:grid; align-content:start; min-width:0; background:var(--card); border:1px solid var(--line);
  border-radius:var(--radius); box-shadow:var(--shadow); }
.area > h2 { padding:var(--sp-4) var(--sp-5) var(--sp-1); font-size:var(--fs-label); font-weight:var(--fw-semi);
  letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }
.area.wide > h2, .area.wide > .tile:not(.ranking) { grid-column:1 / -1; }
@media (min-width:720px) {
  .areas { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .area.wide { grid-column:1 / -1; grid-template-columns:repeat(2,minmax(0,1fr)); }
  .area.wide > .tile.ranking { border-top:0; }
  .area.wide > .tile.ranking + .tile.ranking { border-left:1px solid var(--hair); }
}
@media (min-width:1180px), print {
  .areas { grid-template-columns:var(--tracks); grid-template-rows:auto repeat(var(--rows),auto); row-gap:0; }
  .area { grid-row:1 / -1; grid-template-rows:subgrid; }
  .area.wide { grid-column:span 2; grid-template-columns:subgrid; column-gap:0; }
  .area.wide > .tile.ranking { grid-row:span var(--span); }
}

/* KPI tile: name and info button, the value, the change, badges */
.tile { min-width:0; padding:var(--sp-3) var(--sp-5) var(--sp-4); border-top:1px solid var(--hair); }
.area > h2 + .tile { border-top:0; }
.tile .name { display:flex; align-items:flex-start; gap:2px; font-size:13px; font-weight:var(--fw-medium); line-height:1.3; color:var(--muted); }
.tile .name .info { flex:none; margin-top:-1px; }
.tile .value { margin-top:6px; font-size:var(--fs-metric); font-weight:var(--fw-bold); line-height:1.1; letter-spacing:-0.03em; }
.tile .value .per { font-size:13px; font-weight:var(--fw-regular); letter-spacing:-0.01em; color:var(--muted); white-space:nowrap; }
.tile .value.none { font-size:var(--fs-lead); font-weight:var(--fw-semi); letter-spacing:-0.015em; color:var(--faint); }
.tile .change { margin-top:var(--sp-1); font-size:var(--fs-small); color:var(--muted); }
.tile .tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:var(--sp-2); }
.sim, .flag { display:inline-block; height:18px; padding:0 7px; border-radius:980px; font-size:10px; font-weight:var(--fw-semi);
  line-height:18px; letter-spacing:.04em; text-transform:uppercase; white-space:nowrap; }
.sim { background:var(--warn-bg); color:var(--warn); }
.flag { background:var(--bad-bg); color:var(--bad); }

/* Top-10 rankings: the rule under each category is scaled to the leader */
table.rank { min-width:0; margin-top:var(--sp-2); }
table.rank th, table.rank td { padding:5px 6px; font-size:var(--fs-small); }
table.rank th { padding-top:var(--sp-1); font-size:10px; }
table.rank th:first-child, table.rank td:first-child { width:1.6em; padding-left:0; text-align:right; color:var(--faint); }
table.rank th:last-child, table.rank td:last-child { padding-right:0; }
table.rank .cat { text-align:left; width:100%; max-width:0; overflow:hidden; text-overflow:ellipsis; }
table.rank td.cat { background-image:linear-gradient(var(--bar),var(--bar)); background-position:left bottom;
  background-size:var(--w) 3px; background-repeat:no-repeat; }
table.rank tbody tr:first-child td { font-weight:var(--fw-semi); }
.foot-accs { margin-top:var(--sp-6); }
@media print {
  @page { size:letter landscape; margin:0.35in; }
  body { font-size:8pt; }
  header h1 { font-size:13pt; }
  .summary { padding:3pt 7pt; font-size:9pt; }
  .areas { margin-top:5pt; column-gap:5pt; }
  .area { box-shadow:none; border-color:#d2d2d7; border-radius:8px; }
  .area > h2 { padding:4pt 7pt 1pt; font-size:6.5pt; }
  .tile { padding:3pt 7pt 4pt; }
  .tile .name { font-size:7pt; }
  .tile .value { font-size:14pt; margin-top:1pt; }
  .tile .value .per { font-size:6.5pt; white-space:nowrap; }
  .tile .value.none { font-size:9pt; }
  .tile .change { font-size:6.5pt; line-height:1.25; margin-top:1pt; }
  .tile .tags { margin-top:2pt; gap:2pt; }
  .sim, .flag { height:auto; line-height:8pt; padding:0 3pt; font-size:5.5pt; }
  table.rank { margin-top:2pt; }
  table.rank th, table.rank td { font-size:6.5pt; padding:0.8pt 2.5pt; }
  table.rank th { font-size:5.5pt; }
}
"""

DELTA_REASON = {"no_prior_period": "no prior period", "current_no_data": "", "not_applicable": ""}
SOURCE = {"files": "Marketplace exports", "internal": "Goodwill internal data", "mixed": "Marketplace exports and internal data"}


def fmt(value, unit):
    """A KPI value in its unit; `per` is appended by the tile."""
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
    return f'<span class="chg{cls}">{arrow}{escape(shown)}</span>'


def footnote_text(note):
    """The note without the missing-day sentence, which the coverage banner already states."""
    return " ".join(p for p in re.split(r"(?<=\.) ", note or "") if p and " has no data on " not in p)


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
    return f'<table class="rank"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table>'


def tip(k, prior_label, sim_label, pillars):
    """The info popover: formula, source, comparison, pillar, coverage and the full note."""
    prior = fmt(k.get("prior_value"), k["unit"])
    partial = " (partial period)" if (k["delta"] or {}).get("reason") == "partial_period" else ""
    source = SOURCE.get(k.get("source"), k.get("source") or "")
    return info(f'tip-{k["id"].replace(".", "-")}', k["name"], [
        ("Formula", escape(k["definition"])),
        ("Source", escape(source + (f" ({sim_label.lower()})" if k["simulated"] else ""))),
        ("Compared with", escape(f"{prior_label}: {prior}{partial}") if prior is not None else ""),
        ("Pillar", escape(pillars.get(k.get("pillar"), ""))),
        ("Covers", escape(", ".join(k["covers"])) if k.get("covers") else ""),
        ("Note", escape(k["note"]) if k.get("note") else ""),
    ])


def tile(k, prior_label, sim_label, pillars, mark=""):
    status = k["status"]
    head = f'<div class="name has-tip"><span>{escape(k["name"])}{mark}</span>{tip(k, prior_label, sim_label, pillars)}</div>'
    tags = (('<span class="flag">Partial</span>' if status == "partial" else "")
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
        versus = f' <span class="muted">vs {escape(prior)}</span>' if prior is not None else ""
        change = (f'<div class="change">{delta}{versus}</div>' if (delta or prior) else "") + tags
    kind = " ranking" if k["kind"] == "ranking" else ""
    return f'<div class="tile {status}{kind}">{head}{main}{change}</div>'


def footnotes(kf):
    """Number each distinct note (the missing-day sentence left out); returns ({kpi id: mark}, lines)."""
    numbers, names, marks = {}, {}, {}
    for k in kf["kpis"]:
        text = footnote_text(k.get("note"))
        if text:
            n = numbers.setdefault(text, len(numbers) + 1)
            names.setdefault(text, []).append(k["name"])
            marks[k["id"]] = f'<sup class="fn">{n}</sup>'
    lines = [f"<sup>{n}</sup> {escape(', '.join(names[t]))}: {escape(t)}" for t, n in numbers.items()]
    return marks, lines


def areas_html(kf, sim_label, marks):
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
                        + "".join(tile(k, prior, sim_label, pillars, marks.get(k["id"], "")) for k in ks) + "</section>")
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


def simulated_note(kf, sim_label):
    if not kf.get("internal_data"):
        return 'No internal data stored for this period: KPIs that need it show "No data".'
    simulated = sum(k["simulated"] for k in kf["kpis"])
    if not simulated:
        return ""
    return (f'{simulated} of {len(kf["kpis"])} KPIs use {sim_label.lower()} (badged). '
            f'{kf["definitions"].get("simulated", "")}').strip()


def facts_html(kf, sim_note):
    period, prior, cov, internal = kf["period"], kf["prior_period"], kf["coverage"], kf.get("internal_data")
    counts = [(sum(k["status"] == s for k in kf["kpis"]), name) for s, name in
              (("ok", "ok"), ("partial", "partial"), ("no_data", "no data"))]
    not_stored = "" if prior.get("available", True) else ' <span class="muted">(not stored)</span>'
    about = info("tip-internal", "internal data", [("Internal data", escape(sim_note))]) if sim_note else ""
    return facts([
        ("Period", escape(span(period["start"], period["through"])), ""),
        ("Compared with", escape(prior["label"]) + not_stored, ""),
        ("Marketplace data", f'{cov["days_complete"]} of {cov["days_expected"]} days complete',
         "good" if cov["complete"] else "bad"),
        ("KPI status", " · ".join(f"{n} {name}" for n, name in counts if n), ""),
        ("Internal data", escape(f'{internal["label"]}, as of {internal["as_of"]}') if internal else "None stored",
         "" if internal else "bad", about),
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
    sim_note = simulated_note(kf, sim_label)
    marks, notes = footnotes(kf)
    methodology = "".join(f"<p>{escape(v)}</p>" for v in kf["definitions"].values())
    defs = "".join(f"<div><dt>{escape(k['name'])}</dt><dd>{escape(k['definition'])}</dd></div>" for k in kf["kpis"])
    formulas = f"{len(kf['kpis'])} formulas"
    cadence = {"day": "Daily", "week": "Weekly", "month": "Monthly"}.get(period["type"], period["type"].title())
    body = (f'<header><h1>COO scorecard: {escape(period["label"])}</h1>'
            f'<p>{cadence} · {len(kf["kpis"])} KPIs in {len(kf["areas"])} areas · '
            f'generated {escape(stamp(kf["generated_at"]))}</p></header>'
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>'
            f'{facts_html(kf, sim_note)}{coverage}\n'
            f'{areas_html(kf, sim_label, marks)}\n'
            f'<div class="foot-accs">{accordion("Methodology", methodology, "periods, comparison, simulated data")}'
            f'{accordion("KPI definitions", f"<dl>{defs}</dl>", formulas)}</div>'
            + print_notes([escape(sim_note)] + notes
                          + [escape(" ".join(v for key, v in kf["definitions"].items() if key != "simulated" or not sim_note))])
            + '<p class="nav"><a href="index.html">All scorecards</a> · <a href="../index.html">Reports</a></p>')
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
