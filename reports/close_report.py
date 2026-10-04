"""Month-end close page: what `reports.bc_export` produced, for the people who post it.

Reads out/close/<YYYY-MM>/ (control totals, exceptions, General Journal, AR invoice) and writes
reports/close/<YYYY-MM>.html with the reconciliation status per source, the exceptions to work,
and download links to the four Business Central CSV files (copied next to the page).

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

from reports.pulse import CSS, PAGE

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "close"
DEST = ROOT / "reports" / "close"
FILES = [("general_journal", "General Journal lines"), ("ar_invoice", "AR invoice lines"),
         ("control_totals", "Control totals"), ("exceptions", "Exceptions")]
STATUS_CLASS = {"RECONCILED": "ok", "OPEN": "stale", "UNEXPLAINED": "missing", "MISMATCH": "missing"}

CLOSE_CSS = """
main { max-width:1100px; }
h2.sec { font-size:13px; color:var(--primary); text-transform:uppercase; letter-spacing:.05em; margin:20px 0 6px; }
.pill.stale { background:var(--ink); color:#fff; }
td.detail { white-space:normal; text-align:left; max-width:520px; }
.downloads a { margin-right:14px; }
@media print {
  @page { size:letter portrait; margin:0.4in; }
  body { font-size:8.5pt; }
  table { font-size:7.5pt; }
  th, td { padding:3px 5px; }
  td.detail { max-width:none; }
  .downloads, .nav { display:none; }
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


def render(month, folder):
    t = {k: read(folder / f"{k}_{month}.csv") for k, _ in FILES}
    docs = defaultdict(int)
    for line in t["general_journal"]:
        docs[line["Document No."]] += cents(line["Amount"])
    unbalanced = [d for d, c in docs.items() if c]
    text, alert = headline(t["control_totals"], len(docs), t["exceptions"])
    if unbalanced:
        text, alert = f"Journal does not balance: {', '.join(unbalanced)}.", True
    cols = ["Revenue In", "Revenue Posted", "Receivable Posted", "Deposits", "Open Balance", "Explained", "Unexplained"]
    control_rows = "\n".join(
        f'<tr><td>{escape(r["Source"])}</td><td>{escape(r["Path"])}</td>'
        + "".join(f"<td>{money(cents(r[c]))}</td>" for c in cols)
        + f'<td class="status"><span class="pill {STATUS_CLASS.get(r["Status"], "")}">{escape(r["Status"])}</span></td></tr>'
        for r in t["control_totals"])
    order = {"open_balance": 0, "not_posted": 1, "info": 2}
    exc = sorted(t["exceptions"], key=lambda e: (order.get(e["Effect"], 3), e["Source"], e["Kind"]))
    exc_rows = "\n".join(
        f'<tr><td>{escape(e["Kind"].replace("_", " "))}</td><td>{escape(e["Source"])}</td>'
        f'<td>{money(cents(e["Amount"])) if e["Amount"] else ""}</td><td>{escape(e["Effect"].replace("_", " "))}</td>'
        f'<td class="detail">{escape(e["Detail"])}</td></tr>' for e in exc)
    invoices = {line["Document No."] for line in t["ar_invoice"]}
    downloads = " ".join(f'<a href="{month}/{k}_{month}.csv">{label}</a>' for k, label in FILES)
    label = f"{date.fromisoformat(month + '-01'):%B %Y}"
    body = (f'<header><h1>Month-end close: {label}</h1><p>Goodwill Michiana e-commerce · Business Central import files · '
            f'{len(t["general_journal"])} journal lines in {len(docs)} documents, {len(invoices)} invoice(s)</p></header>'
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>'
            f'<p class="downloads"><strong>Download:</strong> {downloads}</p>'
            f'<h2 class="sec">Reconciliation by source</h2><div class="card"><table><thead><tr><th>Source</th><th>Path</th>'
            + "".join(f"<th>{c}</th>" for c in cols) + '<th class="status">Status</th></tr></thead><tbody>\n'
            f'{control_rows}\n</tbody></table></div>'
            f'<h2 class="sec">Exceptions to work</h2><div class="card"><table><thead><tr><th>Kind</th><th>Source</th><th>Amount</th>'
            f'<th>Effect</th><th>Detail</th></tr></thead><tbody>\n{exc_rows}\n</tbody></table></div>'
            f'<section class="foot"><p>OPEN: money still in transit or not paid out yet, fully explained by the exceptions marked '
            f'"open balance". UNEXPLAINED: money nobody has accounted for; resolve before posting. Positive amounts are debits.</p></section>'
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
