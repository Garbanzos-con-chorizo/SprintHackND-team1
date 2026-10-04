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


# ---------------------------------------------------------------- Goodwill Books statement (V3.9)

STATEMENT_HEADER = ["Statement Period Start", "Statement Period End", "Gross Sales", "Fees", "Net Payment",
                    "Payment Date", "Payment Reference"]
BOOKS_BANK_TEXT = "GOODWILL BOOKS"  # what the bank prints for the statement's payment (our invention)


def books_statement(month: str) -> dict:
    """The Goodwill Books payment statement that arrives during `month`: the PRIOR month's sales, the fees
    kept, and the net amount paid, with the day it was paid (in `month`) and its reference."""
    first, _ = month_span(month)
    prior_last = first - timedelta(days=1)
    rng = _rng(month, "books")
    sales = rng.randrange(240000, 420000)
    fees = round(sales * 0.15)  # a flat commission: our invention
    return {"period_from": prior_last.replace(day=1), "period_to": prior_last, "sales_cents": sales,
            "fees_cents": fees, "net_cents": sales - fees, "paid_date": first.replace(day=rng.randrange(8, 15)),
            "reference": f"GWB-{prior_last:%Y-%m}"}


def books_key(st: dict) -> dict:
    return {"goodwillbooks": {**st, "period_from": st["period_from"].isoformat(),
                              "period_to": st["period_to"].isoformat(), "paid_date": st["paid_date"].isoformat(),
                              "bank_account": BANK_ACCOUNT, "bank_text": BOOKS_BANK_TEXT}}


def simulate_books_statement(month: str, dest_dir: Path) -> tuple[list[Path], dict]:
    st = books_statement(month)
    row = [_us(st["period_from"]), _us(st["period_to"]), _money(st["sales_cents"]), _money(st["fees_cents"]),
           _money(st["net_cents"]), _us(st["paid_date"]), st["reference"]]
    name = f"goodwillbooks_statement_{st['period_from']:%Y-%m}.csv"  # named for the month it reports
    return [_write_csv(dest_dir / name, STATEMENT_HEADER, [row])], books_key(st)


# ---------------------------------------------------------------- bank feed of account 0101 (V3.7)

BANK_ACCOUNT = "0101"  # deck slide 38: "1st Source acct 0101 • GL 10009"
BANK_HEADER = ["Account", "Posting Date", "Description", "Debit", "Credit", "Balance"]
CARRIER_BANK_TEXT = {"osm": "OSM WORLDWIDE", "pb": "PITNEY BOWES", "easypost": "EASYPOST"}  # our invention


def bank_0101_records(month: str) -> list[dict]:
    """The month of the account the carriers are paid from. `kind` says what each line is: a carrier
    (`osm`, `pb`, `easypost`), `goodwillbooks` (the statement's payment, the only credit), or `other`."""
    first, last = month_span(month)
    rng = _rng(month, "bank0101")
    lines = []
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        if day.weekday() == 0:    # OSM is paid every Monday
            lines.append((day, "osm", f"{CARRIER_BANK_TEXT['osm']} DES:POSTAGE ID:{day:%m%d}", -rng.randrange(21000, 46000)))
        if day.weekday() == 3:    # EasyPost every Thursday
            lines.append((day, "easypost", f"{CARRIER_BANK_TEXT['easypost']} DES:LABELS ID:{day:%m%d}", -rng.randrange(6000, 19000)))
        if day.day in (5, 19):    # the postage meter is refilled twice a month
            lines.append((day, "pb", f"{CARRIER_BANK_TEXT['pb']} DES:POSTAGE REFILL ID:{day:%m%d}", -rng.randrange(25000, 60000)))
    st = books_statement(month)
    lines.append((st["paid_date"], "goodwillbooks", f"{BOOKS_BANK_TEXT} DES:PAYMENT ID:{st['reference']}", st["net_cents"]))
    lines.append((first.replace(day=3), "other", "ULINE DES:SHIPPING SUPPLIES", -rng.randrange(8000, 24000)))
    lines.append((first.replace(day=17), "other", "ULINE DES:SHIPPING SUPPLIES", -rng.randrange(8000, 24000)))
    lines.append((last, "other", "MONTHLY SERVICE CHARGE", -1500))
    lines.sort(key=lambda line: (line[0], line[2]))
    balance = 2500000 + rng.randrange(0, 500000)  # opening balance, enough for the month
    records = []
    for day, kind, text, cents in lines:
        balance += cents
        records.append({"kind": kind, "posting_date": day, "description": text, "amount_cents": cents,
                        "balance_cents": balance})
    return records


def bank_0101_key(records: list[dict]) -> dict:
    carriers = {name: {"bank_text": text,
                       "cents": -sum(r["amount_cents"] for r in records if r["kind"] == name),
                       "payments": sum(r["kind"] == name for r in records)}
                for name, text in CARRIER_BANK_TEXT.items()}
    return {"carriers": {"bank_account": BANK_ACCOUNT, **carriers,
                         "total_cents": sum(c["cents"] for c in carriers.values()),
                         "lines": len(records), "other_debits": sum(r["kind"] == "other" for r in records)}}


def simulate_bank_0101(month: str, dest_dir: Path) -> tuple[list[Path], dict]:
    records = bank_0101_records(month)
    rows = [[BANK_ACCOUNT, _us(r["posting_date"]), r["description"],
             _money(-r["amount_cents"]) if r["amount_cents"] < 0 else "",
             _money(r["amount_cents"]) if r["amount_cents"] > 0 else "", _money(r["balance_cents"])] for r in records]
    path = _write_csv(dest_dir / f"bank_activity_{BANK_ACCOUNT}_{month}.csv", BANK_HEADER, rows)
    return [path], bank_0101_key(records)
