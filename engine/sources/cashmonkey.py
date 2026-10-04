"""Cash Monkey "Orders Report": the probable nightly source for eBay, Amazon and Goodwill Books (slides 27-30).

What the deck shows: a CSV named like `orders2023-20261001-132256-96170.csv`, "one line per unit" with
marketplace fees pro-rated to each unit, a Channel selector (Amazon-MF, eBay, Goodwillbooks), order dates
in UTC (so a late-evening Eastern sale carries the next UTC date), non-USD converted to USD.

THE COLUMN NAMES ARE GUESSES: the deck never shows this CSV. Replace the aliases below with a real file's
header (nothing else needs to change). A multi-unit order is several rows with the same order id and is
summed into one row. A refund is assumed to be a row with a negative item price.
"""
from ..parsers import register
from ._common import OrderReportParser


@register
class CashMonkey(OrderReportParser):
    source = "cashmonkey"
    marketplace = "other"
    filename_patterns = (r"orders2023", r"cash.?monkey")
    required_columns = ("order id", "channel", "item price", ("order date utc", "order date"))

    order_id = ("Order ID",)
    date = ("Order Date (UTC)", "Order Date")
    gross = ("Item Price",)
    fees = ("Marketplace Fees", "Market Fees")
    shipping = ("Shipping", "Shipping Price")   # pro-rated per unit by Cash Monkey, so the lines of an order sum to the total
    currency = ("Currency",)
    channel = ("Channel",)
    channel_marketplaces = {"amazon mf": "amazon", "amazon": "amazon", "ebay": "ebay", "goodwillbooks": "other"}
    date_assume_tz = "UTC"
    identical_rows_are_duplicates = False  # one line per unit: two identical units are two units
