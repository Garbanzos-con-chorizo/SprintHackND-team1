"""Amazon Seller Central exports: the Orders report and the Payments transaction report.

Checked against the team's synthetic Date Range report (modeled on Amazon's public layout), not a real
Goodwill file. Timestamps carry a zone name (PDT) and are converted to Eastern; Transfer rows are
skipped; one row per item, so a multi-item order is summed into one row. When a real file arrives,
correct the aliases below (nothing else needs to change). Amazon only
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
    shipping = ("shipping credits", "shipping-price")
    row_type = ("type", "transaction type")
    skip_types = ("transfer",)
    currency = ("currency",)
