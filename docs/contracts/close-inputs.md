# Contract: close inputs (C3.1): what the engine hands the month-end close

- **Owner:** Victor (`engine/`). **Consumers:** Dani (`reports.reconcile`, the close), by decision 009.
- **Status:** draft v0.3. `transactions.csv`, `payouts.csv`, `bank.csv`, `source_coverage.json` and `ledger.csv` are **built**, and so is the command that delivers the simulated month-end sources. The other files are **planned** (their task in brackets) and keep the shapes below unless this file says otherwise.
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
| `ledger.csv` | built (V3.5) | `entry_no`, `posting_date`, `document_type`, `document_no`, `gl_account`, `department`, `vendor_no`, `description`, `amount_cents` (debit positive), `source_file`, `source_row`. Every row of the export; the FedEx filter is Dani's rule, not the parser's (section below) |
| `statements.csv` | planned (V3.9) | `source` (`goodwillbooks`), `period_from`, `period_to`, `sales_cents`, `fees_cents`, `net_cents`, `paid_date`, `reference`, `source_file`, `source_row` |
| `jewelry.csv` | planned (V3.10) | `item_id`, `order_id`, `sold_date`, `amount_cents`, `supplier` (empty when the lookup does not know the item), `source_file`, `source_row` |
| `source_coverage.json` | built (V3.3) | per source, the files read, the days each covers, whether a simulator wrote it, and the days no file covers (section below) |

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

### `ledger.csv` (FedEx, from Business Central's ledger: a simulated API)
Every row of a Business Central G/L entries export. **The export's layout is ours** (`Entry No.`, `Posting Date`, `Document Type`, `Document No.`, `G/L Account No.`, `Department Code`, `Vendor No.`, `Description`, `Amount`): nobody has shown us one, and the only file there is comes from the simulator below.

| Column | Rule |
|---|---|
| `entry_no` | Business Central's entry number. The same entry in two overlapping exports counts once (`duplicate` warning, `same ledger entry as ...`). Added to the plan's draft; it is the first column. |
| `posting_date` | `YYYY-MM-DD`. |
| `document_type`, `document_no` | As written. A FedEx refund that came back as a bank deposit has a `document_no` starting `BNKDEPOSIT` and an empty type. |
| `gl_account`, `department`, `vendor_no` | As written, text. |
| `description` | As written, trimmed. |
| `amount_cents` | Debit positive, credit negative: a charge is positive, a refund negative. |
| `source_file`, `source_row` | Where it was read. |

**The parser filters nothing.** FedEx's month, as we read slide 38 (`ASSUMPTIONS.md` 2c.5): the rows with `gl_account` 40356, `department` 180 and `vendor_no` V00122, summed. The refunds are among them, negative, so the sum is already net of the BNKDEPOSIT refunds. The simulator also writes rows of another vendor, another department and another account, which that filter must leave out.

### `source_coverage.json`
```json
{"month": "2026-09", "through": "2026-09-30",
 "sources": {"amazon": {"files": [{"name": "amazon_daterange_2026-09-01_2026-09-20.csv", "from": "2026-09-01",
                                   "to": "2026-09-20", "basis": "file_name", "rows": 293, "simulated": false}],
                        "days_missing": ["2026-09-21", "2026-09-22"]}}}
```
- **Month:** the month of `--date`, from its 1st to `--date` (`through`). Run with the month end, as the close does, and it covers the whole month.
- **Sources:** keyed like `source_status.json`, by marketplace (`shopgoodwill`, `amazon`, `ebay` are always listed; `other` when a file has rows for it). Files that feed no marketplace are keyed by their parser's name instead (`bank`). A file that can carry several marketplaces (Cash Monkey) is listed only under the ones it has rows for. A single-marketplace file is listed even with 0 rows, because its days are still covered (a quiet day).
- **`from`, `to`, `basis`:** the days the file says it covers. `basis: file_name` means they come from the name: two dates (`2026-09-01_2026-09-20`, `09-07-2026_09-07-2026`), one date, or a month (`bank_activity_2026-09` = the whole month). Otherwise `basis: rows`: the first and last date of the file's rows (`business_date`, `paid_date`, `posting_date`). Amazon's names state Pacific days; the engine does not convert them.
- **`rows`:** the rows this file gave this source (transactions plus payouts, or bank lines), counted before cross-file de-duplication.
- **`simulated`:** `true` when `engine fetch --simulate` wrote the file. The simulator records each file it writes in `<inbox>/_simulated.json`, and a later real fetch of the same name removes it. The inbox reader skips that manifest (it is not a report).
- **`days_missing`:** the days of the month, up to `through`, that no file of the source covers. A source with no file has every day missing. `null` for a source made only of statements or lookups, which do not report day by day (from V3.8 on).
- A month-end file that feeds no marketplace is keyed by its parser: `bank`, `bc_ledger` (V3.5).

