"""KPI groups from decision 006, for any period: used by the weekly dashboard and the monthly scorecard.

Inputs are the daily pulse files for the period (real data, through the engine and the pulse)
and the mock Goodwill internal API (reports/mock_api.py) for the company data we don't have.
Every KPI carries its source, "files" or "simulated", and the HTML badges simulated ones.
"""
import csv
import json
from datetime import timedelta
from html import escape
from string import Template

from reports import mock_api
from reports.pulse import LABELS, money

MARKETS = ["shopgoodwill", "amazon", "ebay"]  # "other" has no source yet
SUMS = ["gross_cents", "refunds_cents", "revenue_cents", "fees_cents", "orders", "customers"]
SECTIONS = ["Financial", "Listings & Production", "Sales Effectiveness", "Category Effectiveness",
            "Customer & Marketplace"]

KPI_CSS = """
.section { margin:var(--sp-6) 0 0; }
.section h2 { display:flex; align-items:center; gap:var(--sp-4); margin:0; padding-bottom:var(--sp-2);
  border-bottom:var(--bd-blue); color:var(--ink); font-size:var(--fs-label); font-weight:var(--fw-bold);
  letter-spacing:.06em; text-transform:uppercase; }
.section > .badge { margin:var(--sp-3) 0 0; }
.cards { display:flex; flex-wrap:wrap; gap:1px; background:var(--rule); border:var(--bd); border-top:0; }
.card.kpi { flex:1 1 200px; margin:0; padding:var(--sp-4) var(--sp-5); background:var(--bg); overflow:visible; }
.badge { display:inline-block; margin-top:var(--sp-3); padding:0 var(--sp-2); font-size:9.5px; font-weight:var(--fw-semi);
  letter-spacing:.06em; text-transform:uppercase; line-height:15px; border:1px solid; }
.badge.files { color:var(--blue); border-color:var(--blue); background:var(--bg); }
.badge.simulated { color:var(--ink-2); border-color:var(--rule); background:var(--bg-2); }
.simnote { margin:var(--sp-4) 0 0; padding:var(--sp-3) var(--sp-5); background:var(--bg-1); border:var(--bd);
  font-size:var(--fs-small); color:var(--ink-2); }
.card table { min-width:520px; }
@media print {
  @page { size:letter portrait; margin:0.4in; }
  body { font-size:8pt; }
  .simnote { font-size:7pt; padding:3pt 6pt; margin-top:4pt; }
  .section { margin-top:6pt; }
  .section h2 { font-size:6.5pt; padding-bottom:1pt; }
  .cards { flex-wrap:wrap; }
  .card.kpi { flex-basis:22%; padding:3pt 6pt; break-inside:avoid; }
  .kpi .label { font-size:6.5pt; }
  .kpi .value { font-size:12pt; }
  .card table { min-width:0; }
  .card th, .card td { padding:1pt 5pt; font-size:7pt; }
  .badge { font-size:5.5pt; line-height:8pt; padding:0 2.5pt; margin-top:2pt; }
  section.foot { font-size:6.5pt; margin-top:5pt; }
  section.foot h2 { margin:3pt 0 1pt; }
  section.foot dl { gap:0 8pt; }
}
"""
SIMNOTE = """<p class="simnote"><strong>Simulated internal data:</strong> KPIs marked SIMULATED use labor hours, listings,
cost of goods or category mix from a mock of Goodwill's internal systems, not Goodwill figures. KPIs marked
FROM MARKETPLACE FILES are calculated from the exports.</p>"""

PAGE_BODY = Template("""<header>
  <h1>$title</h1>
  <p>$range · $coverage$mock</p>
</header>
<p class="summary$summary_class">$summary</p>
$simnote
$sections
<section class="foot">
  <h2>Definitions</h2>
  <dl>
$definitions
  </dl>
  <p class="nav">$nav</p>
</section>""")


def totals(pulses):
    """Sum each marketplace over the days it had data; count those days."""
    out = {m: {**{k: 0 for k in SUMS}, "days": 0} for m in MARKETS}
    for p in pulses:
        for m in MARKETS:
            row = p["marketplaces"].get(m, {})
            if row.get("status") == "ok":
                out[m]["days"] += 1
                for k in SUMS:
                    out[m][k] += row[k] or 0
    out["all"] = {k: sum(out[m][k] for m in MARKETS) for k in SUMS}
    return out


