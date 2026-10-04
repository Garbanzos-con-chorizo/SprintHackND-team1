"""Month-end close page: what `reports.bc_export` produced, for the people who post it.

Reads out/close/<YYYY-MM>/ (control totals, exceptions, General Journal, AR invoice; and, when they are
there, the close payload, the engine's files and the run history) and writes reports/close/<YYYY-MM>.html:
what is simulated, the reconciliation status per source, the exceptions to work with who owns each, the
Cash Monkey cross-check, Goodwill's nine month-end sources with what this run has for each, and download
links to the four Business Central CSV files (copied next to the page).

The nine sources and their wording come from reports/config/close_sources.csv (deck slide 38). `Detect`
says how the page knows a source reached this run; `When_Absent` is what it says otherwise: change it
from "not modeled" to "not in this inbox" when a reader for that source lands in the engine.

    python -m reports.close_report --month 2026-09
"""
import argparse
import csv
import json
import re
import shutil
from collections import defaultdict
from datetime import date
from html import escape
from pathlib import Path

from reports.theme import CSS, DOWNLOAD_ICON, PAGE, accordion, expander, facts, info, kv, print_notes

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "close"
DEST = ROOT / "reports" / "close"
SOURCES = ROOT / "reports" / "config" / "close_sources.csv"
FILES = [("general_journal", "General Journal lines"), ("ar_invoice", "AR invoice lines"),
         ("control_totals", "Control totals"), ("exceptions", "Exceptions")]
STATUS_CLASS = {"RECONCILED": "ok", "OPEN": "stale", "INCOMPLETE": "missing", "UNEXPLAINED": "missing",
                "MISMATCH": "missing"}
LABELS = {"cashmonkey": "Cash Monkey"}

def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_if_there(path):
    return read(path) if path.exists() else []


def cents(text):
    return round(float(text) * 100) if text not in ("", None) else 0


def money(c):
    return f"{'-' if c < 0 else ''}${abs(c) / 100:,.2f}"


def headline(control, journal_docs, exceptions):
    bad = [r for r in control if r["Status"] in ("INCOMPLETE", "UNEXPLAINED", "MISMATCH")]
    parts = [f"{journal_docs} journal documents, all balanced to 0.00"]
    parts.append(", ".join(f"{r['Source']} {r['Status']}" + (f" ({money(cents(r['Unexplained']))})" if r["Status"] == "UNEXPLAINED" else "")
                           for r in control))
    parts.append(f"{len(exceptions)} exceptions")
    return "; ".join(parts) + ".", bool(bad)


def source_states(folder, payload, path=SOURCES):
    """Goodwill's nine month-end sources and what this run has for each: (config row, present, note)."""
    engine = folder / "engine"
    bank, payouts = read_if_there(engine / "bank.csv"), read_if_there(engine / "payouts.csv")
    missing = {e["source"] for e in payload.get("exceptions", []) if e["kind"] == "missing_report"}
    states = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            how, _, what = row["Detect"].partition(":")
            present = {
                "marketplace": lambda: what in payload.get("sources", {}),
                "cross_check": lambda: any(c["against"] == what for c in payload.get("cross_checks", [])),
                "engine_file": lambda: bool(read_if_there(engine / what)),
                "bank_account": lambda: any(r.get("account") == what for r in bank),
                "payout_period": lambda: any(r["marketplace"] == what and r.get("period_from") for r in payouts),
            }[how]()
            note = "a report is missing for some days: see the exceptions" if how == "marketplace" and what in missing else ""
            states.append((row, present, note))
    return states