## The simulated month-end sources
```
python -m engine fetch --simulate --close-month YYYY-MM --inbox DIR --out DIR2 [--source a,b]
```
We assume each month-end source nobody has shown us can be fetched through an API (`ASSUMPTIONS.md` 2c). None exists for us, so each is a provider class in `engine/scrapers/` whose real client is a stub (`not_configured`) and whose simulator writes the file the API would have delivered. **Every layout and every value is ours and synthetic**, the same for the same month. The command writes:
- the files into `DIR`, and their names into `DIR/_simulated.json`, so `source_coverage.json` reads `"simulated": true` for each;
- `DIR2/fetch_log.json`: `{"close_month": "2026-09", "sources": {"bc_ledger": {"status": "ok", "files": ["bc_gl_entries_2026-09.csv"], "detail": "simulated: synthetic data, no real API", "simulated": true}}}`;
- `DIR2/expected_close_sources.json`: the answer key for those files, **computed from the generated records, never by the parsers**. Dani's tests read this file; they never import the simulators.

Without `--simulate` nothing is written and every source reads `not_configured`. The nightly `engine fetch --date` never delivers these sources.

| Source (`--source`) | File in the inbox | Engine output | In the answer key | Task |
|---|---|---|---|---|
| `bc_ledger` | `bc_gl_entries_<month>.csv` | `ledger.csv` | `fedex`: `gl_account`, `department`, `vendor_no`, `refund_document_prefix`, `charges_cents`, `refunds_cents` (positive), `net_cents`, `entries`, `entries_left_out` | V3.5 |

## What the engine does not do
- It matches nothing: deposits to payouts, payouts to windows and the FedEx filter are all Dani's (`reports/reconcile.py`).
- It does not read answer keys. The simulated sources (V3.5, V3.7 to V3.10) arrive with `python -m engine fetch --simulate --close-month YYYY-MM --inbox DIR --out DIR2`, which also writes `DIR2/expected_close_sources.json`. That is the answer key for those files, computed from the generated records, never by the parsers.

## Checked on `messy_month` (`engine/tests/test_payouts_bank.py`)
`python -m engine run --inbox data/sample/messy_month/inbox --out out/tmp --date 2026-09-30` writes:
- `payouts.csv` with 31 rows: 29 eBay and 2 Amazon, after the overlapping eBay download is de-duplicated. Each amount equals the answer key's `close.payouts[].amount_cents`. The key's eBay payout of 2026-10-01 is not in any file.
- `bank.csv` with 26 rows: 24 credits and 2 debits.
- `warnings.json` with no `unparseable` entry for `bank_activity_2026-09.csv`.
- `source_coverage.json` with `days_missing` of `2026-09-21` and `2026-09-22` for Amazon, `2026-09-07` for ShopGoodwill, and none for eBay or the bank (`engine/tests/test_source_coverage.py`).

## Changelog
- v0.3 (2026-10-04, Victor, V3.5): `ledger.csv` built, with `entry_no` added as its first column. `engine fetch --simulate --close-month` and `expected_close_sources.json` built, with `bc_ledger` as the first source. `days_missing` may be `null`.
- v0.2 (2026-10-04, Victor, V3.3): `source_coverage.json` built. Additions to the planned shape: `through`, and `basis` on each file. Simulated files are recorded in `<inbox>/_simulated.json`.
- v0.1 (2026-10-04, Victor, V3.2): `payouts.csv` and `bank.csv` built; the other shapes copied from the plan's section 4 as planned.
