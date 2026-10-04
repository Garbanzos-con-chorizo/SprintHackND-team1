"""Month-end close page: what `reports.bc_export` produced, for the people who post it.

Reads out/close/<YYYY-MM>/ (control totals, exceptions, General Journal, AR invoice) and writes
reports/close/<YYYY-MM>.html: what to resolve before posting, the reconciliation per source, the
exceptions to work, and download links to the four Business Central CSV files (copied next to the
page).

Default view: status and amounts. Each action item opens to its full text, each ledger row to its
breakdown (path, revenue in, receivable, deposits, explained), and the exceptions sit in one
accordion per effect. In print the detail rows show and the action texts, exceptions and status
definitions print as one-line notes, on one portrait page.

    python -m reports.close_report --month 2026-09
"""
import argparse
import csv
import re
import shutil
from collections import defaultdict
from datetime import date
from html import escape
from pathlib import Path

from reports.theme import CSS, PAGE, accordion, expander, facts, kv, print_notes

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "close"
DEST = ROOT / "reports" / "close"
FILES = [("general_journal", "General Journal lines"), ("ar_invoice", "AR invoice lines"),
         ("control_totals", "Control totals"), ("exceptions", "Exceptions")]
STATUS_CLASS = {"RECONCILED": "ok", "OPEN": "open", "UNEXPLAINED": "bad", "MISMATCH": "bad"}
# Exception effects (docs/contracts/close-payload.md), in the order they are worked.
EFFECTS = [("open_balance", "Open balance", "in transit or not paid out yet; explains the open balance"),
           ("not_posted", "Not posted", "held out of the Business Central files"),
           ("info", "For review", "changes no number")]
LEGEND = ("<b>OPEN:</b> money still in transit or not paid out yet, fully explained by the exceptions under "
          '"Open balance". <b>UNEXPLAINED:</b> money nobody has accounted for; resolve before posting. '
          "<b>RECONCILED:</b> open balance 0.00. Positive amounts are debits.")
DOWNLOAD_ICON = ('<svg width="11" height="11" viewBox="0 0 10 10" aria-hidden="true"><path d="M5 0v6.5M2 3.8 5 6.8 8 3.8'
                 'M0.5 9.3h9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>')

CLOSE_CSS = """
/* Action required: one row per item, opening to its full text */
.action { margin-top:var(--sp-3); padding:var(--sp-1) 0; }
.action-hd { display:flex; flex-wrap:wrap; align-items:center; gap:var(--sp-1) 10px; padding:10px var(--sp-5); font-size:13px; color:var(--muted); }
details.act { border-top:1px solid var(--hair); }
details.act > summary { display:grid; grid-template-columns:minmax(80px,140px) minmax(0,1fr) auto 14px; align-items:center;
  gap:var(--sp-3); padding:11px var(--sp-5); list-style:none; cursor:pointer; }
details.act > summary::-webkit-details-marker { display:none; }
details.act > summary::after { content:"\\203A"; justify-self:end; font-size:18px; line-height:1; color:var(--faint); transition:transform .2s ease; }
details.act[open] > summary::after { transform:rotate(90deg); }
details.act > summary:hover { background:var(--hover); }
.act .who { font-weight:var(--fw-semi); }
.act .what { color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.act .amt { font-weight:var(--fw-semi); color:var(--bad); }
.act p { padding:0 var(--sp-5) var(--sp-3); font-size:13px; color:var(--muted); }

/* Business Central files */
.files { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:var(--sp-3); }
.file { display:flex; flex-direction:column; gap:2px; padding:var(--sp-4) var(--sp-5); background:var(--card);
  border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); color:var(--ink);
  transition:box-shadow .2s ease, transform .2s ease; }
.file:hover { text-decoration:none; box-shadow:0 8px 28px rgba(0,0,0,.07); transform:translateY(-1px); }
.file b { font-weight:var(--fw-semi); }
.file b span { margin-left:var(--sp-2); font-weight:var(--fw-regular); color:var(--muted); }
.file code { font-size:var(--fs-small); color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.file .get { align-self:flex-start; display:inline-flex; align-items:center; gap:6px; margin-top:10px; padding:4px 12px;
  border-radius:980px; background:var(--accent); color:#fff; font-size:var(--fs-small); font-weight:var(--fw-semi); }

/* Ledger and exceptions */
.dot { display:inline-block; width:7px; height:7px; margin-right:8px; border-radius:50%; background:var(--bad); vertical-align:1px; }
table.ledger td.zero { color:var(--faint); }
table.ledger td.bad { color:var(--bad); font-weight:var(--fw-semi); }
table.exc td.detail { min-width:300px; text-align:left; white-space:normal; color:var(--muted); }
@media (max-width:640px) {
  details.act > summary { grid-template-columns:minmax(0,1fr) auto 14px; }
  .act .what { grid-column:1 / -1; grid-row:2; }
}
@media print {
  @page { size:letter portrait; margin:0.4in; }
  body { font-size:8pt; }
  .action { margin-top:4pt; padding:1pt 0; box-shadow:none; border-color:#d2d2d7; border-radius:8px; }
  .action-hd { padding:2pt 8pt; font-size:7.5pt; }
  details.act > summary { padding:2pt 8pt; grid-template-columns:70pt minmax(0,1fr) auto; gap:6pt; }
  details.act > summary::after { display:none; }
}
"""


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cents(text):
    return round(float(text) * 100) if text not in ("", None) else 0


