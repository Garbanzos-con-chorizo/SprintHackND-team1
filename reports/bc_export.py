"""Business Central month-end export: General Journal lines, AR invoice lines and control totals (phase 3).

Input is a close payload (JSON): month totals per source, the bank deposits matched to each
source, and the open exceptions. Rules live in reports/config/bc_mapping.csv, one row per source:
which path it posts through (Journal or Invoice, never both), its G/L accounts, customer and
department. Staff change a rule by editing that file, not this code.

Output (out/close/<YYYY-MM>/), CSV in the column order of the BC pages so rows can be pasted
into the General Journal / Sales Invoice grid or loaded with Edit in Excel:
  general_journal_<YYYY-MM>.csv   one balanced document per journal-path source, one per deposit
  ar_invoice_<YYYY-MM>.csv        one sales invoice per invoice-path source
  control_totals_<YYYY-MM>.csv    source totals in vs posted, deposits, open balance
Money is integer cents internally; BC convention on output: positive = debit, negative = credit.
If any document does not sum to 0.00, nothing is written and the command exits 1. After writing,
the files are read back and checked again (exit 2 if that check fails).

    python -m reports.bc_export                       # built-in mock payload (perfectly reconciled)
    python -m reports.bc_export --payload close.json  # a real payload, e.g. from reconciliation
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPING = ROOT / "reports" / "config" / "bc_mapping.csv"
OUT = ROOT / "out" / "close"
JOURNAL_COLUMNS = ["Posting Date", "Document Type", "Document No.", "Account Type", "Account No.", "Description",
                   "Amount", "Department Code"]
INVOICE_COLUMNS = ["Document No.", "Customer No.", "Posting Date", "Type", "No.", "Description", "Quantity",
                   "Unit Price", "Amount", "Department Code"]
CONTROL_COLUMNS = ["Source", "Path", "Revenue In", "Revenue Posted", "Difference", "Receivable Posted",
                   "Deposits", "Open Balance", "Explained", "Unexplained", "Status"]
EXCEPTION_COLUMNS = ["Kind", "Source", "Amount", "Effect", "Detail"]
# Effect of an exception: "open_balance" explains part of a source's open balance (money in transit,
# activity not paid yet, a payout for activity missing from our files); "not_posted" = held out of BC;
# "info" = nothing to post, someone should look.
# Status of a source, worst first: MISMATCH (posted revenue differs from the input), UNEXPLAINED (money
# nobody has accounted for), INCOMPLETE (accounted for, but a report is missing), OPEN, RECONCILED.


def _mock_payload():
    """September close, perfectly reconciled: every source's deposits add up to exactly what it is owed.
    Sales, refunds and fees for eBay and Amazon, and ShopGoodwill sales, are the messy_month file totals."""
    sources = {
        "ebay": {"sales_cents": 2005232, "refunds_cents": 9497, "shipping_cents": 98460, "handling_cents": 0,
                 "fees_cents": 310373},
        "amazon": {"sales_cents": 943451, "refunds_cents": 5198, "shipping_cents": 163590, "handling_cents": 0,
                   "fees_cents": 233115},
        "shopgoodwill": {"sales_cents": 3911800, "refunds_cents": 0, "shipping_cents": 1407626,
                         "handling_cents": 352200, "fees_cents": 0},
    }
    partial = {"ebay": [("2026-09-08", 445000), ("2026-09-15", 452311), ("2026-09-22", 431200), ("2026-09-29", None)],
               "amazon": [("2026-09-18", 405100), ("2026-09-30", None)],
               "shopgoodwill": [("2026-09-08", 1302344), ("2026-09-15", 1488210), ("2026-09-22", 1395522),
                                ("2026-09-29", None)]}
    deposits = []
    for src, rows in partial.items():
        owed = net(sources[src])
        for d, cents in rows:  # the last deposit is whatever is left, so the source is fully paid
            cents = owed - sum(x["amount_cents"] for x in deposits if x["source"] == src) if cents is None else cents
            deposits.append({"date": d, "source": src, "amount_cents": cents,
                             "reference": f"{src.upper()} PAYOUT {d[5:7]}{d[8:]}"})
    return {"month": "2026-09", "posting_date": "2026-09-30", "mock": "built-in mock payload",
            "sources": sources, "deposits": deposits, "exceptions": []}


def net(s):
    """What the marketplace owes Goodwill for the month."""
    return s["sales_cents"] - s["refunds_cents"] + s["shipping_cents"] + s.get("handling_cents", 0) - s["fees_cents"]


def load_mapping(path=MAPPING):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = {r["Source"].strip(): {k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)}
    for src, r in rows.items():
        if r["Path"] not in ("Journal", "Invoice"):
            raise ValueError(f"bc_mapping.csv: {src} has Path '{r['Path']}', expected Journal or Invoice")
        if r["Path"] == "Invoice" and not r["Customer_No"]:
            raise ValueError(f"bc_mapping.csv: {src} posts by invoice but has no Customer_No")
        if r["Path"] == "Journal" and not r["Clearing_Account"]:
            raise ValueError(f"bc_mapping.csv: {src} posts by journal but has no Clearing_Account")
    return rows


def build(payload, mapping):
    """Journal lines, invoice lines, control rows and exceptions, all in cents. No I/O."""
    month = payload["month"]
    yymm = month[2:4] + month[5:7]
    posting = payload["posting_date"]
    period = f"{date.fromisoformat(month + '-01'):%b %Y}"
    journal, invoice, exceptions = [], [], list(payload.get("exceptions", []))

    def jl(doc, account_type, account, desc, cents, m, doc_type="", when=posting):
        journal.append({"Posting Date": when, "Document Type": doc_type,
                        "Document No.": doc, "Account Type": account_type, "Account No.": account,
                        "Description": desc, "Amount": cents, "Department Code": m["Department_Code"]})

    def il(doc, m, account, desc, cents):
        invoice.append({"Document No.": doc, "Customer No.": m["Customer_No"], "Posting Date": posting,
                        "Type": "G/L Account", "No.": account, "Description": desc, "Quantity": 1,
                        "Unit Price": cents, "Amount": cents, "Department Code": m["Department_Code"]})

    posted_sources = []
    for src, s in payload["sources"].items():
        m = mapping.get(src)
        if not m:
            exceptions.append({"kind": "unmapped_source", "source": src, "amount_cents": net(s), "effect": "not_posted",
                               "detail": f"{src}: no row in bc_mapping.csv; not posted"})
            continue
        posted_sources.append(src)
        label, code = m["Label"], m["Code"]
        parts = [("Sales_Account", f"{label} sales {period}", -s["sales_cents"]),
                 ("Refunds_Account", f"{label} refunds {period}", s["refunds_cents"]),
                 ("Shipping_Account", f"{label} shipping charged {period}", -s["shipping_cents"]),
                 ("Handling_Account", f"{label} handling {period}", -s.get("handling_cents", 0))]
        if m["Path"] == "Journal":
            doc = f"ECOM-{yymm}-{code}"
            jl(doc, "G/L Account", m["Clearing_Account"], f"{label} net receivable {period}", net(s), m)
            for col, desc, cents in parts:
                if cents:
                    jl(doc, "G/L Account", m[col], desc, cents, m)
            if s["fees_cents"]:
                jl(doc, "G/L Account", m["Fees_Account"], f"{label} marketplace fees {period}", s["fees_cents"], m)
        else:
            doc = f"SI-ECOM-{yymm}-{code}"
            for col, desc, cents in parts:
                if cents:
                    il(doc, m, m[col], desc, -cents)  # invoice lines are positive for income, negative for refunds
            if s["fees_cents"]:
                fees_doc = f"ECOM-{yymm}-{code}-FEES"
                jl(fees_doc, "G/L Account", m["Fees_Account"], f"{label} marketplace fees {period}", s["fees_cents"], m)
                jl(fees_doc, "Customer", m["Customer_No"], f"{label} marketplace fees {period}", -s["fees_cents"], m)

    seen = defaultdict(int)
    for dep in sorted(payload.get("deposits", []), key=lambda d: (d["date"], d["source"])):
        m = mapping.get(dep["source"])
        if not m or dep["source"] not in posted_sources:
            exceptions.append({"kind": "unmatched_deposit", "source": dep["source"], "amount_cents": dep["amount_cents"],
                               "effect": "not_posted",
                               "detail": f"{dep['date']} {dep.get('reference', '')}: source '{dep['source']}' "
                                         f"not posted this month"})
            continue
        base = f"BNK-{dep['date'][5:7]}{dep['date'][8:]}-{m['Code']}"
        seen[base] += 1
        doc = base if seen[base] == 1 else f"{base}-{seen[base]}"
        desc = f"{dep.get('reference') or m['Label'] + ' payout'} deposit"
        jl(doc, "Bank Account", m["Bank_Account"], desc, dep["amount_cents"], m, "Payment", dep["date"])
        if m["Path"] == "Journal":
            jl(doc, "G/L Account", m["Clearing_Account"], desc, -dep["amount_cents"], m, "Payment", dep["date"])
        else:
            jl(doc, "Customer", m["Customer_No"], desc, -dep["amount_cents"], m, "Payment", dep["date"])

    control = []
    for src in posted_sources:
        s, m = payload["sources"][src], mapping[src]
        rev_in = s["sales_cents"] - s["refunds_cents"]
        accounts = {m["Sales_Account"], m["Refunds_Account"]}
        if m["Path"] == "Journal":
            rev_posted = -sum(l["Amount"] for l in journal if l["Document No."] == f"ECOM-{yymm}-{m['Code']}"
                              and l["Account No."] in accounts)
            receivable = sum(l["Amount"] for l in journal if l["Account No."] == m["Clearing_Account"]
                             and l["Document No."].startswith("ECOM"))
        else:
            rev_posted = sum(l["Amount"] for l in invoice if l["Customer No."] == m["Customer_No"] and l["No."] in accounts)
            receivable = (sum(l["Amount"] for l in invoice if l["Customer No."] == m["Customer_No"])
                          + sum(l["Amount"] for l in journal if l["Account No."] == m["Customer_No"]
                                and l["Document Type"] != "Payment"))
        deposits = sum(d["amount_cents"] for d in payload.get("deposits", []) if d["source"] == src)
        diff, open_balance = rev_posted - rev_in, receivable - deposits
        explained = sum(e.get("amount_cents", 0) for e in exceptions
                        if e.get("effect") == "open_balance" and e.get("source") == src)
        unexplained = open_balance - explained
        # INCOMPLETE: every cent is accounted for, but a payout paid for days no report covers, so the
        # revenue posted for this source is known to be short until that report is downloaded.
        incomplete = any(e.get("kind") == "payout_data_gap" and e.get("source") == src for e in exceptions)
        status = ("MISMATCH" if diff else "UNEXPLAINED" if unexplained else "INCOMPLETE" if incomplete
                  else "OPEN" if open_balance else "RECONCILED")
        control.append({"Source": m["Label"], "Path": m["Path"], "Revenue In": rev_in, "Revenue Posted": rev_posted,
                        "Difference": diff, "Receivable Posted": receivable, "Deposits": deposits,
                        "Open Balance": open_balance, "Explained": explained, "Unexplained": unexplained,
                        "Status": status})
    return journal, invoice, control, exceptions


def unbalanced(journal):
    """Documents whose lines don't sum to zero: {document: cents}."""
    sums = defaultdict(int)
    for line in journal:
        sums[line["Document No."]] += line["Amount"]
    return {doc: c for doc, c in sums.items() if c}