CLOSE_CSS = """
.notice { display:flex; flex-wrap:wrap; align-items:center; gap:6px 8px; margin-top:var(--sp-3); font-size:13px; color:var(--muted); }
.notice .tip { min-width:300px; right:auto; }
.pill.stale { background:var(--neutral-bg); color:var(--muted); }

/* Action required: one row per item, opening to its owner and what to do */
.action { margin-top:var(--sp-3); padding:var(--sp-1) 0; }
.action-hd { display:flex; flex-wrap:wrap; align-items:center; gap:var(--sp-1) 10px; padding:10px var(--sp-5); font-size:13px; color:var(--muted); }
details.act { border-top:1px solid var(--hair); }
details.act > summary { display:grid; grid-template-columns:minmax(80px,140px) minmax(0,1fr) auto 14px; align-items:center;
  gap:var(--sp-3); padding:11px var(--sp-5); list-style:none; cursor:pointer; transition:background-color var(--t-hover) var(--ease-out); }
details.act > summary::-webkit-details-marker { display:none; }
details.act > summary::after { content:"\\203A"; justify-self:end; font-size:18px; line-height:1; color:var(--faint);
  transition:transform var(--t-reveal) var(--ease-out); }
details.act[open] > summary::after { transform:rotate(90deg); }
details.act > summary:hover { background:var(--hover); }
.act .who { font-weight:var(--fw-semi); }
.act .what { color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.act .amt { font-weight:var(--fw-semi); color:var(--ink); }
.act p { padding:0 var(--sp-5) var(--sp-3); font-size:13px; color:var(--muted); }

/* Business Central files: cards that lift, a pill that fills on hover */
.files { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:var(--sp-3); }
.file { display:flex; flex-direction:column; gap:2px; padding:var(--sp-4) var(--sp-5); background:var(--card);
  border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); color:var(--ink); }
.file:hover { text-decoration:none; }
.file b { font-weight:var(--fw-semi); }
.file b span { margin-left:var(--sp-2); font-weight:var(--fw-regular); color:var(--muted); }
.file code { font-size:var(--fs-small); color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.file .get { align-self:flex-start; display:inline-flex; align-items:center; gap:6px; margin-top:10px; padding:4px 12px;
  border-radius:980px; background:var(--neutral-bg); color:var(--accent); font-size:var(--fs-small); font-weight:var(--fw-semi);
  transition:background-color var(--t-hover) var(--ease-out), color var(--t-hover) var(--ease-out); }
.file:hover .get { background:var(--accent); color:#fff; }

/* Ledger, exceptions, sources */
.dot { display:inline-block; width:7px; height:7px; margin-right:8px; border-radius:50%; background:var(--bad); vertical-align:1px;
  animation:breathe 2.4s ease-in-out infinite; }
table.ledger td.zero { color:var(--faint); }
table.ledger td.bad { color:var(--bad); font-weight:var(--fw-semi); }
td.detail, td.text, th.text { min-width:180px; text-align:left; white-space:normal; color:var(--muted); }
td.owner { text-align:left; }
.state { font-weight:var(--fw-semi); color:var(--ink); }
.state.absent { font-weight:var(--fw-regular); color:var(--faint); }
.acc-note { margin-top:var(--sp-3); font-size:12px; color:var(--faint); }
@media (max-width:640px) {
  details.act > summary { grid-template-columns:minmax(0,1fr) auto 14px; }
  .act .what { grid-column:1 / -1; grid-row:2; }
}
@media print {
  @page { size:letter portrait; margin:0.4in; }
  body { font-size:8pt; }
  .notice { margin-top:4pt; font-size:7pt; }
  .action { margin-top:4pt; padding:1pt 0; box-shadow:none; border-color:#d2d2d7; border-radius:8px; }
  .action-hd { padding:2pt 8pt; font-size:7.5pt; }
  details.act > summary { padding:2pt 8pt; grid-template-columns:70pt minmax(0,1fr) auto; gap:6pt; }
  details.act > summary::after { display:none; }
}
"""
ACTION_STATUS = {"UNEXPLAINED": ("Unexplained balance", "Unexplained"),
                 "INCOMPLETE": ("Report missing", "Open Balance"),
                 "MISMATCH": ("Revenue mismatch", "Difference")}