def money(c):
    return f"{'-' if c < 0 else ''}${abs(c) / 100:,.2f}"


def headline(control, journal_docs, exceptions):
    bad = [r for r in control if r["Status"] in ("UNEXPLAINED", "MISMATCH")]
    parts = [f"{journal_docs} journal documents, all balanced to 0.00"]
    parts.append(", ".join(f"{r['Source']} {r['Status']}" + (f" ({money(cents(r['Unexplained']))})" if r["Status"] == "UNEXPLAINED" else "")
                           for r in control))
    parts.append(f"{len(exceptions)} exceptions")
    return "; ".join(parts) + ".", bool(bad)


def amount_cell(c, cls=""):
    cls = " ".join(x for x in (cls, "zero" if c == 0 else "") if x)
    return f'<td class="{cls}">{money(c)}</td>' if cls else f"<td>{money(c)}</td>"


def ledger(control):
    """Control totals: source, revenue posted, open balance, unexplained and status; each row opens
    to the rest of its control totals. A red dot marks a source that is neither reconciled nor explained."""
    body = []
    totals = dict.fromkeys(("Revenue Posted", "Open Balance", "Unexplained"), 0)
    for i, r in enumerate(control):
        for c in totals:
            totals[c] += cents(r[c])
        dot = '<span class="dot"></span>' if STATUS_CLASS.get(r["Status"]) == "bad" else ""
        detail_id = f"src-{i}"
        breakdown = kv([("Path", escape(r["Path"])), ("Revenue in", money(cents(r["Revenue In"]))),
                        ("Revenue posted", money(cents(r["Revenue Posted"]))),
                        ("Difference", money(cents(r["Difference"])) if cents(r.get("Difference")) else ""),
                        ("Receivable posted", money(cents(r["Receivable Posted"]))),
                        ("Deposits", money(cents(r["Deposits"]))), ("Explained", money(cents(r["Explained"])))])
        body.append(f'<tr class="xrow"><td>{expander(detail_id)}{dot}'
                    f'<b>{escape(r["Source"])}</b></td>{amount_cell(cents(r["Revenue Posted"]))}'
                    f'{amount_cell(cents(r["Open Balance"]))}'
                    f'{amount_cell(cents(r["Unexplained"]), "bad" if cents(r["Unexplained"]) else "")}'
                    f'<td class="status"><span class="pill {STATUS_CLASS.get(r["Status"], "")}">{escape(r["Status"])}</span></td></tr>'
                    f'<tr class="xdetail" id="{detail_id}" hidden><td colspan="5">{breakdown}</td></tr>')
    body.append(f'<tr class="total"><td>Total</td>{"".join(amount_cell(v) for v in totals.values())}<td></td></tr>')
    return ('<div class="card"><table class="ledger"><thead><tr><th>Source</th><th>Revenue posted</th><th>Open balance</th>'
            '<th>Unexplained</th><th class="status">Status</th></tr></thead><tbody>\n' + "\n".join(body) + "\n</tbody></table></div>")


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


def kind(e):
    return e["Kind"].replace("_", " ").capitalize()


