"""Upright "Paid orders" report: the probable nightly source for ShopGoodwill (deck slides 21-26).

What the deck shows (docs/contracts/source-formats.md): one row per order, header in row 1, a `Channel`
column reading "Shopgoodwill", `Channel Order ID`, `Channel Buyer`, `Subtotal` (merchandise), `Total`
(subtotal + shipping + handling + tax), `Currency`. File name pattern `paid_orders_<MM-DD-YYYY>_<MM-DD-YYYY>`.

GUESSES, to confirm with a real file: the exact header spelling (several are cut off in the screenshot),
whether a paid-date column exists (none is visible, so the date falls back to the day in the file name,
which is the day the report was run for), and which fee column is a marketplace fee. Revenue is
`Subtotal`; shipping, handling and tax are not revenue. Only `Shopgoodwill` rows are taken: other
channels in an Upright export belong to other sources and would otherwise be counted twice.
"""
from ..parsers import register
from ._common import OrderReportParser


@register
class Upright(OrderReportParser):
    source = "upright"
    marketplace = "other"
    filename_patterns = (r"paid.?orders", r"upright")
    required_columns = ("upright order id", "channel order id", "subtotal")
    filename_date = r"(\d{2})-(\d{2})-(\d{4})"

    order_id = ("Channel Order ID", "Upright Order ID")
    date = ("Paid At", "Paid Date", "Order Date")
    gross = ("Subtotal",)
    fees = ("Final Value Fee",)
    buyer = ("Channel Buyer",)
    currency = ("Currency",)
    channel = ("Channel",)
    channel_marketplaces = {"shopgoodwill": "shopgoodwill"}
    strict_channels = True
