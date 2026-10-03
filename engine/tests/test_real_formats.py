"""Regression tests for column spellings and conventions found when Orlando's real-format samples
(Upright and Cash Monkey .xlsx) first ran through the engine."""
import csv
from datetime import datetime

from openpyxl import Workbook

from engine.cli import run


def rows_of(tmp_path):
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        return {r["order_id"]: r for r in csv.DictReader(f)}


def make_xlsx(path, header, rows):
    wb = Workbook()
    wb.active.append(header)
    for r in rows:
        wb.active.append(r)
    wb.save(path)


def test_upright_payment_date_is_pacific_and_customers_are_orders(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    make_xlsx(inbox / "paid_orders_10-01-2026_10-03-2026.xlsx",
              ["Upright Order ID", "Channel", "Channel Order ID", "Channel Buyer", "Order Items", "Payment Date", "Subtotal", "Currency"],
              [[1, "Shopgoodwill", 1001, "buyerA", 1, datetime(2026, 10, 2, 12, 0, 0), 20, "USD"],     # noon Pacific: Oct 2 Eastern
               [2, "Shopgoodwill", 1002, "buyerA", 1, datetime(2026, 10, 2, 22, 30, 0), 30, "USD"]])   # 10:30 PM Pacific = 1:30 AM Eastern Oct 3
    run(inbox, tmp_path / "out", "2026-10-02")
    rows = rows_of(tmp_path)
    assert rows["1001"]["business_date"] == "2026-10-02"
    assert rows["1002"]["business_date"] == "2026-10-03"
    # buyer id is kept, but staff count rows, so the pulse must count orders
    assert rows["1001"]["customer_id"] == "buyerA" and rows["1001"]["customer_basis"] == "order"


def test_cash_monkey_market_fees_column_and_excel_dates(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    make_xlsx(inbox / "orders2023-20261002-001512-96170.xlsx",
              ["Order Date", "Account", "Channel", "Order ID", "SKU", "Quantity", "Item Price", "Shipping", "Market Fees", "Currency"],
              [[datetime(2026, 10, 2, 1, 30, 0), "276", "eBay", "E-1", "S", 1, 23.99, 0, 3.48, "USD"]])   # 1:30 UTC = 9:30 PM Eastern Oct 1
    run(inbox, tmp_path / "out", "2026-10-01")
    r = rows_of(tmp_path)["E-1"]
    assert (r["gross_cents"], r["fee_cents"], r["business_date"], r["marketplace"]) == ("2399", "348", "2026-10-01", "ebay")
