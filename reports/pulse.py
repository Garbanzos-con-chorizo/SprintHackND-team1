"""Render the nightly pulse JSON as an HTML page with a one-line summary (tasks P-O2, P-O3).

Reads out/pulse/<date>.json (shape: docs/pitch/gemini/pulse_proposal.md) and writes
reports/pulse/<date>.html, <date>.csv (same layout as the monthly CSV,
see reports/schema.py), <date>.email.html (inline styles for Outlook) and index.html.
Standard library only.

    python -m reports.pulse --date 2026-10-02 [--src out/pulse] [--dest reports/pulse]
"""
import argparse
import json
import re
from datetime import date
from html import escape
from pathlib import Path
from string import Template

from reports.schema import day_record, write_csv

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["shopgoodwill", "amazon", "ebay", "other"]
LABELS = {"shopgoodwill": "ShopGoodwill", "amazon": "Amazon", "ebay": "eBay", "other": "Other"}
# Statuses and delta reasons from docs/contracts/pulse.md (schema_version 1).
NO_DATA = {
    "missing": "No data: file not received",
    "stale": "No data: file received, but no orders for this day",
    "unknown": "No data: file status unknown",
    "not_configured": "Not tracked yet",
}
PILL = {"ok": "OK", "missing": "Missing", "stale": "Stale", "unknown": "Unknown", "not_configured": "Not tracked"}
REASONS = {
    "current_not_ok": "no data today",
    "prior_unavailable": "no data for the prior day",
    "coverage_changed": "not comparable: different marketplaces reported each day",
    "prior_zero": "prior day revenue was $0",
}

# Goodwill palette: blue #0054A4 and black #231F20 on white. Greys are tints of the black.
# Green and red mark change and missing data only; green is too light for text on white
# (about 2:1), so it is a badge background under black text; red passes as text (about 5.6:1).
CSS = """
:root { --primary:#0054A4; --ink:#231F20; --bg:#fff; --card:#fff; --up:#9DBB68; --down:#CC1F40;
  --muted:#5c5859; --line:#d3d2d2; --nodata:#f4f4f4; --radius:2px; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif; }
main { max-width:980px; margin:0 auto; padding:24px 16px 48px; }
header { background:var(--primary); color:#fff; border-radius:var(--radius); padding:18px 20px; }
header h1 { margin:0; font-size:22px; }
header p { margin:4px 0 0; font-size:13px; opacity:.9; }
.summary { background:var(--card); border:1px solid var(--line); border-left:5px solid var(--primary);
  border-radius:var(--radius); padding:12px 16px; margin:16px 0 0; font-size:17px; font-weight:600; }
.summary.alert { border-left-color:var(--down); }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:16px 0; }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px; }
.kpi .label { color:var(--primary); font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.04em; }
.kpi .value { font-size:24px; font-weight:700; margin-top:2px; font-variant-numeric:tabular-nums; }
.kpi .sub { font-size:13px; margin-top:4px; }
.banner { background:var(--card); border:1px solid var(--line); border-left:5px solid var(--down); border-radius:var(--radius);
  padding:10px 14px; margin:0 0 16px; font-size:14px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:var(--radius); overflow-x:auto; }
table { width:100%; border-collapse:collapse; min-width:720px; }
th, td { padding:10px 12px; text-align:right; border-bottom:1px solid var(--line);
  font-variant-numeric:tabular-nums; white-space:nowrap; }
th { font-size:12px; color:var(--primary); font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
th:first-child, td:first-child, td.status, th.status { text-align:left; }
tr.total td { font-weight:700; border-top:2px solid var(--primary); border-bottom:none; }
td.nodata { text-align:left; background:var(--nodata); color:var(--down); font-weight:600; }
td.nodata.quiet { color:var(--muted); font-weight:400; font-style:italic; }
.pill { display:inline-block; font-size:11px; font-weight:700; padding:2px 8px; border-radius:var(--radius); }
.pill.ok { background:var(--up); color:var(--ink); }
.pill.missing, .pill.stale, .pill.unknown { background:var(--down); color:#fff; }
.pill.not_configured { border:1px solid var(--line); color:var(--muted); }
.chg { display:inline-block; padding:1px 8px; border-radius:var(--radius); font-weight:600; }
.chg.up { background:var(--up); color:var(--ink); }
.chg.down { background:var(--down); color:#fff; }
.muted { color:var(--muted); }
small.note { display:block; color:var(--muted); font-size:12px; font-weight:400; white-space:normal;
  max-width:220px; margin-left:auto; margin-top:2px; }
section.foot { margin-top:20px; font-size:13px; color:var(--muted); }
section.foot h2 { font-size:13px; color:var(--primary); margin:16px 0 6px; }
dl { display:grid; grid-template-columns:max-content 1fr; gap:4px 16px; margin:0; }
dt { font-weight:600; color:var(--ink); }
dd { margin:0; }
a { color:var(--primary); }
ul.days { list-style:none; padding:0; margin:16px 0; }
ul.days li { background:var(--card); border:1px solid var(--line); border-radius:var(--radius); margin-bottom:8px; }
ul.days a { display:block; padding:12px 16px; text-decoration:none; font-weight:600; }
.chg, .pill { border:1px solid transparent; }
@media print {
  @page { size:letter; margin:0.5in; }
  body { background:#fff; font-size:10.5pt; }
  main { max-width:none; padding:0; }
  /* Keep brand colors when the browser allows it... */
  header, .summary, .pill, .chg, .banner, td.nodata { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  /* ...and borders that still read correctly if backgrounds are dropped. */
  header { border:2px solid var(--primary); }
  .chg.up, .pill.ok { border-color:var(--ink); }
  .chg.down, .pill.missing, .pill.stale, .pill.unknown { border-color:var(--down); }
  .kpi, .card, .summary, .banner { border-color:var(--muted); }
  .card { overflow:visible; }
  table { min-width:0; font-size:9.5pt; }
  th, td { padding:6px 8px; }
  .kpis { grid-template-columns:repeat(4,1fr); }
  header, .summary, .kpis, .kpi, .banner, tr, dl { break-inside:avoid; }
  thead { display:table-header-group; }
  section.foot h2 { break-after:avoid; }
  .nav { display:none; }
}
"""

PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>$css</style>
</head>
<body>
<main>
$body
</main>
</body>
</html>
""")

DAY = Template("""<header>
  <h1>Nightly pulse: $day_long</h1>
  <p>Goodwill Michiana e-commerce · compared with $prior_long · times in $tz · generated $generated$mock</p>
</header>
<p class="summary$summary_class">$summary</p>
<div class="kpis">
  <div class="kpi"><div class="label">Enterprise revenue</div><div class="value">$ent_revenue</div><div class="sub">$ent_delta</div></div>
  <div class="kpi"><div class="label">Orders</div><div class="value">$ent_orders</div><div class="sub muted">sale orders; refunds not counted</div></div>
  <div class="kpi"><div class="label">Customers</div><div class="value">$ent_customers</div><div class="sub">$ent_customers_delta</div></div>
  <div class="kpi"><div class="label">Marketplace fees</div><div class="value">$ent_fees</div><div class="sub muted">not deducted from revenue</div></div>
</div>
$banner
<div class="card">
<table>
  <thead><tr>
    <th>Marketplace</th><th class="status">Status</th><th>Revenue</th><th>vs prior day</th>
    <th>Orders</th><th>Customers</th><th>Refunds</th><th>Fees</th>
  </tr></thead>
  <tbody>
$rows
  </tbody>
</table>
</div>
<section class="foot">
  <h2>Data quality</h2>
  <p>$quality</p>
  <h2>Definitions</h2>
  <dl>
$definitions
  </dl>
  <p class="nav"><a href="index.html">All days</a> · <a href="$email_name">Email version</a></p>
</section>""")

INDEX = Template("""<header>
  <h1>Nightly pulse</h1>
  <p>Goodwill Michiana e-commerce · $count report(s)</p>
