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
]

# Sources the pulse expects a file from each day (keys of source_status.json).
EXPECTED_SOURCES = ["shopgoodwill", "amazon", "ebay"]

WARNING_KINDS = [
    "duplicate",
    "bad_date",
    "bad_amount",
    "missing_column",
    "unsupported_currency",
    "unparseable",
]
