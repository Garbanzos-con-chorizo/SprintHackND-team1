"""ShopGoodwill seller orders export.

COLUMN NAMES ARE UNVERIFIED GUESSES: nothing in the brief or deck shows this export, so these are
the most likely names. ShopGoodwill pays out one amount per item (no marketplace fee column is
assumed). Correct the aliases below when a real file arrives; nothing else needs to change.
"""
from ..parsers import register
from ._common import OrderReportParser


@register
class ShopGoodwill(OrderReportParser):
    source = "shopgoodwill"
    marketplace = "shopgoodwill"
    filename_patterns = (r"shop.?goodwill", r"\bsgw?\b", r"sg_")
    required_columns = (("order id", "order number", "invoice number", "invoice"),)

    def detect(self, table):
        # Its columns are generic ("Order ID", "Amount"), so columns alone must never claim a file:
        # require the file name too (columns + name scores 3, columns alone scores 2).
        score = super().detect(table)
        return score if score >= 3 else 0

    order_id = ("Order ID", "Order number", "Invoice number", "Invoice")
    date = ("Paid date", "Closing date", "Date sold", "Order date", "Date")
    gross = ("Winning bid", "Final price", "Item total", "Item price", "Amount")
    buyer = ("Buyer ID", "Bidder", "Winner", "Buyer")
    refund_amount = ("Refund amount", "Refunded")
    currency = ("Currency",)