LEGEND = ("<b>OPEN:</b> money still in transit or not paid out yet, fully explained by the exceptions marked \"open balance\". "
          "<b>INCOMPLETE:</b> every cent is accounted for, but a payout paid for days no report covers; download that report "
          "and run the close again. <b>UNEXPLAINED:</b> money nobody has accounted for; resolve before posting. "
          "<b>RECONCILED:</b> open balance 0.00. Positive amounts are debits. The owners are role names we chose, not Goodwill's.")
SYNTHETIC = ("<b>Synthetic sample data.</b> No real Goodwill file has been read. Account, customer and document numbers are "
             "placeholders; only department 180 comes from Goodwill's own slide. <b>Posting status: Not posted.</b> These are "
             "import files in Business Central's column order; nothing here has been sent to a Business Central.")
EFFECTS = [("open_balance", "Open balance", "in transit or not paid out yet; explains the open balance"),
           ("not_posted", "Not posted", "held out of the Business Central files"),
           ("info", "For review", "changes no number")]


def amount_cell(c, cls=""):
    cls = " ".join(x for x in (cls, "zero" if c == 0 else "") if x)
    return f'<td class="{cls}">{money(c)}</td>' if cls else f"<td>{money(c)}</td>"


def ledger(control):
    """Control totals: source, revenue posted, open balance, unexplained and status; each row opens to the rest."""
    body, totals = [], dict.fromkeys(("Revenue Posted", "Open Balance", "Unexplained"), 0)
    for i, r in enumerate(control):
        for c in totals:
            totals[c] += cents(r[c])
        dot = '<span class="dot"></span>' if STATUS_CLASS.get(r["Status"]) == "missing" else ""
        detail_id = f"src-{i}"
        breakdown = kv([("Path", escape(r["Path"])), ("Revenue in", money(cents(r["Revenue In"]))),
                        ("Revenue posted", money(cents(r["Revenue Posted"]))),
                        ("Difference", money(cents(r["Difference"])) if cents(r.get("Difference")) else ""),
                        ("Receivable posted", money(cents(r["Receivable Posted"]))),
                        ("Deposits", money(cents(r["Deposits"]))), ("Explained", money(cents(r["Explained"])))])
        body.append(f'<tr class="xrow"><td>{expander(detail_id)}{dot}<b>{escape(r["Source"])}</b></td>'
                    f'{amount_cell(cents(r["Revenue Posted"]))}{amount_cell(cents(r["Open Balance"]))}'
                    f'{amount_cell(cents(r["Unexplained"]), "bad" if cents(r["Unexplained"]) else "")}'
                    f'<td class="status"><span class="pill {STATUS_CLASS.get(r["Status"], "")}">{escape(r["Status"])}</span></td></tr>'
                    f'<tr class="xdetail" id="{detail_id}" hidden><td colspan="5">{breakdown}</td></tr>')
    body.append(f'<tr class="total"><td>Total</td>{"".join(amount_cell(v) for v in totals.values())}<td></td></tr>')
    return ('<div class="card"><table class="ledger"><thead><tr><th>Source</th><th>Revenue posted</th><th>Open balance</th>'
            '<th>Unexplained</th><th class="status">Status</th></tr></thead><tbody>\n' + "\n".join(body) + "\n</tbody></table></div>")


def kind(e):
    return e["Kind"].replace("_", " ").capitalize()


def exception_groups(exceptions):
    """[(name, what, total or "", rows)] per effect, in working order; total only where amounts add up."""
    known = [e for e, _, _ in EFFECTS]
    groups = []
    for effect, name, what in EFFECTS + [(None, "Other", "")]:
        rows = [e for e in exceptions if (e["Effect"] == effect if effect else e["Effect"] not in known)]
        if rows:
            rows.sort(key=lambda e: (e["Source"] == "", e["Source"], e["Kind"]))
            total = money(sum(cents(e["Amount"]) for e in rows)) if effect in ("open_balance", "not_posted") else ""
            groups.append((name, what, total, rows))
    return groups


