# Contract: close payload (input of the Business Central export)

- **Owner:** Orlando (`reports/bc_export.py`) until the phase 3 split (decision 007, Orlando's response). **Producer:** reconciliation (D2-D5), whoever builds it. **Consumer:** `python -m reports.bc_export --payload <file>`.
- **Status:** draft. Verified with the built-in mock (`python -m reports.bc_export`, 7 tests in `reports/tests/test_bc_export.py`).

## Shape
```json
{
  "month": "2026-09",
  "posting_date": "2026-09-30",
  "sources": {
    "ebay": { "sales_cents": 2005232, "refunds_cents": 9497, "shipping_cents": 98460, "handling_cents": 0, "fees_cents": 310373 }
  },
  "deposits": [
    { "date": "2026-09-08", "source": "ebay", "amount_cents": 445000, "reference": "EBAY PAYOUT 0908" }
  ],
  "exceptions": [
    { "kind": "in_transit", "source": "amazon", "amount_cents": 415074, "effect": "open_balance",
      "detail": "AMZN-0928 for 2026-09-15 to 2026-09-28: paid 2026-09-29, reaches the bank after month end" },
    { "kind": "unmatched_deposit", "source": "", "amount_cents": 41237, "effect": "not_posted",
      "detail": "2026-09-17 REMOTE DEPOSIT CAPTURE REF 88213: no payout matches it" }
  ]
}
```
- Integer cents. `refunds_cents` and `fees_cents` are **positive** amounts (the export signs them).
- `sources` keys must match `Source` in `reports/config/bc_mapping.csv`; an unknown source becomes an `unmapped_source` exception and is not posted.
- `deposits` are bank deposits **already matched** to a source (one deposit covering several payouts of the same source is one entry). A deposit nobody could match goes in `exceptions`, not here.
- `exceptions` go to `exceptions_<month>.csv`; nothing in them is posted. `effect` says what each one does:
  `open_balance` explains part of that source's open balance (`amount_cents`, signed: money still owed is
  positive, a payout for activity missing from our files is negative), `not_posted` is held out of BC,
  `info` needs a look but changes no number.

## What the export guarantees
- Each source posts through exactly one path from `bc_mapping.csv`: **Journal** (net receivable to a clearing account, sales / refunds / shipping / handling / fees to their accounts) or **Invoice** (one sales invoice to the source's customer, fees as a journal against the customer).
- Each deposit is one journal document: bank debit, clearing (or customer) credit.
- **Every document sums to 0.00, or nothing is written** (exit 1). The files are then read back and re-checked (exit 2 if that fails).
- `control_totals_<month>.csv` per source: revenue in vs posted (must match), receivable posted, deposits, open balance. `Explained` = the `open_balance` exceptions for that source, `Unexplained` = open balance minus explained. `RECONCILED`: open balance 0. `OPEN`: open but fully explained. `UNEXPLAINED`: money nobody has accounted for. `MISMATCH`: posted revenue differs from the input.

## Changelog
- draft v0.2: exceptions carry source, amount and effect; control totals add Explained / Unexplained. `reports/mock_recon.py` builds a payload from the messy-month answer key.
- draft v0.1: initial, with the mock payload.
