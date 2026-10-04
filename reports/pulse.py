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
from reports.theme import CSS, E, EMAIL_FONT, PAGE, accordion, expander, info, kv, print_notes, stamp

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["shopgoodwill", "amazon", "ebay", "other"]
# Goodwill's own row names (slide 31): the Other row is always shown, the total is "Total e-commerce".
LABELS = {"shopgoodwill": "ShopGoodwill", "amazon": "Amazon", "ebay": "eBay", "other": "Other e-commerce channels"}
TOTAL = "Total e-commerce"
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

DAY = Template("""<header>
  <h1>Nightly pulse: $day_long</h1>
  <p>Compared with $prior_long · generated $generated$mock</p>
</header>
<p class="summary$summary_class">$summary</p>
<div class="kpis">
  <div class="kpi"><div class="label has-tip">Total e-commerce$tip_revenue</div><div class="value">$ent_revenue</div><div class="sub">$ent_delta</div></div>
  <div class="kpi"><div class="label has-tip">Orders$tip_orders</div><div class="value">$ent_orders</div></div>
  <div class="kpi"><div class="label has-tip">Customers$tip_customers</div><div class="value">$ent_customers</div><div class="sub">$ent_customers_delta</div></div>
  <div class="kpi"><div class="label has-tip">Marketplace fees$tip_fees</div><div class="value">$ent_fees</div></div>
</div>
$banner
<h2 class="sec">By marketplace<span class="aside noprint">Select a row for customers, refunds and fees</span></h2>
<div class="card">
<table>
  <thead><tr><th>Marketplace</th><th>Revenue</th><th>vs prior day</th><th>Orders</th><th class="status">Status</th></tr></thead>
  <tbody>
$rows
  </tbody>
</table>
</div>
$quality
$definitions
$notes
<p class="nav"><a href="index.html">All days</a> · <a href="$email_name">Email version</a></p>""")