def exceptions_html(groups):
    """One accordion per effect, closed: the count and sum show, the rows open on demand."""
    parts = []
    for name, what, total, rows in groups:
        lines = "".join(f'<tr><td>{escape(kind(e))}</td><td class="l">{escape(e["Source"]) or "-"}</td>'
                        f'<td>{money(cents(e["Amount"])) if e["Amount"] else ""}</td>'
                        f'<td class="detail">{escape(e["Detail"])}</td></tr>' for e in rows)
        table = ('<div class="card"><table class="exc"><thead><tr><th>Kind</th><th class="l">Source</th><th>Amount</th>'
                 f'<th class="l">Detail</th></tr></thead><tbody>{lines}</tbody></table></div>')
        meta = " · ".join(x for x in (str(len(rows)), total, what) if x)
        parts.append(accordion(name, table, escape(meta)))
    return "".join(parts)


def exception_notes(groups):
    return [f'<b>{escape(name)}</b> · {escape(kind(e))}' + (f' · {escape(e["Source"])}' if e["Source"] else "")
            + (f' · {money(cents(e["Amount"]))}' if e["Amount"] else "") + f' — {escape(e["Detail"])}'
            for name, _, _, rows in groups for e in rows]


def action_items(control, exceptions, docs, unbalanced):
    """What must be resolved before the files are imported: unbalanced documents, sources with money
    nobody has accounted for, and anything held out of the files. (who, short label, amount, full text)."""
    items = [("Journal", "Unbalanced document", money(docs[d]), f"Document {d} does not balance; import nothing until it does.")
             for d in unbalanced]
    for r in control:
        if r["Status"] == "UNEXPLAINED":
            why = next((e["Detail"] for e in exceptions if e["Source"] == r["Source"] and e["Kind"] == "residual_unexplained"),
                       "Open balance nobody has accounted for; resolve before posting.")
            items.append((r["Source"], "Unexplained balance", money(cents(r["Unexplained"])), why))
        elif r["Status"] == "MISMATCH":
            items.append((r["Source"], "Revenue mismatch", money(cents(r["Difference"])),
                          "Posted revenue differs from the input; do not import."))
    for e in exceptions:
        if e["Effect"] == "not_posted":
            items.append((e["Source"] or "Unassigned", kind(e), money(cents(e["Amount"])) if e["Amount"] else "", e["Detail"]))
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
        ("Sources", " · ".join(f"{statuses.count(s)} {s.lower()}" for s in STATUS_CLASS if s in statuses),
         "bad" if any(STATUS_CLASS.get(s) == "bad" for s in statuses) else ""),
        ("Exceptions", f'{len(t["exceptions"])} · {held} held out', "bad" if held else ""),
    ])
    items = action_items(t["control_totals"], t["exceptions"], docs, unbalanced)
    groups = exception_groups(t["exceptions"])
    files = "".join(f'<a class="file" href="{month}/{k}_{month}.csv" download><b>{label}<span>{len(t[k])} rows</span></b>'
                    f'<code>{k}_{month}.csv</code><span class="get">{DOWNLOAD_ICON}Download CSV</span></a>'
                    for k, label in FILES)
    notes = ([f"<b>Action</b> · {escape(who)} · {escape(amount)} — {escape(text)}" for who, _, amount, text in items]
             + exception_notes(groups) + [LEGEND])
    posting = t["general_journal"][0]["Posting Date"] if t["general_journal"] else ""
    label = f"{date.fromisoformat(month + '-01'):%B %Y}"
    body = (f'<header><h1>Month-end close: {label}</h1><p>Business Central import'
            + (f" · posting date {escape(posting)}" if posting else "") + "</p></header>"
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>{summary}'
            f'{action_html(items, t["exceptions"])}'
            f'<section class="noprint"><h2 class="sec">Business Central import files</h2><div class="files">{files}</div></section>'
            f'<h2 class="sec">Reconciliation by source<span class="aside noprint">Select a row for its breakdown</span></h2>'
            f'{ledger(t["control_totals"])}'
            f'<h2 class="sec noprint">Exceptions to work<span class="aside">{len(t["exceptions"])} · none of them is posted</span></h2>'
            f'{exceptions_html(groups)}'
            f'{accordion("Status definitions", f"<p>{LEGEND}</p>", "open, unexplained, reconciled")}'
            + print_notes(notes)
            + '<p class="nav"><a href="../index.html">Reports</a></p>')
    return PAGE.substitute(title=f"Month-end close {month}", css=CSS + CLOSE_CSS, body=body)


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
