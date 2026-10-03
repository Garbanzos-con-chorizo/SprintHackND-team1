"""eBay Seller Hub exports: the Orders report and the Transaction report.

COLUMN NAMES ARE UNVERIFIED GUESSES from how eBay lays these reports out; we have no real sample
yet. When a real file arrives, correct the aliases below (nothing else needs to change) and update
the sample test. The Transaction report has a Type column (Order / Refund); the Orders report doesn't.
"""
from ..parsers import register
from ._common import OrderReportParser


@register
class Ebay(OrderReportParser):
    source = "ebay"
    marketplace = "ebay"
    filename_patterns = (r"ebay",)
    required_columns = (("order number", "order id"), "buyer username")  # 'Buyer ID' is too generic to detect on

    order_id = ("Order number", "Order ID")
    date = ("Sale Date", "Transaction creation date", "Order creation date", "Date")
    gross = ("Item subtotal", "Gross transaction amount", "Item price", "Order total")
    fees = ("Final Value Fee - fixed", "Final Value Fee - variable", "Final Value Fee", "Regulatory operating fee")
    buyer = ("Buyer username", "Buyer ID")
    row_type = ("Type", "Transaction type")
    currency = ("Currency", "Transaction currency")