def exceptions_html(groups):
    """One accordion per effect, closed: the count and sum show, the rows (with owner and what to do) open on demand."""
    parts = []
    for name, what, total, rows in groups:
        lines = "".join(f'<tr><td>{escape(kind(e))}</td><td class="owner">{escape(e["Source"]) or "-"}</td>'
                        f'<td>{money(cents(e["Amount"])) if e["Amount"] else ""}</td>'
                        f'<td class="detail">{escape(e["Detail"])}</td><td class="owner">{escape(e.get("Owner") or "")}</td>'
                        f'<td class="text">{escape(e.get("Action") or "")}</td></tr>' for e in rows)
        table = ('<div class="card"><table class="exc"><thead><tr><th>Kind</th><th class="l">Source</th><th>Amount</th>'
                 '<th class="text">Detail</th><th class="text">Owner</th><th class="text">What to do</th></tr></thead>'
                 f'<tbody>{lines}</tbody></table></div>')
        parts.append(accordion(name, table, escape(" · ".join(x for x in (str(len(rows)), total, what) if x))))
    return "".join(parts)


def action_items(control, exceptions, docs, unbalanced):
    """What to resolve before importing: (who, short label, amount, full text with owner and what to do)."""
    items = [("Journal", "Unbalanced document", money(docs[d]), f"Document {d} does not balance; import nothing until it does.")
             for d in unbalanced]
    for r in control:
        if r["Status"] in ACTION_STATUS:
            label, column = ACTION_STATUS[r["Status"]]
            related = [e for e in exceptions if e["Source"] == r["Source"] and e["Kind"] in ("residual_unexplained", "missing_report")]
            text = " ".join(f'{e["Detail"]}' + (f' Owner: {e["Owner"]}. {e["Action"]}' if e.get("Action") else "") for e in related)
            items.append((r["Source"], label, money(cents(r.get(column) or 0)), text or LEGEND))
    for e in exceptions:
        if e["Effect"] == "not_posted":
            extra = f' Owner: {e["Owner"]}. {e["Action"]}' if e.get("Action") else ""
            items.append((e["Source"] or "Unassigned", kind(e), money(cents(e["Amount"])) if e["Amount"] else "", e["Detail"] + extra))
    return items


def action_html(items, exceptions):
    if not items:
        review = sum(e["Effect"] == "info" for e in exceptions)
        more = f"; {review} exception(s) for review below" if review else ""
        return ('<section class="panel action"><div class="action-hd"><span class="pill ok">No action required before posting</span>'
                f'<span>Every source is reconciled or fully explained{more}.</span></div></section>')
    rows = "".join(f'<details class="act"><summary><span class="who">{escape(who)}</span><span class="what">{escape(what)}</span>'
                   f'<span class="amt">{escape(amount)}</span></summary><p>{escape(text)}</p></details>'
                   for who, what, amount, text in items)
    return (f'<section class="panel action"><div class="action-hd"><span class="pill bad">Action required</span>'
            f'<span>{len(items)} item(s) to resolve before posting</span></div>{rows}</section>')