</header>
<ul class="days">
$items
</ul>""")


def money(cents):
    return "-" if cents is None else f"{'-' if cents < 0 else ''}${abs(cents) / 100:,.2f}"


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def label(key, m=None):
    return (m or {}).get("label") or LABELS.get(key, key.title())


def excluded_keys(ent):
    return [x["marketplace"] if isinstance(x, dict) else x for x in ent.get("excluded") or []]


def prior_date(p):
    return p.get("prior_date") or (p["enterprise"].get("delta") or {}).get("prior_date")


def delta_html(d, note=None):
    if not d or d.get("revenue_cents") is None:
        reason = (d or {}).get("reason")
        reason = REASONS.get(reason, reason) or "no comparison"
        return f'<span class="muted">n/a</span><small class="note">{escape(reason)}</small>'
    cents, pct = d["revenue_cents"], d.get("revenue_pct")
    cls, arrow = ("up", "▲") if cents > 0 else ("down", "▼") if cents < 0 else ("", "")
    pct_txt = f" ({pct:+.1f}%)" if pct is not None else ""
    sign = "+" if cents > 0 else ""
    note = note or REASONS.get(d.get("reason"), d.get("reason"))
    note = f'<small class="note">{escape(note)}</small>' if note else ""
    return f'<span class="chg {cls}">{arrow} {sign}{money(cents)}{pct_txt}</span>{note}'


def count_delta(n):
    if n is None:
        return '<span class="muted">sum across marketplaces</span>'
    cls = "up" if n > 0 else "down" if n < 0 else ""
    return f'<span class="chg {cls}">{n:+d}</span> <span class="muted">vs prior day</span>'


def summary_line(p):
    """P-O3: one templated sentence, e.g. "Revenue up 4.2% vs Friday; ShopGoodwill strongest (61% of revenue)"."""
    markets, ent = p["marketplaces"], p["enterprise"]
    ed = ent.get("delta") or {}
    prior = f"{date.fromisoformat(prior_date(p)):%A}" if prior_date(p) else "the prior day"
    pct = ed.get("revenue_pct")
    if pct is None:
        parts = [f"Revenue {money(ent['revenue_cents'])}, not comparable with {prior}"]
    elif round(pct, 1) == 0:
        parts = [f"Revenue flat vs {prior}"]
    else:
        parts = [f"Revenue {'up' if pct > 0 else 'down'} {abs(pct):.1f}% vs {prior}"]
    if pct is not None and ent.get("excluded"):
        parts[0] += " on comparable marketplaces"
    ok = [k for k in ORDER if markets.get(k, {}).get("status") == "ok"]
    if len(ok) > 1 and ent["revenue_cents"]:
        k = max(ok, key=lambda k: markets[k]["revenue_cents"])
        top = markets[k]
        parts.append(f"{label(k, top)} strongest ({top['revenue_cents'] / ent['revenue_cents']:.0%} of revenue)")
    for k in ORDER:
        m = markets.get(k, {})
        if m.get("status") == "missing":
            parts.append(f"{label(k, m)} file missing")
        elif m.get("status") == "stale":
            parts.append(f"{label(k, m)} file has no orders for this day")
        elif m.get("status") == "unknown":
            parts.append(f"{label(k, m)} file status unknown")
    if ent.get("refunds_cents"):
        parts.append(f"{money(-ent['refunds_cents'])} refunded")
    dups = ((p.get("data_quality") or {}).get("by_kind") or {}).get("duplicate")
    if dups:
        parts.append(f"{dups} duplicate rows removed")
    return "; ".join(parts) + "."


def row_html(key, m):
    name = escape(label(key, m))
    status = m.get("status", "missing")
    pill = f'<span class="pill {status}">{PILL.get(status, escape(status))}</span>'
    if status != "ok":
        return (f'    <tr><td>{name}</td><td class="status">{pill}</td>'
                f'<td class="nodata{" quiet" if status == "not_configured" else ""}" colspan="6">'
                f'{NO_DATA.get(status, "No data")}</td></tr>')
    basis = '<small class="note">counted by order</small>' if m.get("customer_basis") == "order" else ""
    return (f'    <tr><td>{name}</td><td class="status">{pill}</td><td>{money(m["revenue_cents"])}</td>'
            f'<td>{delta_html(m.get("delta"))}</td><td>{m["orders"]:,}</td><td>{m["customers"]:,}{basis}</td>'
            f'<td>{money(m["refunds_cents"])}</td><td>{money(m["fees_cents"])}</td></tr>')


def render_day(p):
    markets, ent = p["marketplaces"], p["enterprise"]
    rows = [row_html(k, markets.get(k, {"status": "missing"})) for k in ORDER]
    excluded = [label(k, markets.get(k)) for k in excluded_keys(ent)]
    ed = ent.get("delta") or {}
    same = "same marketplaces on both days" if excluded and ed.get("revenue_cents") is not None else None
    rows.append(
        f'    <tr class="total"><td>Enterprise total</td><td class="status">'
        f'{"Partial" if excluded else "Complete"}</td><td>{money(ent["revenue_cents"])}</td>'
        f'<td>{delta_html(ed, same)}</td><td>{ent["orders"]:,}</td><td>{ent["customers"]:,}</td>'
        f'<td>{money(ent["refunds_cents"])}</td><td>{money(ent["fees_cents"])}</td></tr>')

    banner = ""
    if excluded:
        names = " and ".join(escape(n) for n in excluded)
        banner = (f'<div class="banner"><strong>{names}: no data for this day.</strong> Enterprise totals '
                  f'exclude {names} and are not a full day.</div>')

    dq = p.get("data_quality") or {}
    if dq.get("warnings_total"):
        parts = ", ".join(f"{escape(k.replace('_', ' '))} rows: {n}" for k, n in sorted(dq.get("by_kind", {}).items()))
        quality = f"{dq['warnings_total']} issue(s) handled automatically: {parts}. Duplicates were counted once."
    else:
        quality = "No issues found in tonight's files."
    if dq.get("rows_rejected"):
        quality += f" {dq['rows_rejected']} row(s) could not be read and were left out."

    defs = "\n".join(f"    <dt>{escape(k.replace('_', ' ').capitalize())}</dt><dd>{escape(v)}</dd>"
                     for k, v in (p.get("definitions") or {}).items())
    body = DAY.substitute(
        summary=escape(summary_line(p)),
        email_name=f"{p['business_date']}.email.html",
        summary_class=" alert" if excluded else "",
        day_long=long_date(p["business_date"]),
        prior_long=long_date(prior_date(p)) if prior_date(p) else "no prior day",
        tz=escape(p.get("timezone", "America/New_York")),
        generated=escape(p.get("generated_at", "")),
        mock=" · <strong>mock data</strong>" if p.get("mock") else "",
        ent_revenue=money(ent["revenue_cents"]),
        ent_delta=delta_html(ed, same),
        ent_orders=f"{ent['orders']:,}",
        ent_customers_delta=count_delta(ed.get("customers")),
        ent_customers=f"{ent['customers']:,}",
        ent_fees=money(ent["fees_cents"]),
        banner=banner,
        rows="\n".join(rows),
        quality=quality,
        definitions=defs,
    )
    return PAGE.substitute(title=f"Nightly pulse {p['business_date']}", css=CSS, body=body)


# Email copy: Outlook desktop renders with Word, which ignores <style> variables, grid and
# border-radius. So: nested tables, every style inline on the element, web-safe fonts, hex colors.
E = {"primary": "#0054A4", "ink": "#231F20", "bg": "#ffffff", "up": "#9DBB68", "down": "#CC1F40",
     "muted": "#5c5859", "line": "#d3d2d2"}
EMAIL_FONT = "font-family:Arial,Helvetica,sans-serif;"


def email_delta(d):
    if not d or d.get("revenue_cents") is None:
        return f'<span style="color:{E["muted"]};">n/a</span>'
    cents, pct = d["revenue_cents"], d.get("revenue_pct")
    pct_txt = f" ({pct:+.1f}%)" if pct is not None else ""
    if cents > 0:
        return (f'<span style="background:{E["up"]};color:{E["ink"]};padding:1px 6px;">'
                f'&#9650; +{money(cents)}{pct_txt}</span>')
    if cents < 0:
        return (f'<span style="background:{E["down"]};color:#ffffff;padding:1px 6px;">'
                f'&#9660; {money(cents)}{pct_txt}</span>')
    return f"{money(cents)}{pct_txt}"


def render_email(p):
    markets, ent = p["marketplaces"], p["enterprise"]
    td = f'style="{EMAIL_FONT}font-size:14px;color:{E["ink"]};padding:8px 10px;border-bottom:1px solid {E["line"]};text-align:right;"'
    td_l = td.replace("text-align:right", "text-align:left")
    th = f'style="{EMAIL_FONT}font-size:11px;color:{E["primary"]};padding:8px 10px;text-align:right;border-bottom:2px solid {E["primary"]};"'
    th_l = th.replace("text-align:right", "text-align:left")

    rows = []
    for k in ORDER:
        m = markets.get(k, {"status": "missing"})
        name = escape(label(k, m))
        if m["status"] != "ok":
            color = E["muted"] if m["status"] == "not_configured" else E["down"]
            rows.append(f'<tr><td {td_l}>{name}</td><td {td_l} colspan="5">'
                        f'<b style="color:{color};">{NO_DATA.get(m["status"], "No data")}</b></td></tr>')
            continue
        rows.append(f'<tr><td {td_l}>{name}</td><td {td}>{money(m["revenue_cents"])}</td>'
                    f'<td {td}>{email_delta(m.get("delta"))}</td><td {td}>{m["orders"]:,}</td>'
                    f'<td {td}>{money(m["refunds_cents"])}</td><td {td}>{money(m["fees_cents"])}</td></tr>')
    tot = td.replace("border-bottom:1px solid", "font-weight:bold;border-top:2px solid").replace(
        f'{E["line"]};text', f'{E["primary"]};text')
    rows.append(f'<tr><td {tot.replace("text-align:right", "text-align:left")}>Enterprise total</td>'
                f'<td {tot}>{money(ent["revenue_cents"])}</td><td {tot}>{email_delta(ent.get("delta"))}</td>'
                f'<td {tot}>{ent["orders"]:,}</td><td {tot}>{money(ent["refunds_cents"])}</td>'
                f'<td {tot}>{money(ent["fees_cents"])}</td></tr>')

    excluded = [label(k, markets.get(k)) for k in excluded_keys(ent)]
    alert = ""
    if excluded:
        names = " and ".join(escape(n) for n in excluded)
        alert = (f'<tr><td style="{EMAIL_FONT}font-size:14px;color:{E["ink"]};background:#fbe8ec;'
                 f'border-left:5px solid {E["down"]};padding:10px 14px;"><b>{names}: no data for this day.</b> '
                 f'Totals exclude {names}.</td></tr>'
                 f'<tr><td style="height:12px;line-height:12px;">&nbsp;</td></tr>')
    defs = "<br>".join(f"<b>{escape(k.replace('_', ' ').capitalize())}:</b> {escape(v)}"
                       for k, v in (p.get("definitions") or {}).items())
    mock = " &middot; mock data" if p.get("mock") else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nightly pulse {p['business_date']}</title></head>
<body style="margin:0;padding:0;background:{E['bg']};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{E['bg']};">
<tr><td align="center" style="padding:16px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:100%;">
<tr><td style="{EMAIL_FONT}background:{E['primary']};color:#ffffff;padding:16px 20px;">
  <div style="font-size:20px;font-weight:bold;">Nightly pulse: {long_date(p['business_date'])}</div>
  <div style="font-size:12px;">Goodwill Michiana e-commerce{mock}</div></td></tr>
<tr><td style="height:12px;line-height:12px;">&nbsp;</td></tr>
<tr><td style="{EMAIL_FONT}font-size:16px;font-weight:bold;color:{E['ink']};background:#ffffff;border-left:5px solid {E['down'] if excluded else E['primary']};padding:12px 14px;">{escape(summary_line(p))}</td></tr>
<tr><td style="height:12px;line-height:12px;">&nbsp;</td></tr>
{alert}<tr><td style="background:#ffffff;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><th {th_l}>MARKETPLACE</th><th {th}>REVENUE</th><th {th}>VS PRIOR DAY</th><th {th}>ORDERS</th><th {th}>REFUNDS</th><th {th}>FEES</th></tr>
{chr(10).join(rows)}
</table></td></tr>
<tr><td style="{EMAIL_FONT}font-size:11px;color:{E['muted']};padding:12px 2px;">{defs}</td></tr>
</table></td></tr></table>
</body></html>
"""


