"""Amazon Seller Central exports: the Orders report and the Payments transaction report.

COLUMN NAMES ARE UNVERIFIED GUESSES from how Amazon lays these reports out; we have no real sample
yet. When a real file arrives, correct the aliases below (nothing else needs to change). Amazon only
exposes a buyer email in some reports; it is hashed before it reaches customer_id. The Payments
report lists fees as negative numbers; they are stored as positive costs.
"""
from ..parsers import register
from ._common import OrderReportParser


@register
class Amazon(OrderReportParser):
    source = "amazon"
    marketplace = "amazon"
    filename_patterns = (r"amazon",)
    required_columns = (("amazon order id", "order id"), ("purchase date", "date time"))

    order_id = ("amazon-order-id", "order-id", "Order ID")
    date = ("purchase-date", "date/time", "Order date")
    gross = ("item-price", "product sales", "Item subtotal")
    fees = ("selling fees", "referral fee", "fba fees", "other transaction fees")
    buyer = ("buyer-email", "buyer email")
    row_type = ("type", "transaction type")
    currency = ("currency",)
