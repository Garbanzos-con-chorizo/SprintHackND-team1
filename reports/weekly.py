"""Weekly dashboard: a week of daily pulses plus the KPI groups from decision 005.

Reads out/pulse/<date>.json for the ISO week (Monday to Sunday), adds internal data from the
mock Goodwill internal API (reports/mock_api.py), and writes reports/weekly/<YYYY>-W<WW>.html,
<YYYY>-W<WW>.csv and index.html. Every KPI says where it comes from: "files" (the marketplace
exports, through the pulse) or "simulated" (needs the mock API, labelled on the page).

    python -m reports.weekly --week 2026-W38 [--src out/pulse] [--dest reports/weekly]
    python -m reports.weekly --date 2026-09-16      # the week containing that day
"""
import argparse
import csv
import json
import re
from datetime import date, timedelta
from html import escape
from pathlib import Path
from string import Template

from reports import mock_api
from reports.pulse import CSS, LABELS, PAGE, money

ROOT = Path(__file__).resolve().parent.parent
MARKETS = ["shopgoodwill", "amazon", "ebay"]  # "other" has no source yet
SUMS = ["gross_cents", "refunds_cents", "revenue_cents", "fees_cents", "orders", "customers"]
SECTIONS = ["Financial", "Listings & Production", "Sales Effectiveness", "Category Effectiveness",
            "Customer & Marketplace"]
CSV_COLUMNS = ["Week", "Section", "KPI", "Marketplace", "Value", "Unit", "Source"]

WEEK_CSS = """
.section { margin:22px 0 0; }
.section h2 { font-size:15px; color:var(--primary); margin:0 0 8px; text-transform:uppercase; letter-spacing:.04em; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; }
.card.kpi { padding:14px 16px; overflow:visible; }
.badge { display:inline-block; margin-top:6px; font-size:11px; font-weight:700; padding:2px 8px; border-radius:6px; }
.badge.files { color:var(--primary); border:1px solid var(--primary); }
.badge.simulated { color:var(--ink); background:#fff4cc; border:1px dashed #8a6d00; }
.simnote { background:#fff4cc; border:1px dashed #8a6d00; border-radius:10px; padding:10px 14px; margin:16px 0 0; font-size:14px; }
.card table { min-width:520px; }
"""

DAY = Template("""<header>
  <h1>Weekly dashboard: week $week_no, $year</h1>
  <p>Goodwill Michiana e-commerce · $range · $coverage$mock</p>
</header>
<p class="summary$summary_class">$summary</p>
<p class="simnote"><strong>Simulated internal data:</strong> numbers with a yellow badge use labor hours, listings,
cost of goods or category mix from a mock of Goodwill's internal systems. They show how the dashboard works,
not Goodwill's real figures. Blue-badge numbers come from the marketplace exports.</p>
$sections
<section class="foot">
  <h2>Definitions</h2>
  <dl>
$definitions
  </dl>
  <p class="nav"><a href="index.html">All weeks</a></p>
</section>""")


def parse_week(text):
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", text)
    if not m:
        raise argparse.ArgumentTypeError("week must look like 2026-W38")
    return date.fromisocalendar(int(m[1]), int(m[2]), 1)


def load_week(src, monday):
    pulses = []
    for i in range(7):
        f = Path(src) / f"{monday + timedelta(days=i):%Y-%m-%d}.json"
        if f.exists():
            pulses.append(json.loads(f.read_text(encoding="utf-8")))
    return pulses


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


def kpis(monday, pulses, prior):
    """The weekly KPI list. Each: section, kpi, marketplace, value, unit, source."""
    sunday = monday + timedelta(days=6)
    t, tp = totals(pulses), totals(prior) if prior else None
    labor = mock_api.labor_hours(monday, sunday)["hours"]
    lst = mock_api.listings(monday, sunday)["new_listings"]
    cpo = mock_api.cost_per_order(monday, sunday)["cost_per_order_cents"]
    mix = mock_api.category_mix(monday, sunday)["mix"]
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
    prev = tp["all"]["revenue_cents"] if tp and len(prior) == 7 else None
    add(S, "Revenue vs prior week", ratio(rev - prev, prev) if prev else None, "pct", "files")

    for cat in mock_api.CATEGORIES:
        cat_rev = sum(t[m]["revenue_cents"] * mix[m][cat] for m in MARKETS)
        add(C, cat, round(cat_rev), "cents", "simulated")

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


