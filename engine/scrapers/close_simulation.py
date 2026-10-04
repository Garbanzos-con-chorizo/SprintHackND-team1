"""Simulated month-end sources: what each API we assume (docs/ASSUMPTIONS.md, section 2c) would deliver.

Nobody on the team has seen these sources, so EVERY LAYOUT AND EVERY VALUE HERE IS OURS: synthetic, seeded
by the month, so the same month always gives the same files. `python -m engine fetch --simulate
--close-month YYYY-MM` writes them into the inbox, where the normal pipeline reads them (engine/sources/).

Each source has two halves, kept apart on purpose:
  - the records (`*_records`), generated here, each tagged with what it is;
  - the answer key (`*_key`), computed from those tags, never by a parser and never by the rule the
    close applies. A test then checks that parser + rule on the written file give the key.
The only values that are Goodwill's are the four FedEx codes of deck slide 38 (FEDEX below).
"""
import calendar
import csv
import random
from datetime import date, timedelta
from pathlib import Path

# Deck slide 38: "BC GL 40356 • Dept 180 • V00122 • net BNKDEPOSIT refunds".
FEDEX = {"gl_account": "40356", "department": "180", "vendor_no": "V00122"}
REFUND_DOCUMENT_PREFIX = "BNKDEPOSIT"


def month_span(month: str) -> tuple[date, date]:
    year, mon = int(month[:4]), int(month[5:7])
    return date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])


def _rng(month: str, what: str) -> random.Random:
    return random.Random(f"{what}:{month}")  # a text seed is stable across runs and machines


def _us(day: date) -> str:
    return f"{day:%m/%d/%Y}"


def _money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def _write_csv(path: Path, header: list[str], rows: list[list]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


# ---------------------------------------------------------------- Business Central ledger (FedEx, V3.5)

LEDGER_HEADER = ["Entry No.", "Posting Date", "Document Type", "Document No.", "G/L Account No.",
                 "Department Code", "Vendor No.", "Description", "Amount"]


def ledger_records(month: str) -> list[dict]:
    """The month's G/L entries around shipping. `kind` says what each one is: `fedex_charge`, `fedex_refund`
    (a refund that came back as a bank deposit), or `other` (rows the FedEx filter must leave out: another
    vendor, another department, another account)."""
    first, last = month_span(month)
    rng = _rng(month, "ledger")
    records = []

    def add(day, kind, doc_type, doc_no, gl, dept, vendor, text, cents):
        records.append({"kind": kind, "posting_date": day, "document_type": doc_type, "document_no": doc_no,
                        "gl_account": gl, "department": dept, "vendor_no": vendor, "description": text,
                        "amount_cents": cents})

    invoice = 108200 + int(month[5:7]) * 100
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        if day.weekday() in (1, 4):  # FedEx bills twice a week
            invoice += 1
            add(day, "fedex_charge", "Invoice", f"PI-{invoice}", *FEDEX.values(),
                f"FedEx shipping charges through {day:%b} {day.day}", rng.randrange(18000, 52000))
    for day_no in sorted(rng.sample(range(5, last.day - 1), 3)):
        day = first.replace(day=day_no)
        add(day, "fedex_refund", "", f"{REFUND_DOCUMENT_PREFIX}-{day:%m%d}", *FEDEX.values(),
            "FedEx refund received (bank deposit)", -rng.randrange(1200, 6500))
    others = [
        ("Invoice", "40356", "180", "V00087", "UPS shipping charges"),            # another vendor
        ("Invoice", "40356", "110", "V00122", "FedEx shipping charges, stores"),  # another department
        ("Invoice", "60510", "180", "V00122", "FedEx Office printing"),           # another account
        ("Invoice", "40356", "180", "V00087", "UPS shipping charges"),
        ("Invoice", "61200", "180", "V00310", "Packaging supplies"),
    ]
    for doc_type, gl, dept, vendor, text in others:
        invoice += 1
        add(first.replace(day=rng.randrange(2, last.day)), "other", doc_type, f"PI-{invoice}", gl, dept, vendor, text,
            rng.randrange(4000, 30000))
    records.sort(key=lambda r: (r["posting_date"], r["document_no"]))
    for i, r in enumerate(records, start=1):
        r["entry_no"] = f"{first:%y%m}{i:04d}"
    return records


def ledger_key(records: list[dict]) -> dict:
    charges = sum(r["amount_cents"] for r in records if r["kind"] == "fedex_charge")
    refunds = -sum(r["amount_cents"] for r in records if r["kind"] == "fedex_refund")
    return {"fedex": {**FEDEX, "refund_document_prefix": REFUND_DOCUMENT_PREFIX,
                      "charges_cents": charges, "refunds_cents": refunds, "net_cents": charges - refunds,
                      "entries": sum(r["kind"] != "other" for r in records),
                      "entries_left_out": sum(r["kind"] == "other" for r in records)}}


def simulate_ledger(month: str, dest_dir: Path) -> tuple[list[Path], dict]:
    records = ledger_records(month)
    rows = [[r["entry_no"], _us(r["posting_date"]), r["document_type"], r["document_no"], r["gl_account"],
             r["department"], r["vendor_no"], r["description"], _money(r["amount_cents"])] for r in records]
    return [_write_csv(dest_dir / f"bc_gl_entries_{month}.csv", LEDGER_HEADER, rows)], ledger_key(records)