INDEX = Template("""<header>
  <h1>Nightly pulse</h1>
  <p>$count report(s)</p>
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
    """The revenue change, and the note on it (shown in the row's details, not in the cell)."""
    if not d or d.get("revenue_cents") is None:
        reason = (d or {}).get("reason")
        return '<span class="muted">n/a</span>', REASONS.get(reason, reason) or "no comparison"
    cents, pct = d["revenue_cents"], d.get("revenue_pct")
    cls, arrow = ("up", "▲") if cents > 0 else ("down", "▼") if cents < 0 else ("", "")
    pct_txt = f" ({pct:+.1f}%)" if pct is not None else ""
    sign = "+" if cents > 0 else ""
    return (f'<span class="chg {cls}">{arrow} {sign}{money(cents)}{pct_txt}</span>',
            note or REASONS.get(d.get("reason"), d.get("reason")) or "")


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


def detail_row(detail_id, m, note):
    """A row's details: customers (and how they are counted), refunds, fees, the comparison note."""
    basis = " (counted by order)" if m.get("customer_basis") == "order" else ""
    pairs = kv([("Customers", f'{m["customers"]:,}{basis}'), ("Refunds", money(m["refunds_cents"])),
                ("Fees", money(m["fees_cents"])), ("Comparison", escape(note))])
    return f'    <tr class="xdetail" id="{detail_id}" hidden><td colspan="5">{pairs}</td></tr>'


def row_html(key, m):
    name = escape(label(key, m))
    status = m.get("status", "missing")
    pill = f'<td class="status"><span class="pill {status}">{PILL.get(status, escape(status))}</span></td>'
    if status == "not_configured":  # no source feeds it yet: a dash in each cell, as on slide 31
        dash = f'<td class="dash" title="{NO_DATA[status]}">–</td>'
        return f'    <tr><td><span class="xpad"></span>{name}</td>{dash * 3}{pill}</tr>'
    if status != "ok":
        return (f'    <tr><td><span class="xpad"></span>{name}</td><td class="nodata" colspan="3">'
                f'{NO_DATA.get(status, "No data")}</td>{pill}</tr>')
    delta, note = delta_html(m.get("delta"))
    return (f'    <tr class="xrow"><td>{expander("mk-" + key)}{name}</td><td>{money(m["revenue_cents"])}</td>'
            f'<td>{delta}</td><td>{m["orders"]:,}</td>{pill}</tr>\n' + detail_row("mk-" + key, m, note))


def render_day(p):
    markets, ent = p["marketplaces"], p["enterprise"]
    rows = [row_html(k, markets.get(k, {"status": "missing"})) for k in ORDER]
    excluded = [label(k, markets.get(k)) for k in excluded_keys(ent)]
    ed = ent.get("delta") or {}
    same = "same marketplaces on both days" if excluded and ed.get("revenue_cents") is not None else None
    ent_delta, ent_note = delta_html(ed, same)
    rows.append(
        f'    <tr class="total xrow"><td>{expander("mk-total")}{TOTAL}</td><td>{money(ent["revenue_cents"])}</td>'
        f'<td>{ent_delta}</td><td>{ent["orders"]:,}</td>'
        f'<td class="status">{"Partial" if excluded else "Complete"}</td></tr>\n' + detail_row("mk-total", ent, ent_note))

    banner = ""
    if excluded:
        names = " and ".join(escape(n) for n in excluded)
        banner = (f'<div class="banner"><strong>{names}: no data for this day.</strong> Enterprise totals '
                  f'exclude {names} and are not a full day.</div>')

    dq = p.get("data_quality") or {}
    if dq.get("warnings_total"):
        parts = ", ".join(f"{escape(k.replace('_', ' '))} rows: {n}" for k, n in sorted(dq.get("by_kind", {}).items()))
        quality = f"{dq['warnings_total']} issue(s) handled automatically: {parts}. Duplicates were counted once."
        quality_meta = f"{dq['warnings_total']} issue(s) handled automatically"
    else:
        quality, quality_meta = "No issues found in tonight's files.", "no issues"
    if dq.get("rows_rejected"):
        quality += f" {dq['rows_rejected']} row(s) could not be read and were left out."
        quality_meta += f", {dq['rows_rejected']} row(s) left out"

    definitions = dict(p.get("definitions") or {})
    definitions.setdefault("timezone", p.get("timezone", "America/New_York"))
    defs = "".join(f"<div><dt>{escape(k.replace('_', ' ').capitalize())}</dt><dd>{escape(v)}</dd></div>"
                   for k, v in definitions.items())
    one_line = " ".join(f"{escape(k.replace('_', ' ').capitalize())}: {escape(v)}" for k, v in definitions.items())
    get = definitions.get
    body = DAY.substitute(
        summary=escape(summary_line(p)),
        email_name=f"{p['business_date']}.email.html",
        summary_class=" alert" if excluded else "",
        day_long=long_date(p["business_date"]),
        prior_long=long_date(prior_date(p)) if prior_date(p) else "no prior day",
        generated=escape(stamp(p.get("generated_at", ""))),
        mock=" · <strong>mock data</strong>" if p.get("mock") else "",
        tip_revenue=info("tip-revenue", "enterprise revenue", [("Definition", escape(get("revenue", ""))),
                                                               ("Comparison", escape(ent_note))]),
        tip_orders=info("tip-orders", "orders", [("Definition", "Sale orders of the day; refunds are not counted.")]),
        tip_customers=info("tip-customers", "customers", [("Definition", escape(get("customers", "")))]),
        tip_fees=info("tip-fees", "marketplace fees", [("Definition", escape(get("fees", "Not deducted from revenue.")))]),
        ent_revenue=money(ent["revenue_cents"]),
        ent_delta=ent_delta,
        ent_orders=f"{ent['orders']:,}",
        ent_customers_delta=count_delta(ed.get("customers")),
        ent_customers=f"{ent['customers']:,}",
        ent_fees=money(ent["fees_cents"]),
        banner=banner,
        rows="\n".join(rows),
        quality=accordion("Data quality", f"<p>{quality}</p>", quality_meta),
        definitions=accordion("Definitions", f"<dl>{defs}</dl>", ", ".join(k.replace("_", " ") for k in definitions)),
        notes=print_notes([f"<b>Data quality:</b> {quality}", f"<b>Definitions:</b> {one_line}"]),
    )
    return PAGE.substitute(title=f"Nightly pulse {p['business_date']}", css=CSS, body=body, section=("Nightly pulse", "index.html"))


def email_delta(d):
    if not d or d.get("revenue_cents") is None:
        return f'<span style="color:{E["muted"]};">n/a</span>'
    cents, pct = d["revenue_cents"], d.get("revenue_pct")
    pct_txt = f" ({pct:+.1f}%)" if pct is not None else ""
    if cents > 0:
        return f'<b style="color:{E["up"]};">&#9650; +{money(cents)}{pct_txt}</b>'
    if cents < 0:
        return f'<b style="color:{E["down"]};">&#9660; {money(cents)}{pct_txt}</b>'
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
        if m["status"] == "not_configured":
            dash = f'<td {td} title="{NO_DATA["not_configured"]}">&ndash;</td>'
            rows.append(f'<tr><td {td_l}>{name}</td>' + dash * 5 + '</tr>')
            continue
        if m["status"] != "ok":
            color = E["down"]
            rows.append(f'<tr><td {td_l}>{name}</td><td {td_l} colspan="5">'
                        f'<b style="color:{color};">{NO_DATA.get(m["status"], "No data")}</b></td></tr>')
            continue
        rows.append(f'<tr><td {td_l}>{name}</td><td {td}>{money(m["revenue_cents"])}</td>'
                    f'<td {td}>{email_delta(m.get("delta"))}</td><td {td}>{m["orders"]:,}</td>'
                    f'<td {td}>{money(m["refunds_cents"])}</td><td {td}>{money(m["fees_cents"])}</td></tr>')
    tot = td.replace("border-bottom:1px solid", "font-weight:bold;border-top:2px solid").replace(
        f'{E["line"]};text', f'{E["primary"]};text')
    rows.append(f'<tr><td {tot.replace("text-align:right", "text-align:left")}>{TOTAL}</td>'
                f'<td {tot}>{money(ent["revenue_cents"])}</td><td {tot}>{email_delta(ent.get("delta"))}</td>'
                f'<td {tot}>{ent["orders"]:,}</td><td {tot}>{money(ent["refunds_cents"])}</td>'
                f'<td {tot}>{money(ent["fees_cents"])}</td></tr>')

    excluded = [label(k, markets.get(k)) for k in excluded_keys(ent)]
    alert = ""
    if excluded:
        names = " and ".join(escape(n) for n in excluded)
        alert = (f'<tr><td style="{EMAIL_FONT}font-size:14px;color:{E["ink"]};background:{E["tint"]};'
                 f'border-left:3px solid {E["down"]};padding:10px 14px;"><b>{names}: no data for this day.</b> '
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
  <div style="font-size:11px;font-weight:bold;letter-spacing:1px;">GOODWILL MICHIANA &middot; E-COMMERCE REPORTING</div>
  <div style="font-size:20px;font-weight:bold;padding-top:2px;">Nightly pulse: {long_date(p['business_date'])}</div>
  <div style="font-size:12px;">Compared with the prior day{mock}</div></td></tr>
<tr><td style="height:12px;line-height:12px;">&nbsp;</td></tr>
<tr><td style="{EMAIL_FONT}font-size:15px;font-weight:bold;color:{E['ink']};background:{E['tint']};border-left:3px solid {E['down'] if excluded else E['primary']};padding:12px 14px;">{escape(summary_line(p))}</td></tr>
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
    return PAGE.substitute(title="Nightly pulse", css=CSS, body=body, section=("Nightly pulse", "index.html"))


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
