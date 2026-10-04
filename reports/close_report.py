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

from reports.pulse import CSS, PAGE

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "close"
DEST = ROOT / "reports" / "close"
SOURCES = ROOT / "reports" / "config" / "close_sources.csv"
FILES = [("general_journal", "General Journal lines"), ("ar_invoice", "AR invoice lines"),
         ("control_totals", "Control totals"), ("exceptions", "Exceptions")]
STATUS_CLASS = {"RECONCILED": "ok", "OPEN": "stale", "INCOMPLETE": "missing", "UNEXPLAINED": "missing",
                "MISMATCH": "missing"}
LABELS = {"cashmonkey": "Cash Monkey"}

CLOSE_CSS = """
main { max-width:1100px; }
h2.sec { font-size:13px; color:var(--primary); text-transform:uppercase; letter-spacing:.05em; margin:20px 0 6px; }
.pill.stale { background:var(--ink); color:#fff; }
td.detail { white-space:normal; text-align:left; max-width:520px; }
td.text, th.text { white-space:normal; text-align:left; }
td.owner { text-align:left; }
table.tight th, table.tight td { padding-left:8px; padding-right:8px; }
table.tight th { white-space:normal; }
.downloads a { margin-right:14px; }
.simnote { margin:12px 0 0; font-size:13px; border:1px dashed var(--ink); padding:8px 12px; border-radius:var(--radius); }
.state { font-weight:700; }
.state.absent { font-weight:400; color:var(--muted); }
@media print {
  @page { size:letter portrait; margin:0.4in; }
  body { font-size:8.5pt; }
  table { font-size:7.5pt; }
  th, td { padding:3px 5px; }
  td.detail { max-width:none; }
  .simnote { font-size:7.5pt; padding:3px 6px; }
  .downloads, .nav { display:none; }
}
"""


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
        f'<td class="detail">{escape(e["Detail"])}</td><td class="owner">{escape(e.get("Owner") or "")}</td>'
        f'<td class="text">{escape(e.get("Action") or "")}</td></tr>' for e in exc)

    checks = ""
    if payload.get("cross_checks"):
        rows = "\n".join(
            f'<tr><td>{escape(c["source"])}</td><td>{money(c["report_sales_cents"])}</td>'
            f'<td>{money(c["against_sales_cents"])}</td><td>{money(c["difference_cents"])}</td>'
            f'<td>{c["orders_only_in_against"]}</td><td>{c["orders_only_in_report"]}</td>'
            f'<td>{c["orders_with_another_amount"]}</td></tr>' for c in payload["cross_checks"])
        other = LABELS.get(payload["cross_checks"][0]["against"], payload["cross_checks"][0]["against"])
        checks = (f'<h2 class="sec">Cross-check: {escape(other)} against each marketplace\'s own reports</h2>'
                  f'<div class="card"><table><thead><tr><th>Marketplace</th><th>Sales in its reports</th>'
                  f'<th>Sales in {escape(other)}</th><th>Difference</th><th>Orders only in {escape(other)}</th>'
                  f'<th>Orders only in the reports</th><th>Orders with another amount</th></tr></thead><tbody>\n'
                  f'{rows}\n</tbody></table></div>'
                  f'<p class="simnote">Compared order by order, sales only. The journal posts each marketplace from its '
                  f'own reports; the {escape(other)} file is never added to them.</p>')

    sources = ""
    if payload:
        rows = "\n".join(
            f'<tr class="src"><td>{escape(r["Source"])}</td><td class="text">{escape(r["Month_End_Input"])}</td>'
            f'<td class="text">{escape(r["Acquisition_Rule"])}</td>'
            f'<td class="text"><span class="state{"" if present else " absent"}">'
            f'{escape(r["Origin"] if present else r["When_Absent"])}</span>{"; " + escape(note) if note else ""}</td>'
            f'<td class="detail">{escape(r["What_We_Read"]) if present else ""}</td></tr>'
            for r, present, note in source_states(folder, payload))
        sources = ('<h2 class="sec">Goodwill\'s nine month-end sources, and what this run has for each</h2>'
                   '<div class="card"><table><thead><tr><th>Source</th><th class="text">Month-end input</th>'
                   '<th class="text">Acquisition / rule</th>'
                   f'<th class="text">In this run</th><th class="text">What we read</th></tr></thead><tbody>\n{rows}\n</tbody></table></div>'
                   '<p class="simnote">The first three columns are Goodwill\'s own (their slide 38). "Sample file" is a '
                   'synthetic file we generated; "simulated API" is a file written by a stand-in for an API we have not '
                   'seen; "not modeled" means nothing reads that source yet.</p>')

    history = ""
    runs = read_if_there(folder / "runs.csv")
    if runs:
        head = "".join(f'<th class="text">{escape(c.replace("_", " "))}</th>' for c in runs[0])
        rows = "\n".join("<tr>" + "".join(f'<td class="text">{escape(v or "")}</td>' for v in r.values()) + "</tr>"
                         for r in runs[-5:])
        history = (f'<h2 class="sec">Run history (last {min(len(runs), 5)} of {len(runs)})</h2><div class="card"><table>'
                   f'<thead><tr>{head}</tr></thead><tbody>\n{rows}\n</tbody></table></div>')

    invoices = {line["Document No."] for line in t["ar_invoice"]}
    downloads = " ".join(f'<a href="{month}/{k}_{month}.csv">{label}</a>' for k, label in FILES)
    label = f"{date.fromisoformat(month + '-01'):%B %Y}"
    body = (f'<header><h1>Month-end close: {label}</h1><p>Goodwill Michiana e-commerce · Business Central import files · '
            f'{len(t["general_journal"])} journal lines in {len(docs)} documents, {len(invoices)} invoice(s)</p></header>'
            f'<p class="simnote"><strong>Synthetic sample data.</strong> No real Goodwill file has been read. Account, '
            f'customer and document numbers are placeholders; only department 180 comes from Goodwill\'s own slide. '
            f'<strong>Posting status: Not posted.</strong> These are import files in Business Central\'s column order; '
            f'nothing here has been sent to a Business Central.</p>'
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>'
            f'<p class="downloads"><strong>Download:</strong> {downloads}</p>'
            f'<h2 class="sec">Reconciliation by source</h2><div class="card"><table class="tight"><thead><tr><th>Source</th><th>Path</th>'
            + "".join(f"<th>{c}</th>" for c in cols) + '<th class="status">Status</th></tr></thead><tbody>\n'
            f'{control_rows}\n</tbody></table></div>'
            f'<h2 class="sec">Exceptions to work</h2><div class="card"><table><thead><tr><th>Kind</th><th>Source</th><th>Amount</th>'
            f'<th>Effect</th><th class="text">Detail</th><th class="text">Owner</th><th class="text">What to do</th></tr></thead><tbody>\n{exc_rows}\n</tbody></table></div>'
            f'{checks}{sources}{history}'
            f'<section class="foot"><p>OPEN: money still in transit or not paid out yet, fully explained by the exceptions marked '
            f'"open balance". INCOMPLETE: every cent is accounted for, but a payout paid for days no report covers; download '
            f'that report and run the close again. UNEXPLAINED: money nobody has accounted for; resolve before posting. '
            f'Positive amounts are debits. The owners are role names we chose, not Goodwill\'s.</p></section>'
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
