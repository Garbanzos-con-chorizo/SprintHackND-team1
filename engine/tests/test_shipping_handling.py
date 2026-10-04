"""shipping_cents and handling_cents (transaction.md v0.4): what the buyer was charged, kept out of gross."""
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from engine.cli import run
from engine.contract import COLUMNS

ROOT = Path(__file__).resolve().parents[2]


def rows_by_id(tmp_path, files, date="2026-10-02"):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, content in files.items():
        if isinstance(content, str):
            (inbox / name).write_text(content, encoding="utf-8")
        else:
            content.save(inbox / name)
    run(inbox, tmp_path / "out", date)
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        return {r["txn_id"]: r for r in csv.DictReader(f)}


def xlsx(header, rows):
    wb = Workbook()
    wb.active.append(header)
    for r in rows:
        wb.active.append(r)
    return wb


def test_the_columns_are_in_the_contract_and_the_output(tmp_path):
    assert COLUMNS[COLUMNS.index("fee_cents") + 1:COLUMNS.index("fee_cents") + 3] == ["shipping_cents", "handling_cents"]
    run(tmp_path, tmp_path / "out", "2026-10-02")
    header = (tmp_path / "out" / "transactions.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header == COLUMNS


def test_ebay_shipping_and_handling_is_shipping_and_refunds_give_it_back(tmp_path):
    csv_text = (
        '"Transaction report"\n\n'
        '"Transaction creation date","Type","Order number","Buyer username","Item subtotal","Shipping and handling",'
        '"Final Value Fee - fixed","Final Value Fee - variable"\n'
        '"Oct 2, 2026","Order","25-1","buyer1","33.99","5.99","-0.30","-5.30"\n'
        '"Oct 2, 2026","Refund","25-1","buyer1","-24.99","-5.99","--","--"\n'
        '"Oct 2, 2026","Order","25-2","buyer2","10.00","--","-0.30","-1.00"\n')
    r = rows_by_id(tmp_path, {"ebay_transactions_2026-10-02.csv": csv_text})
    assert (r["ebay:25-1:sale"]["gross_cents"], r["ebay:25-1:sale"]["shipping_cents"]) == ("3399", "599")   # shipping is not in gross
    assert (r["ebay:25-1:refund"]["gross_cents"], r["ebay:25-1:refund"]["shipping_cents"]) == ("-2499", "-599")
    assert r["ebay:25-2:sale"]["shipping_cents"] == "0"                                                      # '--' is empty
    assert all(x["handling_cents"] == "0" for x in r.values())


def test_amazon_shipping_credits_sum_over_the_items_of_an_order(tmp_path):
    csv_text = (
        '"date/time","type","order id","sku","product sales","shipping credits","selling fees"\n'
        '"Oct 2, 2026 9:00:00 AM PDT","Order","111-1","A","14.49","3.99","-2.00"\n'
        '"Oct 2, 2026 9:00:00 AM PDT","Order","111-1","B","10.00","3.99","-1.50"\n'
        '"Oct 2, 2026 11:00:00 AM PDT","Refund","111-1","A","-14.49","-3.99","0"\n')
    r = rows_by_id(tmp_path, {"amazon_daterange_2026-10-02.csv": csv_text})
    assert (r["amazon:111-1:sale"]["gross_cents"], r["amazon:111-1:sale"]["shipping_cents"]) == ("2449", "798")
    assert r["amazon:111-1:refund"]["shipping_cents"] == "-399"


def test_upright_has_shipping_charged_and_handling(tmp_path):
    wb = xlsx(["Upright Order ID", "Channel", "Channel Order ID", "Channel Buyer", "Payment Date", "Subtotal",
               "Shipping Charged", "Handling", "Currency"],
              [[1, "Shopgoodwill", 1001, "buyerA", datetime(2026, 10, 2, 12, 0), 20, 10.99, 3, "USD"]])
    r = rows_by_id(tmp_path, {"paid_orders_10-02-2026_10-02-2026.xlsx": wb})["upright:1001:sale"]
    assert (r["gross_cents"], r["shipping_cents"], r["handling_cents"]) == ("2000", "1099", "300")


def test_legacy_shopgoodwill_export_has_shipping_and_handling_fee(tmp_path):
    wb = xlsx(["Order #", "Buyer", "Close Date", "Winning Bid", "Shipping", "Handling Fee", "Order Total"],
              [["SG-1", "rusty", datetime(2026, 10, 2, 9, 0), 39, 10.99, 3, 52.99]])
    r = rows_by_id(tmp_path, {"ShopGoodwill_Orders_2026-10-02.xlsx": wb})["shopgoodwill:SG-1:sale"]
    assert (r["gross_cents"], r["shipping_cents"], r["handling_cents"]) == ("3900", "1099", "300")


def test_cash_monkey_lines_sum_to_the_order_shipping(tmp_path):
    """Cash Monkey pro-rates shipping per unit, so the lines of an order add up to what was charged."""
    wb = xlsx(["Order Date", "Channel", "Order ID", "SKU", "Quantity", "Item Price", "Shipping", "Market Fees", "Currency"],
              [["2026-10-02 15:00:00", "eBay", "E-1", "S1", 1, 10.0, 2.0, 1.5, "USD"],
               ["2026-10-02 15:00:00", "eBay", "E-1", "S1", 1, 10.0, 2.0, 1.5, "USD"]])
    r = rows_by_id(tmp_path, {"orders2023-20261003-001500-1.xlsx": wb})["cashmonkey:E-1:sale"]
    assert (r["gross_cents"], r["shipping_cents"]) == ("2000", "400")


def test_a_refund_column_carries_no_shipping(tmp_path):
    wb = xlsx(["Order #", "Buyer", "Close Date", "Winning Bid", "Shipping", "Refund amount"],
              [["SG-9", "x", datetime(2026, 10, 2, 9, 0), 125, 10.99, 20]])
    r = rows_by_id(tmp_path, {"ShopGoodwill_Orders_2026-10-02.xlsx": wb})
    assert r["shopgoodwill:SG-9:sale"]["shipping_cents"] == "1099"
    assert r["shopgoodwill:SG-9:refund"]["shipping_cents"] == "0"


def test_two_copies_that_differ_only_in_shipping_are_flagged(tmp_path):
    a = ('"date/time","type","order id","product sales","shipping credits"\n'
         '"Oct 2, 2026 9:00:00 AM PDT","Order","111-1","10.00","3.99"\n')
    b = a.replace('"3.99"', '"4.99"')
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "amazon_a.csv").write_text(a, encoding="utf-8")
    (inbox / "amazon_b.csv").write_text(b, encoding="utf-8")
    run(inbox, tmp_path / "out", "2026-10-02")
    warnings = json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8"))
    assert any("shipping_cents differ" in w["reason"] for w in warnings)


@pytest.mark.skipif(not (ROOT / "data/sample/messy_month/expected.json").exists(), reason="sample data not present")
def test_month_totals_equal_the_answer_key_computed_independently_of_the_engine(tmp_path):
    """Orlando's September answer key counts shipping and handling from the generated orders, not from the engine."""
    run(ROOT / "data/sample/messy_month/inbox", tmp_path, "2026-09-30")
    key = json.loads((ROOT / "data/sample/messy_month/expected.json").read_text(encoding="utf-8"))
    key = key["close"]["marketplace_totals_from_files"]
    totals = defaultdict(lambda: [0, 0])
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if "2026-09-01" <= r["business_date"] <= "2026-09-30":
                totals[r["marketplace"]][0] += int(r["shipping_cents"])
                totals[r["marketplace"]][1] += int(r["handling_cents"])
    for marketplace in ("shopgoodwill", "ebay", "amazon"):
        assert totals[marketplace] == [key[marketplace]["shipping_cents"], key[marketplace]["handling_cents"]], marketplace