def ratio(a, b):
    return a / b if b else None


def compute(start, end, pulses, prior, prior_days, prior_name):
    """KPI list for [start, end]. `prior` = the previous period's pulses (`prior_days` long), compared
    only when every prior day has a pulse.
    Each KPI: section, kpi, marketplace, value, unit, source."""
    t, tp = totals(pulses), totals(prior) if prior else None
    labor = mock_api.labor_hours(start, end)["hours"]
    lst = mock_api.listings(start, end)["new_listings"]
    cpo = mock_api.cost_per_order(start, end)["cost_per_order_cents"]
    mix = mock_api.category_mix(start, end)["mix"]
    rev, orders = t["all"]["revenue_cents"], t["all"]["orders"]
    cogs = sum(t[m]["orders"] * cpo[m] for m in MARKETS)
    out = []

    def add(section, kpi, value, unit, source, market="all"):
        out.append({"section": section, "kpi": kpi, "marketplace": market, "value": value, "unit": unit,
                    "source": source})

    F, L, S, C, M = SECTIONS
    add(F, "Net revenue", rev, "cents", "files")
    add(F, "Marketplace fees % of revenue", ratio(t["all"]["fees_cents"], rev), "pct", "files")
    add(F, "Gross margin (est.)", ratio(rev - cogs, rev), "pct", "simulated")
    add(F, "Revenue per labor hour", ratio(rev, labor["total"]), "cents", "simulated")

    add(L, "New listings", sum(lst.values()), "count", "simulated")
    add(L, "Listings per listing hour", ratio(sum(lst.values()), labor["processing_listing"]), "number", "simulated")
    add(L, "Orders shipped per pick-pack hour", ratio(orders, labor["pick_pack_ship"]), "number", "simulated")
    add(L, "Labor hours", labor["total"], "hours", "simulated")

    add(S, "Average order value", ratio(rev, orders), "cents", "files")
    add(S, "Refund rate", ratio(-t["all"]["refunds_cents"], t["all"]["gross_cents"]), "pct", "files")
    add(S, "Sell-through (orders / new listings)", ratio(orders, sum(lst.values())), "pct", "simulated")
    prev = tp["all"]["revenue_cents"] if tp and len(prior) == prior_days else None
    add(S, f"Revenue vs prior {prior_name}", ratio(rev - prev, prev) if prev else None, "pct", "files")

    for cat in mock_api.CATEGORIES:
        add(C, cat, round(sum(t[m]["revenue_cents"] * mix[m][cat] for m in MARKETS)), "cents", "simulated")

    for m in MARKETS:
        add(M, "Revenue", t[m]["revenue_cents"], "cents", "files", m)
        add(M, "Share of revenue", ratio(t[m]["revenue_cents"], rev), "pct", "files", m)
        add(M, "Orders", t[m]["orders"], "count", "files", m)
        add(M, "Customers (sum of days)", t[m]["customers"], "count", "files", m)
        add(M, "Days with data", t[m]["days"], "count", "files", m)
    return out, t


def pct(v):
    """One decimal, or two when the change is tiny, so +0.05% doesn't read as 0.0%."""
    return f"{v * 100:.2f}%" if 0 < abs(v * 100) < 0.1 else f"{v * 100:.1f}%"


def fmt(k):
    v, unit = k["value"], k["unit"]
    if v is None:
        return "n/a"
    if unit == "cents":
        return money(round(v))
    if unit == "pct":
        return pct(v)
    if unit == "hours":
        return f"{v:,.1f} h"
    if unit == "count":
        return f"{v:,}"
    return f"{v:,.1f}"


def badge(source):
    if source == "simulated":
        return '<span class="badge simulated">Simulated internal data</span>'
    return '<span class="badge files">From marketplace files</span>'


