# Contract: close payload (input of the Business Central export)

- **Owner:** Dani for phase 3 (decision 009; Orlando wrote it and `reports/bc_export.py`). **Producer:** `python -m reports.reconcile` (matching from the raw inbox); `reports/mock_recon.py` builds the same payload from an answer key, for tests. **Consumer:** `python -m reports.bc_export --payload <file>`.
- **Status:** draft v0.4. Verified with the built-in mock (`python -m reports.bc_export`) and the messy month (`reports/tests/test_reconcile.py`, `test_bc_export.py`).

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
  "payouts": [
    { "id": "AMAZON-PAID-0929", "source": "amazon", "paid": "2026-09-29", "deposit": null, "amount_cents": 489384,
      "activity_from": "2026-09-15", "activity_to": "2026-09-28", "files_net_cents": 415074, "gap_cents": 74310,
      "days_missing": ["2026-09-21", "2026-09-22"] }
  ],
  "exceptions": [
    { "kind": "in_transit", "source": "amazon", "amount_cents": 489384, "effect": "open_balance",
      "detail": "AMAZON-PAID-0929: paid 2026-09-29, not in the bank by 2026-09-30" },
    { "kind": "payout_data_gap", "source": "amazon", "amount_cents": -74310, "effect": "open_balance",
      "detail": "AMAZON-PAID-0929 paid $4,893.84 for 2026-09-15 to 2026-09-28; our files hold $4,150.74 for those days. No Amazon report covers 2026-09-21 to 2026-09-22: download it and run the close again" },
    { "kind": "unmatched_deposit", "source": "", "amount_cents": 41237, "effect": "not_posted",
      "detail": "2026-09-17 REMOTE DEPOSIT CAPTURE REF 88213: matches no bank rule; held out of the journal" }
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

## Payouts and their windows (v0.4)
`payouts` lists every payout the close knows of; the export ignores it, the close page and the tests read it. Always present: `id`, `source`, `paid`, `deposit` (the date it reached the bank, or `null`: not there by month end), `amount_cents`. For a source checked payout by payout, each entry also has:

| Field | Meaning |
|---|---|
| `activity_from`, `activity_to` | the days of activity the payout covers, in the source's own payout calendar |
| `files_net_cents` | what our files hold for those days (sales minus refunds, plus shipping and handling, minus fees) |
| `gap_cents` | paid minus files. 0 = the payout is fully explained by our files |
| `days_missing` | days of the window no report covers (from the report file names) |
| `inferred` | `true` when the payout was taken from a bank deposit because the source has no payout report (ShopGoodwill) |

The window comes from the payout's own `period_from` / `period_to` when its report states them, otherwise from two columns of `bc_mapping.csv`: `Payout_Cutoff` (`daily`: paid on D for the activity of D-1; `previous_day`: paid on D for everything since the previous payout, through D-1; `weekly:SUN`: through the last Sunday before D) and `Payout_Timezone` (the calendar those days are counted in). The first payout of the month starts on the 1st: last month's open items are not carried over.

A row's day in that calendar needs the order's time (`occurred_at`, `transaction.md` v0.5), or the Eastern `business_date` when the source pays by Eastern days. A source with neither is not checked payout by payout: its open balance is checked as one figure (the rule of v0.3) and a `no_order_times` exception says so.

## Exception kinds
| Kind | Effect | Meaning |
|---|---|---|
| `in_transit` | `open_balance`, positive | a payout paid in the month that is not in the bank by month end |
| `not_yet_paid_out` | `open_balance`, positive | activity no payout covers yet, to the cent |
| `payout_data_gap` | `open_balance`, negative | a payout paid more than our files hold for its window, and the window has days no report covers. The source reads `INCOMPLETE` |
| `prior_month_payout` | `open_balance`, negative | a payout for activity before the month |
| `payout_mismatch` | `info` | a payout differs from our files for its window and no report is missing. The difference stays unexplained |
| `unmatched_deposit` | `not_posted` | a bank credit no rule assigns to a source |
| `unmapped_source` | `not_posted` | a source with no row in `bc_mapping.csv` (added by the export) |
| `deposit_payout_mismatch` | `info` | a deposit of a source that matches no run of its payouts |
| `missing_report` | `info` | days of the month no report of that source covers |
| `prior_month_refund` | `info` | a refund whose sale is not in this month's files |
| `no_order_times` | `info` | the source could not be checked payout by payout (see above) |
| `residual_unexplained` | `info` | what the one-figure check could not accept |
| `duplicate_rows`, `bad_amount`, `bad_date`, other engine warnings | `info` | rows the engine de-duplicated or rejected |

Two more things since tasks D3.2 and D3.3 of `docs/PLAN_PHASE_3.md`:
- The top-level field `origin` says where the payload came from ("reconciled from the raw inbox", "built-in mock payload", "payload from the ... answer key"). Before v0.4 it was called `mock`, also on a real run; the export still reads the old name.
- Every exception leaves the export with an `owner` and an `action`, the last two columns of `exceptions_<month>.csv`. They come from `reports/config/close_exceptions.csv`, one row per kind and a `*` row for any kind it does not list. **The owners are role names we made up** (Accounting, E-commerce, IT), not Goodwill's; a producer may set `owner` and `action` itself and the export keeps them.
- A marketplace that has rows in the month but no row in `bc_mapping.csv` is in `sources` like any other, so the export reports it as `unmapped_source` instead of the close leaving it out.

## What the export guarantees
- Each source posts through exactly one path from `bc_mapping.csv`: **Journal** (net receivable to a clearing account, sales / refunds / shipping / handling / fees to their accounts) or **Invoice** (one sales invoice to the source's customer, fees as a journal against the customer).
- Each deposit is one journal document: bank debit, clearing (or customer) credit.
- **Every document sums to 0.00, or nothing is written** (exit 1). The files are then read back and re-checked (exit 2 if that fails).
- `control_totals_<month>.csv` per source: revenue in vs posted (must match), receivable posted, deposits, open balance. `Explained` = the `open_balance` exceptions for that source, `Unexplained` = open balance minus explained. Status, worst first: `MISMATCH`: posted revenue differs from the input. `UNEXPLAINED`: money nobody has accounted for. `INCOMPLETE` (v0.4): every cent is accounted for, but the source has a `payout_data_gap`, so its posted revenue is known to be short until the missing report is downloaded. `OPEN`: open but fully explained. `RECONCILED`: open balance 0.

## Changelog
- draft v0.4 (2026-10-04, Dani): payouts carry their window, what the files hold for it and the gap; new exception kinds `payout_data_gap`, `payout_mismatch`, `prior_month_payout`, `no_order_times`; new control status `INCOMPLETE`; `not_yet_paid_out` is now an exact amount, not what is left over; the table of exception kinds. Owner is Dani for phase 3. Additions only: a v0.3 payload still exports the same files.
- draft v0.3: produced by `reports.reconcile` from the raw inbox. Optional extra fields, ignored by the export: `deposits[].matches` (payout ids), `payouts` (every payout read, with its deposit date or null), `stopgaps` (numbers not yet from the engine), `inbox`.
- draft v0.2: exceptions carry source, amount and effect; control totals add Explained / Unexplained. `reports/mock_recon.py` builds a payload from the messy-month answer key.
- draft v0.1: initial, with the mock payload.
