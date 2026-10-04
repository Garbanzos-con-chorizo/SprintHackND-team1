"""Constants from docs/contracts/transaction.md. Change the contract first, then this file."""

TIMEZONE = "America/New_York"

COLUMNS = [
    "txn_id",
    "source",
    "marketplace",
    "type",
    "business_date",
    "order_id",
    "customer_id",
    "customer_basis",
    "gross_cents",
    "fee_cents",
    "source_file",
    "source_row",
    # v2, appended so readers of v1 keep working: what the buyer paid for shipping and handling
    # (signed like gross_cents), and units sold (sales only; empty when the export has no unit count).
    "shipping_cents",
    "handling_cents",
    "units",
]

# Marketplaces the pulse expects data for each day (keys of source_status.json). `other` is not
# listed: it appears only on a day it has rows, otherwise the pulse treats it as not configured.
EXPECTED_MARKETPLACES = ["shopgoodwill", "amazon", "ebay"]

WARNING_KINDS = [
    "duplicate",
    "bad_date",
    "bad_amount",
    "missing_column",
    "unsupported_currency",
    "unparseable",
]