def sections_html(rows, t):
    by_section = {s: [k for k in rows if k["section"] == s] for s in SECTIONS}
    parts = []
    for s in SECTIONS[:3]:
        cards = "\n".join(f'  <div class="card kpi"><div class="label">{escape(k["kpi"])}</div>'
                          f'<div class="value">{fmt(k)}</div>{badge(k["source"])}</div>' for k in by_section[s])
        parts.append(f'<div class="section"><h2>{escape(s)}</h2><div class="cards">\n{cards}\n</div></div>')
    rev = t["all"]["revenue_cents"]
    cats = sorted(by_section[SECTIONS[3]], key=lambda k: -k["value"])
    cat_rows = "\n".join(f'<tr><td>{escape(k["kpi"])}</td><td>{fmt(k)}</td>'
                         f'<td>{(k["value"] / rev * 100 if rev else 0):.1f}%</td></tr>' for k in cats)
    parts.append(f'<div class="section"><h2>{SECTIONS[3]}</h2>{badge("simulated")}'
                 f'<div class="card"><table class="striped"><thead><tr><th>Category</th><th>Revenue (est.)</th>'
                 f'<th>Share</th></tr></thead><tbody>\n{cat_rows}\n</tbody></table></div></div>')
    mk = {(k["marketplace"], k["kpi"]): k for k in by_section[SECTIONS[4]]}
    names = ("Revenue", "Share of revenue", "Orders", "Customers (sum of days)", "Days with data")
    m_rows = "\n".join(f'<tr><td>{LABELS[m]}</td>' + "".join(f'<td>{fmt(mk[(m, n)])}</td>' for n in names) + "</tr>"
                       for m in MARKETS)
    parts.append(f'<div class="section"><h2>{SECTIONS[4]}</h2>{badge("files")}'
                 f'<div class="card"><table><thead><tr><th>Marketplace</th><th>Revenue</th>'
                 f'<th>Share</th><th>Orders</th><th>Customers</th><th>Days with data</th></tr></thead><tbody>\n'
                 f'{m_rows}\n</tbody></table></div></div>')
    return "\n".join(parts)


def summary(rows, t, period_days, prior_name):
    rev = t["all"]["revenue_cents"]
    complete = all(t[m]["days"] == period_days for m in MARKETS)
    growth = next(k for k in rows if k["kpi"].startswith("Revenue vs prior"))["value"]
    text = f"Net revenue {money(rev)} from {t['all']['orders']:,} orders"
    if growth is not None:
        text += f", {'up' if growth >= 0 else 'down'} {pct(abs(growth))} vs the prior {prior_name}"
    if rev:
        top = max(MARKETS, key=lambda m: t[m]["revenue_cents"])
        text += f"; {LABELS[top]} strongest ({t[top]['revenue_cents'] / rev:.0%} of revenue)"
    if not complete:
        text += "; some marketplace days missing, totals are partial"
    return text + ".", complete


def definitions(period_text):
    defs = {
        "Revenue": "Sales minus refunds, before marketplace fees; excludes shipping and tax (as in the nightly pulse).",
        "Period": period_text,
        "Customers": "Sum of the daily counts, so a buyer who orders on two days counts twice.",
        "Gross margin (est.)": "(Revenue - orders x simulated cost per order) / revenue.",
        "Sell-through": "Orders / simulated new listings in the period (a proxy until listing ids are joined).",
        "Category revenue": "Each marketplace's real revenue split by a simulated category mix.",
    }
    return "\n".join(f"    <dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in defs.items())


def write_csv(path, period_column, period, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([period_column, "Section", "KPI", "Marketplace", "Value", "Unit", "Source"])
        for k in rows:
            v = k["value"]
            value = "" if v is None else (f"{v / 100:.2f}" if k["unit"] == "cents" else
                                          f"{v:.4f}" if k["unit"] in ("pct", "number") else v)
            unit = {"cents": "USD", "pct": "ratio"}.get(k["unit"], k["unit"])
            w.writerow([period, k["section"], k["kpi"], LABELS.get(k["marketplace"], "All"), value, unit,
                        "Simulated internal data" if k["source"] == "simulated" else "Marketplace files"])


def load_days(src, start, end):
    pulses, d = [], start
    while d <= end:
        f = src / f"{d:%Y-%m-%d}.json"
        if f.exists():
            pulses.append(json.loads(f.read_text(encoding="utf-8")))
        d += timedelta(days=1)
    return pulses
