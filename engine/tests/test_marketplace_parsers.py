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


# --- Layouts seen in the team's sample exports (data/sample on the o/phase1-data branch) ---

EBAY_TXN_REPORT = (
    '﻿"Transaction report"\r\n"Date range: Oct 1, 2026 - Oct 2, 2026"\r\n"All amounts in USD"\r\n\r\n'
    '"Transaction creation date","Type","Order number","Buyer username","Item subtotal",'
    '"Final Value Fee - fixed","Final Value Fee - variable","Gross transaction amount","Payout currency"\r\n'
    '"Oct 1, 2026","Order","25-1","happydeals","33.99","-0.30","-5.30","42.36","USD"\r\n'
    '"Oct 2, 2026","Refund","25-1","happydeals","-24.99","--","--","-32.73","USD"\r\n'
    '"Oct 1, 2026","Payout","--","--","--","--","--","-441.65","USD"\r\n'
)

AMAZON_DATE_RANGE = (
    '"Includes Amazon Marketplace, Fulfillment by Amazon (FBA), and Amazon Webstore transactions"\n'
    '"Date range: Oct 1, 2026 12:00:00 AM PDT - Oct 2, 2026 11:59:59 PM PDT"\n\n'
    '"date/time","settlement id","type","order id","sku","product sales","selling fees","total"\n'
    '"Oct 1, 2026 9:33:00 PM PDT","1","Order","111-1","BK-1","14.49","-4.57","13.91"\n'
    '"Oct 1, 2026 9:33:00 PM PDT","1","Order","111-1","BK-2","1,000.00","-4.57","13.91"\n'
    '"Oct 2, 2026 9:12:44 AM PDT","1","Transfer","","","0","0","-1,052.64"\n'
)


def test_ebay_transaction_report_layout(tmp_path):
    rows, warnings = run_inbox(tmp_path, {"ebay_transactions_2026-10-02.csv": EBAY_TXN_REPORT.replace("\r\n", "\n")})
    assert warnings == []  # '--' is empty; the Payout row goes to payouts.csv, not to transactions
    got = {r["txn_id"]: (r["gross_cents"], r["fee_cents"], r["business_date"]) for r in rows}
    assert got == {
        "ebay:25-1:sale": ("3399", "560", "2026-10-01"),      # Item subtotal, not the shipping-inclusive gross
        "ebay:25-1:refund": ("-2499", "0", "2026-10-02"),     # refunds count on the day issued
    }


def test_ebay_report_with_bom_and_crlf_bytes(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "ebay_transactions_2026-10-02.csv").write_bytes(EBAY_TXN_REPORT.encode("utf-8"))
    run(inbox, tmp_path / "out", "2026-10-02")
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 2


def test_amazon_date_range_pacific_time_items_and_transfer(tmp_path):
    rows, warnings = run_inbox(tmp_path, {"amazon_daterange_2026-10-02.csv": AMAZON_DATE_RANGE})
    assert warnings == []  # the Transfer row goes to payouts.csv, not to transactions
    assert len(rows) == 1
    r = rows[0]
    assert r["business_date"] == "2026-10-02"        # 9:33 PM PDT Oct 1 is 12:33 AM EDT Oct 2
    assert r["gross_cents"] == "101449"              # two items of one order summed, thousands separator read
    assert r["fee_cents"] == "914"
    assert (r["customer_id"], r["customer_basis"]) == ("", "order")


def test_shopgoodwill_xlsx_with_title_rows_order_hash_and_mixed_dates(tmp_path):
    from datetime import datetime as dt
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(["ShopGoodwill.com - Seller Order Export"])
    ws.append(["Generated: 10/3/2026 6:05 AM"])
    ws.append([])
    ws.append(["Order #", "Item #", "Buyer", "Close Date", "Winning Bid", "Shipping", "Order Total", "Payment Status"])
    ws.append(["SG-1", "1", "rustyhound", "10/1/26 12:02 AM", 39, 10.99, 51.99, "Paid"])
    ws.append(["SG-2", "2", "sunnybear", dt(2026, 10, 1, 3, 22, 9), "$27.00", 10.99, 39.99, "Paid"])
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    wb.save(inbox / "ShopGoodwill_Orders_2026-10-01.xlsx")
    run(inbox, tmp_path / "out", "2026-10-01")
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        got = {r["order_id"]: (r["gross_cents"], r["business_date"]) for r in csv.DictReader(f)}
    assert got == {"SG-1": ("3900", "2026-10-01"), "SG-2": ("2700", "2026-10-01")}


# --- P-V5: the same transaction in two files counts once ---

def test_overlapping_downloads_count_once_and_are_logged(tmp_path):
    first = EBAY_TXN_REPORT.replace("\r\n", "\n")
    # a later re-download that overlaps the first and adds one new order
    second = first.rstrip("\n") + '\n"Oct 2, 2026","Order","25-2","newbuyer","10.00","-0.30","-1.00","12.00","USD"\n'
    rows, warnings = run_inbox(tmp_path, {
        "ebay_transactions_2026-10-02.csv": first,
        "ebay_transactions_2026-10-02 (1).csv": second,
    })
    assert sorted(r["txn_id"] for r in rows) == ["ebay:25-1:refund", "ebay:25-1:sale", "ebay:25-2:sale"]
    dupes = [w for w in warnings if w["kind"] == "duplicate"]
    # the sale, the refund and the payout repeated in the overlap (the payout goes to payouts.csv)
    assert len(dupes) == 3 and all("differ" not in w["reason"] for w in dupes)
    assert sum("same payout" in w["reason"] for w in dupes) == 1
    assert all(w["source_file"] == "ebay_transactions_2026-10-02.csv" or "(1)" in w["source_file"] for w in dupes)


def test_conflicting_copies_keep_first_and_say_so(tmp_path):
    a = EBAY_TXN_REPORT.replace("\r\n", "\n")
    b = a.replace('"33.99"', '"34.99"')  # same order, different amount
    rows, warnings = run_inbox(tmp_path, {"ebay_a.csv": a, "ebay_b.csv": b})
    sale = next(r for r in rows if r["txn_id"] == "ebay:25-1:sale")
    assert sale["gross_cents"] == "3399" and sale["source_file"] == "ebay_a.csv"
    assert any("gross_cents differ" in w["reason"] for w in warnings)