def render(monday, pulses, rows, t):
    sunday = monday + timedelta(days=6)
    year, week_no, _ = monday.isocalendar()
    by_section = {s: [k for k in rows if k["section"] == s] for s in SECTIONS}
    parts = []
    for s in SECTIONS[:3]:
        cards = "\n".join(f'  <div class="card kpi"><div class="label">{escape(k["kpi"])}</div>'
                          f'<div class="value">{fmt(k)}</div>{badge(k["source"])}</div>' for k in by_section[s])
        parts.append(f'<div class="section"><h2>{escape(s)}</h2><div class="cards">\n{cards}\n</div></div>')
    cats = sorted(by_section[SECTIONS[3]], key=lambda k: -k["value"])
    rev = t["all"]["revenue_cents"]
    cat_rows = "\n".join(f'<tr><td>{escape(k["kpi"])}</td><td>{fmt(k)}</td>'
                         f'<td>{(k["value"] / rev * 100 if rev else 0):.1f}%</td></tr>' for k in cats)
    parts.append(f'<div class="section"><h2>{SECTIONS[3]}</h2>{badge("simulated")}'
                 f'<div class="card" style="margin-top:8px"><table><thead><tr><th>Category</th><th>Revenue (est.)</th>'
                 f'<th>Share</th></tr></thead><tbody>\n{cat_rows}\n</tbody></table></div></div>')
    mk = {(k["marketplace"], k["kpi"]): k for k in by_section[SECTIONS[4]]}
    m_rows = "\n".join(
        f'<tr><td>{LABELS[m]}</td>' + "".join(f'<td>{fmt(mk[(m, name)])}</td>' for name in
                                             ("Revenue", "Share of revenue", "Orders", "Customers (sum of days)",
                                              "Days with data")) + "</tr>" for m in MARKETS)
    parts.append(f'<div class="section"><h2>{SECTIONS[4]}</h2>{badge("files")}'
                 f'<div class="card" style="margin-top:8px"><table><thead><tr><th>Marketplace</th><th>Revenue</th>'
                 f'<th>Share</th><th>Orders</th><th>Customers</th><th>Days with data</th></tr></thead><tbody>\n'
                 f'{m_rows}\n</tbody></table></div></div>')

    days_ok = len(pulses)
    complete = all(t[m]["days"] == 7 for m in MARKETS)
    top = max(MARKETS, key=lambda m: t[m]["revenue_cents"])
    growth = next(k for k in rows if k["kpi"] == "Revenue vs prior week")["value"]
    summary = f"Net revenue {money(rev)} from {t['all']['orders']:,} orders"
    if growth is not None:
        summary += f", {'up' if growth >= 0 else 'down'} {pct(abs(growth))} vs the prior week"
    summary += f"; {LABELS[top]} strongest ({t[top]['revenue_cents'] / rev:.0%} of revenue)" if rev else ""
    if not complete:
        summary += "; some marketplace days missing, totals are partial"
    defs = {
        "Revenue": "Sales minus refunds, before marketplace fees; excludes shipping and tax (as in the nightly pulse).",
        "Week": "ISO week, Monday to Sunday, Eastern time.",
        "Customers": "Sum of the daily counts, so a buyer who orders on two days counts twice.",
        "Gross margin (est.)": "(Revenue - orders x simulated cost per order) / revenue.",
        "Sell-through": "Orders this week / simulated new listings this week (a proxy until listing ids are joined).",
        "Category revenue": "Each marketplace's real revenue split by a simulated category mix.",
    }
    body = DAY.substitute(
        week_no=week_no, year=year,
        range=f"{monday:%a %b} {monday.day} to {sunday:%a %b} {sunday.day}, {sunday.year}",
        coverage=f"{days_ok} of 7 daily pulses",
        mock=" · <strong>mock data</strong>" if any(p.get("mock") for p in pulses) else "",
        summary=escape(summary) + ".", summary_class="" if complete else " alert",
        sections="\n".join(parts),
        definitions="\n".join(f"    <dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in defs.items()),
    )
    return PAGE.substitute(title=f"Weekly dashboard {year}-W{week_no:02d}", css=CSS + WEEK_CSS, body=body)


def write_csv(path, week, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for k in rows:
            v = k["value"]
            value = "" if v is None else (f"{v / 100:.2f}" if k["unit"] == "cents" else
                                          f"{v:.4f}" if k["unit"] in ("pct", "number") else v)
            unit = {"cents": "USD", "pct": "ratio"}.get(k["unit"], k["unit"])
            w.writerow([week, k["section"], k["kpi"], LABELS.get(k["marketplace"], "All"), value, unit,
                        "Simulated internal data" if k["source"] == "simulated" else "Marketplace files"])


def render_index(dest):
    weeks = sorted((f.stem for f in dest.glob("*.html") if re.fullmatch(r"\d{4}-W\d{2}", f.stem)), reverse=True)
    items = "\n".join(f'  <li><a href="{w}.html">{w}{" (latest)" if i == 0 else ""}</a></li>'
                      for i, w in enumerate(weeks))
    body = (f'<header><h1>Weekly dashboard</h1><p>Goodwill Michiana e-commerce · {len(weeks)} week(s)</p></header>'
            f'<ul class="days">\n{items}\n</ul>')
    return PAGE.substitute(title="Weekly dashboard", css=CSS + WEEK_CSS, body=body)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--week", type=parse_week, help="ISO week, e.g. 2026-W38")
    g.add_argument("--date", type=date.fromisoformat, help="any day in the week")
    ap.add_argument("--src", default=str(ROOT / "out" / "pulse"))
    ap.add_argument("--dest", default=str(ROOT / "reports" / "weekly"))
    args = ap.parse_args(argv)
    monday = args.week or args.date - timedelta(days=args.date.weekday())
    pulses = load_week(args.src, monday)
    if not pulses:
        raise SystemExit(f"no pulse files for the week of {monday} in {args.src}")
    prior = load_week(args.src, monday - timedelta(days=7))
    rows, t = kpis(monday, pulses, prior)
    year, week_no, _ = monday.isocalendar()
    name = f"{year}-W{week_no:02d}"
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{name}.html").write_text(render(monday, pulses, rows, t), encoding="utf-8")
    write_csv(dest / f"{name}.csv", name, rows)
    (dest / "index.html").write_text(render_index(dest), encoding="utf-8")
    sim = sum(k["source"] == "simulated" for k in rows)
    print(f"wrote {dest / name}.html and .csv: {len(pulses)}/7 days, {len(rows)} KPIs ({sim} simulated)")


if __name__ == "__main__":
    main()
