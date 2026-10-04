"""ShopGoodwill seller orders export.

COLUMN NAMES ARE STILL GUESSES: nothing in the brief or deck shows this export. They match the team's
synthetic export (Orlando's guess, 3 title rows, 'Order #', 'Close Date', 'Winning Bid'), not a real file. ShopGoodwill pays out one amount per item (no marketplace fee column is
assumed). Correct the aliases below when a real file arrives; nothing else needs to change.
"""
from ..parsers import register
from ._common import OrderReportParser


@register
class ShopGoodwill(OrderReportParser):
    source = "shopgoodwill"
    marketplace = "shopgoodwill"
    filename_patterns = (r"shop.?goodwill", r"\bsgw?\b", r"sg_")
    required_columns = (("order id", "order number", "order", "invoice number", "invoice"),)  # 'Order #' normalizes to 'order'

    def detect(self, table):
        # Its columns are generic ("Order ID", "Amount"), so columns alone must never claim a file:
        # require the file name too (columns + name scores 3, columns alone scores 2).
        score = super().detect(table)
        return score if score >= 3 else 0

    order_id = ("Order #", "Order ID", "Order number", "Invoice number", "Invoice")
    date = ("Close Date", "Paid date", "Closing date", "Date sold", "Order date", "Date")
    gross = ("Winning bid", "Final price", "Item total", "Item price", "Amount")
    buyer = ("Buyer ID", "Bidder", "Winner", "Buyer")
    shipping = ("Shipping",)
    handling = ("Handling Fee", "Handling")
    refund_amount = ("Refund amount", "Refunded")
    currency = ("Currency",)