def dollars(cents):
    return f"{'-' if cents < 0 else ''}{abs(cents) // 100}.{abs(cents) % 100:02d}"


def us_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.month:02d}/{d.day:02d}/{d.year}"


def write(folder, month, journal, invoice, control, exceptions, mapping):
    folder.mkdir(parents=True, exist_ok=True)
    paths = {k: folder / f"{k}_{month}.csv" for k in ("general_journal", "ar_invoice", "control_totals", "exceptions")}
    with open(paths["general_journal"], "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(JOURNAL_COLUMNS)
        for l in journal:
            w.writerow([us_date(l["Posting Date"]), l["Document Type"], l["Document No."], l["Account Type"],
                        l["Account No."], l["Description"], dollars(l["Amount"]), l["Department Code"]])
    with open(paths["ar_invoice"], "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(INVOICE_COLUMNS)
        for l in invoice:
            w.writerow([l["Document No."], l["Customer No."], us_date(l["Posting Date"]), l["Type"], l["No."],
                        l["Description"], l["Quantity"], dollars(l["Unit Price"]), dollars(l["Amount"]),
                        l["Department Code"]])
    with open(paths["control_totals"], "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CONTROL_COLUMNS)
        for r in control:
            w.writerow([r[c] if c in ("Source", "Path", "Status") else dollars(r[c]) for c in CONTROL_COLUMNS])
    with open(paths["exceptions"], "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(EXCEPTION_COLUMNS)
        for e in exceptions:
            src = e.get("source") or ""
            w.writerow([e["kind"], mapping.get(src, {}).get("Label", src),
                        dollars(e["amount_cents"]) if e.get("amount_cents") is not None else "",
                        e.get("effect", "info"), e["detail"]])
    return paths


def verify_files(paths):
    """Read the written CSVs back and re-check them from the text alone. Returns a list of problems."""
    def cents(text):
        sign = -1 if text.startswith("-") else 1
        whole, frac = text.lstrip("-").split(".")
        return sign * (int(whole) * 100 + int(frac))

    problems, sums = [], defaultdict(int)
    with open(paths["general_journal"], encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and list(rows[0]) != JOURNAL_COLUMNS:
        problems.append("journal columns differ from the BC General Journal layout")
    for r in rows:
        sums[r["Document No."]] += cents(r["Amount"])
    problems += [f"journal document {d} sums to {dollars(c)}" for d, c in sums.items() if c]
    with open(paths["ar_invoice"], encoding="utf-8", newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            if int(r["Quantity"]) * cents(r["Unit Price"]) != cents(r["Amount"]):
                problems.append(f"invoice row {n}: Quantity x Unit Price != Amount")
    return problems, len(rows), len(sums)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--payload", help="close payload JSON; default: the built-in mock")
    ap.add_argument("--mapping", default=str(MAPPING))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8")) if args.payload else _mock_payload()
    mapping = load_mapping(args.mapping)
    journal, invoice, control, exceptions = build(payload, mapping)
    bad = unbalanced(journal)
    if bad:
        for doc, c in bad.items():
            print(f"REFUSED: document {doc} does not balance (off by {dollars(c)})", file=sys.stderr)
        print("No journal written. Fix the payload or bc_mapping.csv and run again.", file=sys.stderr)
        return 1
    folder = Path(args.out) / payload["month"]
    paths = write(folder, payload["month"], journal, invoice, control, exceptions, mapping)
    problems, n_lines, n_docs = verify_files(paths)
    print(f"{payload.get('mock', 'payload ' + str(args.payload))}: close {payload['month']}")
    for k, p in paths.items():
        print(f"  wrote {p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p}")
    print(f"  journal: {n_lines} lines in {n_docs} documents, every document sums to 0.00"
          if not problems else "  CHECK FAILED")
    print(f"  invoices: {len({l['Document No.'] for l in invoice})} document(s), {len(invoice)} lines")
    for r in control:
        print(f"  {r['Source']:<13} {r['Path']:<8} revenue in {dollars(r['Revenue In']):>10}  posted "
              f"{dollars(r['Revenue Posted']):>10}  receivable {dollars(r['Receivable Posted']):>10}  "
              f"deposits {dollars(r['Deposits']):>10}  open {dollars(r['Open Balance']):>9}  explained "
              f"{dollars(r['Explained']):>9}  unexplained {dollars(r['Unexplained']):>6}  {r['Status']}")
    print(f"  exceptions: {len(exceptions)} " + str(dict(sorted(
        {k: sum(e['kind'] == k for e in exceptions) for k in {e['kind'] for e in exceptions}}.items()))))
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
