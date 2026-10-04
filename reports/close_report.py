"""Month-end close page: what `reports.bc_export` produced, for the people who post it.

Reads out/close/<YYYY-MM>/ (control totals, exceptions, General Journal, AR invoice) and writes
reports/close/<YYYY-MM>.html with what to resolve before posting, the reconciliation ledger per
source, the exceptions to work, and download links to the four Business Central CSV files
(copied next to the page). Prints on one portrait page.

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

from reports.theme import CSS, PAGE, facts

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "close"
DEST = ROOT / "reports" / "close"
FILES = [("general_journal", "General Journal lines"), ("ar_invoice", "AR invoice lines"),
         ("control_totals", "Control totals"), ("exceptions", "Exceptions")]
STATUS_CLASS = {"RECONCILED": "ok", "OPEN": "open", "UNEXPLAINED": "bad", "MISMATCH": "bad"}
# The reconciliation ledger: control-total columns under group headings (CSV column, short heading).
GROUPS = [("Revenue", [("Revenue In", "In"), ("Revenue Posted", "Posted")]),
          ("Receivable", [("Receivable Posted", "Posted"), ("Deposits", "Deposits"), ("Open Balance", "Open")]),
          ("Open balance", [("Explained", "Explained"), ("Unexplained", "Unexplained")])]
# Exception effects (docs/contracts/close-payload.md), in the order they are worked.
EFFECTS = [("open_balance", "Open balance", "in transit or not paid out yet; explains the open balance"),
           ("not_posted", "Not posted", "held out of the Business Central files"),
           ("info", "For review", "changes no number")]
DOWNLOAD_ICON = ('<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M5 0v6.5M2 3.8 5 6.8 8 3.8'
                 'M0 9.4h10" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>')

CLOSE_CSS = """
/* Action required: what to resolve before posting, one ledger-style line per item */
.action { margin:var(--sp-4) 0 0; background:var(--bg); border:var(--bd); border-left:3px solid var(--red); }
.action.clear { border-left-color:var(--green); }
.action > p { display:flex; flex-wrap:wrap; align-items:baseline; gap:var(--sp-1) var(--sp-4); padding:var(--sp-3) var(--sp-5); }
.action > p strong { font-size:var(--fs-label); letter-spacing:.06em; text-transform:uppercase; color:var(--red); }
.action.clear > p strong { color:var(--green); }
.action > p span { color:var(--ink-2); }
.action ol { list-style:none; margin:0; padding:0; }
.action li { display:grid; grid-template-columns:120px 96px minmax(0,1fr); gap:var(--sp-5); padding:var(--sp-3) var(--sp-5);
  border-top:var(--bd); }
.action .who { font-weight:var(--fw-bold); }
.action .amt { text-align:right; font-weight:var(--fw-bold); color:var(--red); white-space:nowrap; }
.action .what { color:var(--ink-2); }

/* Business Central files: one download control per CSV */
.files { display:flex; flex-wrap:wrap; gap:1px; background:var(--rule); border:var(--bd); }
.file { flex:1 1 220px; display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:1px var(--sp-4);
  padding:var(--sp-4) var(--sp-5); background:var(--bg); color:var(--ink); }
