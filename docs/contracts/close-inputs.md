# Contract: close inputs (C3.1): what the engine hands the month-end close

- **Owner:** Victor (`engine/`). **Consumers:** Dani (`reports.reconcile`, the close), by decision 009.
- **Status:** draft v0.1. `transactions.csv`, `payouts.csv` and `bank.csv` are **built**. The other files are **planned** (their task in brackets) and keep the shapes below unless this file says otherwise.
- **Plan:** `docs/PLAN_PHASE_3.md`, sections 3 and 4.

## The command
```
python -m engine run --inbox <month inbox> --out <dir> --date <month end>
```
It reads every file in the inbox and rewrites every file below in `<dir>`. Each CSV is written even when it has no rows (header only), so a reader can tell "nothing reported" from "the engine did not run". CSV rules are those of `transaction.md`: UTF-8, no BOM, header row, RFC 4180 quoting, `\n` line endings, money in integer USD cents. **A file or row the engine cannot read stays a warning in `warnings.json`, never silent.**

## Files

| File | Status | Columns |
|---|---|---|
| `transactions.csv` | built | `transaction.md` v0.5: v0.4 plus `occurred_at` (V3.1) |
| `payouts.csv` | built (V3.2) | `payout_id`, `marketplace`, `paid_date`, `amount_cents`, `period_from`, `period_to`, `source_file`, `source_row` |
| `bank.csv` | built (V3.2) | `bank_txn_id`, `account`, `posting_date`, `description`, `amount_cents`, `balance_cents`, `source_file`, `source_row` |
| `ledger.csv` | planned (V3.5) | `posting_date`, `document_type`, `document_no`, `gl_account`, `department`, `vendor_no`, `description`, `amount_cents` (debit positive), `source_file`, `source_row`. Every row of the export; the FedEx filter is Dani's rule, not the parser's |
| `statements.csv` | planned (V3.9) | `source` (`goodwillbooks`), `period_from`, `period_to`, `sales_cents`, `fees_cents`, `net_cents`, `paid_date`, `reference`, `source_file`, `source_row` |
| `jewelry.csv` | planned (V3.10) | `item_id`, `order_id`, `sold_date`, `amount_cents`, `supplier` (empty when the lookup does not know the item), `source_file`, `source_row` |
| `source_coverage.json` | planned (V3.3) | `{"month": "2026-09", "sources": {"amazon": {"files": [{"name": "...", "from": "2026-09-01", "to": "2026-09-20", "rows": 0, "simulated": false}], "days_missing": ["2026-09-21", "2026-09-22"]}}}` |

### `payouts.csv`
One row per payout a marketplace report says it sent to the bank. Today: eBay's Transaction report `Payout` rows and Amazon's Date Range report `Transfer` rows. ShopGoodwill has no payout report until V3.8 adds the periodic reports.

| Column | Rule |
|---|---|
| `payout_id` | `<marketplace>:<paid_date>`, e.g. `ebay:2026-09-02`. A second payout on the same day in the same file gets `#2`, `#3`. |
| `marketplace` | `ebay`, `amazon`, and `shopgoodwill` from V3.8. |
| `paid_date` | `YYYY-MM-DD`, **the date as the report writes it**, in the report's own zone. Amazon's `Sep 15, 2026 9:12:44 AM PDT` is `2026-09-15` even when the Eastern date would be different. |
| `amount_cents` | Positive = paid to Goodwill. The reports print payouts as negative (money leaving the marketplace); the sign is flipped. eBay: `Net amount` (or `Gross transaction amount` in the older layout); Amazon: `total`. |
| `period_from`, `period_to` | Empty, unless the report states the period it pays for (ShopGoodwill's periodic report, V3.8). The engine never infers a window: that is the close's rule (D3.1). |
| `source_file`, `source_row` | Where it was read. |

**Overlapping downloads:** the same `payout_id` in two files counts once, and the first copy (in sorted file order) wins. The dropped copy is a `duplicate` warning whose reason starts `same payout as`, and that reason also says when the amounts differ. Payout rows never appear in `transactions.csv`.

### `bank.csv`
Every line of a bank export (`Posting Date`, `Description`, `Debit`, `Credit`, optional `Balance`, optional `Account`): credits, debits, payroll, everything. Which lines are marketplace deposits is the close's rule (`Bank_Text` in `bc_mapping.csv`), not the parser's.

| Column | Rule |
|---|---|
| `bank_txn_id` | `<file>:<row>`. |
| `account` | The file's `Account` column; `OPERATING` when it has none (the sample `bank_activity_*.csv`). V3.7 adds `0101`. |
| `posting_date` | `YYYY-MM-DD`. |
| `description` | As written, trimmed. |
| `amount_cents` | Credit positive, debit negative. A line with neither is a `bad_amount` warning. |
| `balance_cents` | The running balance, or empty if the export has none. |
| `source_file`, `source_row` | Where it was read. |

**Overlapping exports:** two lines are the same line only when the account, date, description, amount **and running balance** all match. The later copy is a `duplicate` warning (`same bank line as ...`). An export without a balance column is never de-duplicated, because two same-day fees of the same amount are two real fees.

## What the engine does not do
- It matches nothing: deposits to payouts, payouts to windows and the FedEx filter are all Dani's (`reports/reconcile.py`).
- It does not read answer keys. The simulated sources (V3.5, V3.7 to V3.10) arrive with `python -m engine fetch --simulate --close-month YYYY-MM --inbox DIR --out DIR2`, which also writes `DIR2/expected_close_sources.json`. That is the answer key for those files, computed from the generated records, never by the parsers.

## Checked on `messy_month` (`engine/tests/test_payouts_bank.py`)
`python -m engine run --inbox data/sample/messy_month/inbox --out out/tmp --date 2026-09-30` writes:
- `payouts.csv` with 31 rows: 29 eBay and 2 Amazon, after the overlapping eBay download is de-duplicated. Each amount equals the answer key's `close.payouts[].amount_cents`. The key's eBay payout of 2026-10-01 is not in any file.
- `bank.csv` with 26 rows: 24 credits and 2 debits.
- `warnings.json` with no `unparseable` entry for `bank_activity_2026-09.csv`.

## Changelog
- v0.1 (2026-10-04, Victor, V3.2): `payouts.csv` and `bank.csv` built; the other shapes copied from the plan's section 4 as planned.
