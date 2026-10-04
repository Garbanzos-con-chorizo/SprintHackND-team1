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
    # v0.5 (V3.1), appended: the moment of the sale or refund, ISO 8601 with its offset; empty when the
    # export gives only a date or the day comes from the file name. The close rebuilds Pacific payout days.
    "occurred_at",
]

# Close inputs (docs/contracts/close-inputs.md, V3.2). payouts.csv: money a marketplace says it sent to the
# bank, positive = paid to Goodwill; period_from/period_to only when the report states the period.
PAYOUT_COLUMNS = ["payout_id", "marketplace", "paid_date", "amount_cents", "period_from", "period_to",
                  "source_file", "source_row"]
# bank.csv: every line of a bank export, credits positive, debits negative.
BANK_COLUMNS = ["bank_txn_id", "account", "posting_date", "description", "amount_cents", "balance_cents",
                "source_file", "source_row"]

# The close's other tables (close-inputs.md): file name without .csv -> columns. Every run writes each
# of them, header only when no file fed it.
# ledger.csv (V3.5): every row of a Business Central G/L entries export, debit positive.
LEDGER_COLUMNS = ["entry_no", "posting_date", "document_type", "document_no", "gl_account", "department",
                  "vendor_no", "description", "amount_cents", "source_file", "source_row"]
CLOSE_TABLES = {"ledger": LEDGER_COLUMNS}

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
    "missing_supplier",  # close inputs: a jewelry item the supplier lookup does not know
]