def render_index(dest):
    days = sorted((f.stem for f in dest.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem)),
                  reverse=True)
    items = "\n".join(
        f'  <li><a href="{d}.html">{long_date(d)}{" <span class=\"muted\">(latest)</span>" if i == 0 else ""}</a></li>'
        for i, d in enumerate(days))
    body = INDEX.substitute(count=len(days), items=items or '  <li class="muted">No reports yet.</li>')
    return PAGE.substitute(title="Nightly pulse", css=CSS, body=body)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="business date, YYYY-MM-DD")
    ap.add_argument("--src", default=str(ROOT / "out" / "pulse"), help="folder with <date>.json")
    ap.add_argument("--dest", default=str(ROOT / "reports" / "pulse"), help="folder for the HTML")
    args = ap.parse_args(argv)
    src = Path(args.src) / f"{args.date.isoformat()}.json"
    if not src.exists():
        raise SystemExit(f"no pulse file at {src}; run the pulse command (or reports.mock_pulse) first")
    pulse = json.loads(src.read_text(encoding="utf-8"))
    for path in render(pulse, Path(args.dest)):
        print(f"wrote {path}")
    print(summary_line(pulse))


def render(pulse, dest):
    """Write the page, CSV, email copy and index for one pulse; return the paths written."""
    dest.mkdir(parents=True, exist_ok=True)
    day = pulse["business_date"]
    paths = [dest / f"{day}.html", dest / f"{day}.csv", dest / f"{day}.email.html", dest / "index.html"]
    paths[0].write_text(render_day(pulse), encoding="utf-8")
    write_csv(paths[1], [day_record(pulse)])
    paths[2].write_text(render_email(pulse), encoding="utf-8")
    paths[3].write_text(render_index(dest), encoding="utf-8")
    return paths


if __name__ == "__main__":
    main()