def render(month, folder):
    t = {k: read(folder / f"{k}_{month}.csv") for k, _ in FILES}
    payload_file = folder / f"close_payload_{month}.json"
    payload = json.loads(payload_file.read_text(encoding="utf-8")) if payload_file.exists() else {}
    docs = defaultdict(int)
    for line in t["general_journal"]:
        docs[line["Document No."]] += cents(line["Amount"])
    unbalanced = [d for d, c in docs.items() if c]
    text, alert = headline(t["control_totals"], len(docs), t["exceptions"])
    if unbalanced:
        text, alert = f"Journal does not balance: {', '.join(unbalanced)}.", True
    invoices = {line["Document No."] for line in t["ar_invoice"]}
    statuses = [r["Status"] for r in t["control_totals"]]
    held = sum(e["Effect"] == "not_posted" for e in t["exceptions"])
    summary = facts([
        ("Journal", f'{len(t["general_journal"])} lines · {len(docs)} documents', ""),
        ("Balance", f"{len(unbalanced)} unbalanced" if unbalanced else "Every document 0.00", "bad" if unbalanced else "good"),
        ("AR invoice", f'{len(invoices)} invoice(s) · {len(t["ar_invoice"])} lines', ""),
        ("Sources", " · ".join(f"{statuses.count(s)} {s.lower()}" for s in dict.fromkeys(statuses)),
         "bad" if any(STATUS_CLASS.get(s) == "missing" for s in statuses) else ""),
        ("Exceptions", f'{len(t["exceptions"])} · {held} held out', "bad" if held else ""),
    ])
    notice = ('<p class="notice has-tip"><span class="pill warn">Synthetic sample data</span><span class="pill">Not posted</span>'
              + info("tip-synthetic", "the sample data and posting status", [("About this close", SYNTHETIC)]) + "</p>")
    items = action_items(t["control_totals"], t["exceptions"], docs, unbalanced)
    groups = exception_groups(t["exceptions"])
    files = "".join(f'<a class="file" href="{month}/{k}_{month}.csv" download><b>{label}<span>{len(t[k])} rows</span></b>'
                    f'<code>{k}_{month}.csv</code><span class="get">{DOWNLOAD_ICON}Download CSV</span></a>' for k, label in FILES)

    extras, notes = [], []
    if payload.get("cross_checks"):
        other = LABELS.get(payload["cross_checks"][0]["against"], payload["cross_checks"][0]["against"])
        rows = "\n".join(
            f'<tr><td>{escape(c["source"])}</td><td>{money(c["report_sales_cents"])}</td>'
            f'<td>{money(c["against_sales_cents"])}</td><td>{money(c["difference_cents"])}</td>'
            f'<td>{c["orders_only_in_against"]}</td><td>{c["orders_only_in_report"]}</td>'
            f'<td>{c["orders_with_another_amount"]}</td></tr>' for c in payload["cross_checks"])
        table = (f'<div class="card"><table><thead><tr><th>Marketplace</th><th>Sales in its reports</th>'
                 f'<th>Sales in {escape(other)}</th><th>Difference</th><th>Orders only in {escape(other)}</th>'
                 f'<th>Orders only in the reports</th><th>Orders with another amount</th></tr></thead><tbody>\n{rows}\n</tbody></table></div>'
                 f'<p class="acc-note">Compared order by order, sales only. The journal posts each marketplace from its own '
                 f'reports; the {escape(other)} file is never added to them.</p>')
        extras.append(accordion(f"Cross-check: {other} against each marketplace's own reports", table,
                                f"{len(payload['cross_checks'])} marketplaces"))
        notes.append(f"<b>Cross-check, {escape(other)}:</b> " + "; ".join(
            f'{escape(c["source"])} difference {money(c["difference_cents"])}' for c in payload["cross_checks"]))
    if payload:
        states = source_states(folder, payload)
        rows = "\n".join(
            f'<tr class="src"><td>{escape(r["Source"])}</td><td class="text">{escape(r["Month_End_Input"])}</td>'
            f'<td class="text">{escape(r["Acquisition_Rule"])}</td>'
            f'<td class="text"><span class="state{"" if present else " absent"}">'
            f'{escape(r["Origin"] if present else r["When_Absent"])}</span>{"; " + escape(note) if note else ""}</td>'
            f'<td class="detail">{escape(r["What_We_Read"]) if present else ""}</td></tr>' for r, present, note in states)
        table = ('<div class="card"><table><thead><tr><th>Source</th><th class="text">Month-end input</th>'
                 '<th class="text">Acquisition / rule</th><th class="text">In this run</th><th class="text">What we read</th>'
                 f'</tr></thead><tbody>\n{rows}\n</tbody></table></div>'
                 '<p class="acc-note">The first three columns are Goodwill\'s own (their slide 38). "Sample file" is a synthetic '
                 'file we generated; "simulated API" is a file written by a stand-in for an API we have not seen; "not modeled" '
                 'means nothing reads that source yet.</p>')
        have = sum(present for _, present, _ in states)
        extras.append(accordion("Goodwill's nine month-end sources, and what this run has for each", table,
                                f"{have} of {len(states)} in this run"))
        notes.append(f"<b>Month-end sources:</b> {have} of {len(states)} in this run: " + ", ".join(
            escape(r["Source"]) for r, present, _ in states if present) + ".")
    runs = read_if_there(folder / "runs.csv")
    if runs:
        head = "".join(f'<th class="text">{escape(c.replace("_", " "))}</th>' for c in runs[0])
        rows = "\n".join("<tr>" + "".join(f'<td class="text">{escape(v or "")}</td>' for v in r.values()) + "</tr>"
                         for r in runs[-5:])
        extras.append(accordion(f"Run history (last {min(len(runs), 5)} of {len(runs)})",
                                f'<div class="card"><table><thead><tr>{head}</tr></thead><tbody>\n{rows}\n</tbody></table></div>',
                                f"latest {escape(next(iter(runs[-1].values()), ''))}"))

    notes = ([f"<b>Action</b> · {escape(who)} · {escape(amount)} — {escape(text)}" for who, _, amount, text in items]
             + [f'<b>{escape(name)}</b> · {escape(kind(e))}' + (f' · {escape(e["Source"])}' if e["Source"] else "")
                + (f' · {money(cents(e["Amount"]))}' if e["Amount"] else "") + f' — {escape(e["Detail"])}'
                for name, _, _, rows in groups for e in rows]
             + notes + [SYNTHETIC, LEGEND])
    posting = t["general_journal"][0]["Posting Date"] if t["general_journal"] else ""
    label = f"{date.fromisoformat(month + '-01'):%B %Y}"
    body = (f'<header><h1>Month-end close: {label}</h1><p>Business Central import'
            + (f" · posting date {escape(posting)}" if posting else "") + "</p></header>"
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>{summary}{notice}'
            f'{action_html(items, t["exceptions"])}'
            f'<section class="noprint"><h2 class="sec">Business Central import files</h2><div class="files">{files}</div></section>'
            f'<h2 class="sec">Reconciliation by source<span class="aside noprint">Select a row for its breakdown</span></h2>'
            f'{ledger(t["control_totals"])}'
            f'<h2 class="sec noprint">Exceptions to work<span class="aside">{len(t["exceptions"])} · none of them is posted</span></h2>'
            f'{exceptions_html(groups)}'
            + ("".join(extras) and f'<h2 class="sec noprint">Sources and runs</h2>{"".join(extras)}')
            + accordion("Status definitions", f"<p>{LEGEND}</p>", "open, incomplete, unexplained, reconciled")
            + print_notes(notes)
            + '<p class="nav"><a href="../index.html">Reports</a></p>')
    return PAGE.substitute(title=f"Month-end close {month}", css=CSS + CLOSE_CSS, body=body, section=("Month-end close", f"{month}.html"))


def build(month, src=SRC, dest=DEST):
    folder = Path(src) / month
    if not (folder / f"control_totals_{month}.csv").exists():
        raise SystemExit(f"no close files in {folder}; run reports.reconcile and reports.bc_export first")
    dest = Path(dest)
    (dest / month).mkdir(parents=True, exist_ok=True)
    for k, _ in FILES:
        shutil.copyfile(folder / f"{k}_{month}.csv", dest / month / f"{k}_{month}.csv")
    page = dest / f"{month}.html"
    page.write_text(render(month, folder), encoding="utf-8")
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--month", required=True)
    args = ap.parse_args(argv)
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise SystemExit("--month must look like 2026-09")
    print(f"wrote {build(args.month)}")


if __name__ == "__main__":
    main()