.file:hover { background:var(--blue-tint); text-decoration:none; }
.file b { font-weight:var(--fw-semi); }
.file b span { margin-left:var(--sp-3); font-weight:var(--fw-regular); color:var(--muted); }
.file code { grid-column:1; padding:0; background:none; font-size:var(--fs-small); color:var(--muted);
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.file .get { grid-column:2; grid-row:1 / span 2; display:inline-flex; align-items:center; gap:var(--sp-2);
  padding:var(--sp-1) var(--sp-3); border:1px solid var(--blue); color:var(--blue); font-size:var(--fs-label);
  font-weight:var(--fw-bold); letter-spacing:.06em; }
.file:hover .get { background:var(--blue); color:#fff; }

/* Reconciliation ledger and exceptions */
table.ledger { min-width:880px; }
table.ledger thead tr + tr th:first-child { text-align:right; }
table.ledger th.grp { text-align:center; border-bottom:1px solid var(--blue); padding-bottom:var(--sp-1); }
table.ledger .g { border-left:var(--bd); }
table.ledger td.zero { color:var(--muted); }
table.ledger td.bad { color:var(--red); font-weight:var(--fw-bold); }
table.ledger tr.flag > td:first-child { box-shadow:inset 3px 0 0 var(--red); }
table.exc td.detail { white-space:normal; text-align:left; min-width:320px; color:var(--ink-2); }
table.exc tr.grp > * { background:var(--bg-2); border-bottom:var(--bd); color:var(--ink); }
table.exc tr.grp th { text-align:left; }
table.exc tr.grp .count { margin-left:var(--sp-3); color:var(--muted); }
table.exc tr.grp td { font-weight:var(--fw-bold); }
table.exc tr.grp td.l { font-weight:var(--fw-regular); color:var(--muted); white-space:normal; }
table.exc .none { color:var(--muted); }
@media (max-width:640px) {
  .action li { grid-template-columns:minmax(0,1fr) auto; gap:var(--sp-1) var(--sp-4); }
  .action .what { grid-column:1 / -1; }
}
@media print {
  @page { size:letter portrait; margin:0.4in; }
  body { font-size:8pt; }
  .action > p { padding:3pt 7pt; }
  .action li { grid-template-columns:72pt 58pt minmax(0,1fr); gap:6pt; padding:2.5pt 7pt; }
  table.ledger, table.exc td.detail { min-width:0; }
  table.ledger, table.exc { font-size:7.5pt; }
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


def amount_cell(c, *classes):
    cls = " ".join(x for x in (*classes, "zero" if c == 0 else "") if x)
    return f'<td class="{cls}">{money(c)}</td>' if cls else f"<td>{money(c)}</td>"


def ledger(control):
    """Control totals as a ledger: money columns in groups, a red edge on each source that is
    neither reconciled nor explained, and a total line."""
    cols = [c for _, group in GROUPS for c, _ in group]
    starts = {group[0][0] for _, group in GROUPS}
    head = ('<tr><th rowspan="2">Source</th><th rowspan="2" class="l">Path</th>'
            + "".join(f'<th class="grp g" colspan="{len(group)}">{name}</th>' for name, group in GROUPS)
            + '<th rowspan="2" class="status">Status</th></tr><tr>'
            + "".join(f'<th class="g">{short}</th>' if c in starts else f"<th>{short}</th>"
                      for _, group in GROUPS for c, short in group) + "</tr>")
    body, totals = [], dict.fromkeys(cols, 0)
    for r in control:
        cells = []
        for c in cols:
            totals[c] += cents(r[c])
            cells.append(amount_cell(cents(r[c]), "g" if c in starts else "",
                                     "bad" if c == "Unexplained" and cents(r[c]) else ""))
        flag = ' class="flag"' if STATUS_CLASS.get(r["Status"]) == "bad" else ""
        body.append(f'<tr{flag}><td><b>{escape(r["Source"])}</b></td><td class="l">{escape(r["Path"])}</td>{"".join(cells)}'
                    f'<td class="status"><span class="pill {STATUS_CLASS.get(r["Status"], "")}">{escape(r["Status"])}</span></td></tr>')
    total = "".join(amount_cell(totals[c], "g" if c in starts else "") for c in cols)
    body.append(f'<tr class="total"><td>Total</td><td></td>{total}<td></td></tr>')
    return f'<div class="card"><table class="ledger"><thead>{head}</thead><tbody>\n' + "\n".join(body) + "\n</tbody></table></div>"


def exceptions_table(exceptions):
    """Exceptions grouped by effect. The group line carries the count and, where the amounts add up
    to something (open balance, not posted), their sum."""
    known = [e for e, _, _ in EFFECTS]
    groups = []
    for effect, name, what in EFFECTS + [(None, "Other", "")]:
        rows = [e for e in exceptions if (e["Effect"] == effect if effect else e["Effect"] not in known)]
        if not rows:
            continue
        rows.sort(key=lambda e: (e["Source"] == "", e["Source"], e["Kind"]))
        total = money(sum(cents(e["Amount"]) for e in rows)) if effect in ("open_balance", "not_posted") else ""
        lines = [f'<tr class="grp"><th colspan="2" scope="rowgroup">{name}<span class="count">{len(rows)}</span></th>'
                 f'<td>{total}</td><td class="l">{what}</td></tr>']
        for e in rows:
            source = escape(e["Source"]) if e["Source"] else '<span class="none">-</span>'
            lines.append(f'<tr><td>{escape(e["Kind"].replace("_", " ").capitalize())}</td><td class="l">{source}</td>'
                         f'<td>{money(cents(e["Amount"])) if e["Amount"] else ""}</td>'
                         f'<td class="detail">{escape(e["Detail"])}</td></tr>')
        groups.append("<tbody>\n" + "\n".join(lines) + "\n</tbody>")
    return ('<div class="card"><table class="exc"><thead><tr><th>Kind</th><th class="l">Source</th><th>Amount</th>'
            '<th class="l">Detail</th></tr></thead>\n' + "\n".join(groups) + "\n</table></div>")


def action_items(control, exceptions, docs, unbalanced):
    """What must be resolved before the files are imported: unbalanced documents, sources with money
    nobody has accounted for, and anything held out of the files."""
    items = [("Journal", money(docs[d]), f"Document {d} does not balance; import nothing until it does.")
             for d in unbalanced]
    for r in control:
        if r["Status"] == "UNEXPLAINED":
            why = next((e["Detail"] for e in exceptions if e["Source"] == r["Source"] and e["Kind"] == "residual_unexplained"),
                       "Open balance nobody has accounted for; resolve before posting.")
            items.append((r["Source"], money(cents(r["Unexplained"])), why))
        elif r["Status"] == "MISMATCH":
            items.append((r["Source"], money(cents(r["Difference"])), "Posted revenue differs from the input; do not import."))
    for e in exceptions:
        if e["Effect"] == "not_posted":
            items.append((e["Source"] or "Unassigned", money(cents(e["Amount"])) if e["Amount"] else "",
                          f'{e["Kind"].replace("_", " ").capitalize()}: {e["Detail"]}'))
    if not items:
        review = sum(e["Effect"] == "info" for e in exceptions)
        more = f"; {review} exception(s) for review below" if review else ""
        return ('<div class="action clear"><p><strong>No action required before posting</strong>'
                f'<span>Every source is reconciled or fully explained{more}.</span></p></div>')
    lines = "".join(f'<li><span class="who">{escape(who)}</span><span class="amt">{escape(amount)}</span>'
                    f'<span class="what">{escape(what)}</span></li>' for who, amount, what in items)
    return (f'<div class="action"><p><strong>Action required</strong><span>{len(items)} item(s) to resolve before '
            f'posting</span></p><ol>{lines}</ol></div>')


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
    files = "".join(f'<a class="file" href="{month}/{k}_{month}.csv" download><b>{label}<span>{len(t[k])} rows</span></b>'
                    f'<code>{k}_{month}.csv</code><span class="get">{DOWNLOAD_ICON}CSV</span></a>'
                    for k, label in FILES)
    posting = t["general_journal"][0]["Posting Date"] if t["general_journal"] else ""
    label = f"{date.fromisoformat(month + '-01'):%B %Y}"
    body = (f'<header><h1>Month-end close: {label}</h1><p>Business Central import'
            + (f" · posting date {escape(posting)}" if posting else "") + "</p></header>"
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>{summary}'
            f'{action_items(t["control_totals"], t["exceptions"], docs, unbalanced)}'
            f'<section class="noprint"><h2 class="sec">Business Central import files<span class="aside">CSV, copied '
            f'next to this page</span></h2><div class="files">{files}</div></section>'
            f'<h2 class="sec">Reconciliation by source<span class="aside">Positive amounts are debits</span></h2>'
            f'{ledger(t["control_totals"])}'
            f'<h2 class="sec">Exceptions to work<span class="aside">None of them is posted</span></h2>'
            f'{exceptions_table(t["exceptions"])}'
            f'<section class="foot"><p><b>OPEN:</b> money still in transit or not paid out yet, fully explained by the '
            f'exceptions under "Open balance". <b>UNEXPLAINED:</b> money nobody has accounted for; resolve before '
            f'posting. <b>RECONCILED:</b> open balance 0.00.</p></section>'
            f'<p class="nav"><a href="../index.html">Reports</a></p>')
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
