import csv
import json
from datetime import date, datetime

import pytest

from engine.clean import buyer_key, parse_business_date, parse_money
from engine.cli import run
from engine.contract import COLUMNS


@pytest.mark.parametrize("text,cents", [
    ("$1,234.50", 123450), ("1234.5", 123450), ("(12.00)", -1200), ("12.00-", -1200), ("-$3.10", -310),
    ("USD 3.10", 310), ("5,00", 500), ("1,234", 123400), (5, 500), (5.1, 510), ("0", 0),
])
def test_parse_money(text, cents):
    assert parse_money(text) == cents


@pytest.mark.parametrize("bad", ["", "abc", "12.3.4", None])
def test_parse_money_rejects(bad):
    with pytest.raises(ValueError):
        parse_money("" if bad is None else bad)


@pytest.mark.parametrize("text,expected", [
    ("2026-10-02", "2026-10-02"), ("10/2/26", "2026-10-02"), ("10/02/2026 14:03", "2026-10-02"),
    ("Oct 2, 2026", "2026-10-02"), ("2-Oct-26", "2026-10-02"), ("2026-10-02 14:03:00", "2026-10-02"),
    # 02:30 UTC on Oct 3 is still the evening of Oct 2 in Eastern time
    ("2026-10-03T02:30:00Z", "2026-10-02"), ("2026-10-02T23:30:00-04:00", "2026-10-02"),
    (datetime(2026, 10, 2, 14, 3), "2026-10-02"), (date(2026, 10, 2), "2026-10-02"),
])
def test_parse_business_date(text, expected):
    assert parse_business_date(text) == expected


@pytest.mark.parametrize("bad", ["", "yesterday", "13/45/2026"])
def test_parse_business_date_rejects(bad):
    with pytest.raises(ValueError):
        parse_business_date(bad)


def test_buyer_key_hashes_emails_only():
    assert buyer_key(" sgbidder77 ") == "sgbidder77"
    h = buyer_key("Someone@Example.com")
    assert h.startswith("h_") and "@" not in h and h == buyer_key("someone@example.com")


def run_inbox(tmp_path, files):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, text in files.items():
        (inbox / name).write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    run(inbox, out, "2026-10-02")
    with open(out / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    warnings = json.loads((out / "warnings.json").read_text(encoding="utf-8"))
    return rows, warnings


EBAY = (
    "Transaction creation date,Type,Order number,Buyer username,Gross transaction amount,"
    "Final Value Fee - fixed,Final Value Fee - variable,Currency\n"
    "\"Oct 2, 2026\",Order,12-34567-89012,buyer_ab12,$25.99,$0.30,$3.06,USD\n"
    "\"Oct 2, 2026\",Refund,12-34567-89012,buyer_ab12,($25.99),,,USD\n"
    "\"Oct 2, 2026\",Order,12-34567-89013,buyer_cd34,18.50,0.30,1.94,USD\n"
    "\"Oct 2, 2026\",Order,12-34567-89013,buyer_cd34,18.50,0.30,1.94,USD\n"   # exact duplicate row
    "not a date,Order,12-34567-89014,buyer_ef56,9.99,,,USD\n"                  # bad date
    "\"Oct 2, 2026\",Order,12-34567-89015,buyer_gh78,9.99,,,EUR\n"             # not USD
)

AMAZON = (
    "amazon-order-id\tpurchase-date\tbuyer-email\titem-price\tcurrency\n"
    "114-1\t2026-10-03T02:30:00Z\tjane@example.com\t32.99\tUSD\n"
    "114-2\t2026-10-02T11:30:00-04:00\t\t10.00\tUSD\n"
    "114-2\t2026-10-02T11:30:00-04:00\t\t4.99\tUSD\n"      # second line of the same order
)

SHOPGOODWILL = (
    "Order ID,Paid date,Winning bid,Buyer ID,Refund amount\n"
    "SG-883210,10/2/2026,\"$84.00\",sgbidder77,\n"
    "SG-883211,10/2/2026,\"$125.00\",sgbidder12,$20.00\n"
)


def test_ebay_sale_refund_fees_and_warnings(tmp_path):
    rows, warnings = run_inbox(tmp_path, {"ebay_2026-10-02.csv": EBAY})
    by_id = {r["txn_id"]: r for r in rows}
    assert set(by_id) == {"ebay:12-34567-89012:sale", "ebay:12-34567-89012:refund", "ebay:12-34567-89013:sale"}
    sale = by_id["ebay:12-34567-89012:sale"]
    assert (sale["gross_cents"], sale["fee_cents"], sale["marketplace"], sale["business_date"]) == ("2599", "336", "ebay", "2026-10-02")
    assert (sale["customer_id"], sale["customer_basis"]) == ("buyer_ab12", "buyer")
    assert by_id["ebay:12-34567-89012:refund"]["gross_cents"] == "-2599"
    assert sorted(w["kind"] for w in warnings) == ["bad_date", "duplicate", "unsupported_currency"]
    assert {w["source_row"] for w in warnings} == {4, 5, 6}


def test_amazon_hashes_email_converts_timezone_and_merges_lines(tmp_path):
    rows, warnings = run_inbox(tmp_path, {"amazon_orders.txt": AMAZON})
    by_id = {r["order_id"]: r for r in rows}
    assert warnings == []
    assert by_id["114-1"]["business_date"] == "2026-10-02"          # 02:30 UTC Oct 3 = Oct 2 Eastern
    assert by_id["114-1"]["customer_id"].startswith("h_") and "@" not in by_id["114-1"]["customer_id"]
    assert by_id["114-2"]["gross_cents"] == "1499"                   # two lines, one order, one row
    assert (by_id["114-2"]["customer_id"], by_id["114-2"]["customer_basis"]) == ("", "order")
    assert len(rows) == 2


def test_shopgoodwill_refund_column_creates_refund_row(tmp_path):
    rows, warnings = run_inbox(tmp_path, {"shopgoodwill_oct02.csv": SHOPGOODWILL})
    got = {r["txn_id"]: r["gross_cents"] for r in rows}
    assert got == {
        "shopgoodwill:SG-883210:sale": "8400",
        "shopgoodwill:SG-883211:sale": "12500",
        "shopgoodwill:SG-883211:refund": "-2000",
    }
    assert warnings == []


def test_shopgoodwill_columns_alone_do_not_claim_a_file(tmp_path):
    rows, warnings = run_inbox(tmp_path, {"download.csv": SHOPGOODWILL})
    assert rows == [] and warnings[0]["kind"] == "unparseable"


def test_all_three_together_and_output_columns(tmp_path):
    rows, warnings = run_inbox(tmp_path, {
        "ebay_2026-10-02.csv": EBAY, "amazon_orders.txt": AMAZON, "shopgoodwill_oct02.csv": SHOPGOODWILL,
    })
    assert {r["marketplace"] for r in rows} == {"ebay", "amazon", "shopgoodwill"}
    assert all(set(r) == set(COLUMNS) for r in rows)
    assert len(rows) == 3 + 2 + 3


def test_missing_required_column_rejects_file_with_warning(tmp_path):
    rows, warnings = run_inbox(tmp_path, {"ebay_x.csv": "Order number,Buyer username,Foo\n1,a,b\n"})
    assert rows == []
    assert [w["kind"] for w in warnings] == ["missing_column"]
