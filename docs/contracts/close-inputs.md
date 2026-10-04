# Contract: close inputs (C3.1): what the engine hands the month-end close

- **Owner:** Victor (`engine/`). **Consumers:** Dani (`reports.reconcile`, the close), by decision 009.
- **Status:** draft v0.6. **Every file below is built**, and so is the command that delivers the simulated month-end sources.
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
| `statements.csv` | built (V3.9) | `source` (`goodwillbooks`), `period_from`, `period_to`, `sales_cents`, `fees_cents`, `net_cents`, `paid_date`, `reference`, `source_file`, `source_row` |
| `jewelry.csv` | built (V3.10) | `item_id`, `order_id`, `sold_date`, `amount_cents`, `supplier` (empty when the lookup does not know the item), `source_file`, `source_row` |
| `source_coverage.json` | built (V3.3) | per source, the files read, the days each covers, whether a simulator wrote it, and the days no file covers (section below) |

### `payouts.csv`
One row per payout a marketplace report says it sent to the bank: eBay's Transaction report `Payout` rows, Amazon's Date Range report `Transfer` rows, and each period of ShopGoodwill's periodic report (V3.8). Without a periodic report in the inbox ShopGoodwill has no rows here, and the close takes each of its deposits as a payout.

| Column | Rule |
|---|---|
| `payout_id` | `<marketplace>:<paid_date>`, e.g. `ebay:2026-09-02`. A second payout on the same day in the same file gets `#2`, `#3`. |
| `marketplace` | `ebay`, `amazon`, `shopgoodwill`. |
| `paid_date` | `YYYY-MM-DD`, **the date as the report writes it**, in the report's own zone. Amazon's `Sep 15, 2026 9:12:44 AM PDT` is `2026-09-15` even when the Eastern date would be different. |
| `amount_cents` | Positive = paid to Goodwill. The reports print payouts as negative (money leaving the marketplace); the sign is flipped. eBay: `Net amount` (or `Gross transaction amount` in the older layout); Amazon: `total`. |
| `period_from`, `period_to` | Empty, unless the report states the period it pays for: ShopGoodwill's periodic report does (`Period Start`, `Period End`, in Pacific days). The engine never infers a window: that is the close's rule (D3.1). |
| `source_file`, `source_row` | Where it was read. |

**ShopGoodwill's periodic report** (`shopgoodwill_periodic_<month>.csv`; **the layout is ours**, from the sample generator: `Period Start`, `Period End`, `Paid Date`, `Payout Amount`, `Reference`; what the deck calls "Period 1" and "Period 3" is not modeled). The two sample months have one each in `data/sample/<month>/periodic/`: add that folder to the inbox. A row whose period ends before it starts, or with no amount, is a warning. The report is not a sales report, so it never counts as coverage of ShopGoodwill's days: in `source_coverage.json` it has its own key, `shopgoodwill_periodic`.

**Overlapping downloads:** the same `payout_id` in two files counts once, and the first copy (in sorted file order) wins. The dropped copy is a `duplicate` warning whose reason starts `same payout as`, and that reason also says when the amounts differ. Payout rows never appear in `transactions.csv`.

### `bank.csv`
Every line of a bank export (`Posting Date`, `Description`, `Debit`, `Credit`, optional `Balance`, optional `Account`): credits, debits, payroll, everything. Which lines are marketplace deposits is the close's rule (`Bank_Text` in `bc_mapping.csv`), not the parser's.

| Column | Rule |
|---|---|
| `bank_txn_id` | `<file>:<row>`. |
| `account` | The file's `Account` column; `OPERATING` when it has none (the sample `bank_activity_*.csv`). The simulated feed of the carriers' account writes `0101` (V3.7). Both accounts share this file. |
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

### `statements.csv` (Goodwill Books: a simulated API)
One row per payment statement. **The statement's layout is ours** (`Statement Period Start`, `Statement Period End`, `Gross Sales`, `Fees`, `Net Payment`, `Payment Date`, `Payment Reference`).

| Column | Rule |
|---|---|
| `source` | `goodwillbooks`. |
| `period_from`, `period_to` | The month the statement reports: **the month before** the one it is paid in. |
| `sales_cents`, `fees_cents`, `net_cents` | Sales, the fees kept (positive), and the net paid: sales minus fees. |
| `paid_date`, `reference` | The day it was paid and the payment's reference (`GWB-2026-08`). The same statement in two files counts once, by `reference`. |
| `source_file`, `source_row` | Where it was read. |

Its payment is a credit in the bank feed of account `0101`: same day, same amount, with the reference in the description. Until the close has a rule for it (D3.13), `reconcile` lists that credit as an `unmatched_deposit` and holds it out of the journal.

### `jewelry.csv` (Jewelry Report with Supplier: a simulated API)
The month's jewelry sales, one row per item, each with the supplier a lookup gives for it. **Both input layouts are ours**, and so is the reading of "Supplier" as the Goodwill store that supplied the item (`ASSUMPTIONS.md` 2c.3):
- the report, `jewelry_report_<month>.csv`: `Item ID`, `Order ID`, `Sold Date`, `Description`, `Sale Amount`, with no supplier;
- the lookup, `jewelry_supplier_lookup_<month>.csv`, standing for whatever "Co-Pivot populates Supplier" is: `Item ID`, `Supplier`.

| Column | Rule |
|---|---|
| `item_id`, `order_id` | As written. The same item and order in two files counts once. |
| `sold_date` | `YYYY-MM-DD`. |
| `amount_cents` | The sale amount. |
| `supplier` | From the lookup, by `item_id`. **Empty when the lookup does not know the item**, with a `missing_supplier` warning naming the item and its amount: never a guess. A report that already has a `Supplier` column keeps its value. With no lookup file in the inbox, every row is empty and every row is a warning. Two lookup rows that give one item different suppliers: the first wins and the other is a `duplicate` warning. |
| `source_file`, `source_row` | The report's file and row. |

The lookup is an input only: the engine writes no file for it. These sales are also in the marketplaces' own reports, so `jewelry.csv` must never be added to revenue; what the supplier is used for in the close is still open (plan, question 7). The simulator plants one item the lookup does not know.

### Carriers in `bank.csv` (OSM, PB, EasyPost: a simulated API)
The simulated feed of account `0101` (`bank_activity_0101_<month>.csv`: the bank layout plus an `Account` column) holds the month's carrier payments as debits, the Goodwill Books payment as its only credit, and a few debits that are no carrier's. A carrier's month is the debits on account `0101` whose description contains its text: `OSM WORLDWIDE`, `PITNEY BOWES` (PB), `EASYPOST`. **Those texts are ours**; the answer key repeats them (`carriers.<name>.bank_text`). Which G/L account they post to (slide 38 says 10009 for the bank account) is the close's rule.

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
- A month-end file that feeds no marketplace is keyed by its parser: `bank` (both accounts), `bc_ledger`, `jewelry_report`, and with `days_missing` `null`, `goodwillbooks_statement`, `shopgoodwill_periodic` and `jewelry_suppliers`.

## The simulated month-end sources
```
python -m engine fetch --simulate --close-month YYYY-MM --inbox DIR --out DIR2 [--source a,b]
```
We assume each month-end source nobody has shown us can be fetched through an API (`ASSUMPTIONS.md` 2c). None exists for us, so each is a provider class in `engine/scrapers/` whose real client is a stub (`not_configured`) and whose simulator writes the file the API would have delivered. **Every layout and every value is ours and synthetic**, the same for the same month. The command writes:
- the files into `DIR`, and their names into `DIR/_simulated.json`, so `source_coverage.json` reads `"simulated": true` for each;
- `DIR2/fetch_log.json`: `{"close_month": "2026-09", "sources": {"bc_ledger": {"status": "ok", "files": ["bc_gl_entries_2026-09.csv"], "detail": "simulated: synthetic data, no real API", "simulated": true}}}`;
- `DIR2/expected_close_sources.json`: the answer key for those files, **computed from the generated records, never by the parsers**. Dani's tests read this file; they never import the simulators.

A source marked "on request" is delivered only when named with `--source`. Without `--simulate` nothing is written and every source reads `not_configured`. The nightly `engine fetch --date` never delivers these sources.

| Source (`--source`) | File in the inbox | Engine output | In the answer key | Task |
|---|---|---|---|---|
| `bc_ledger` | `bc_gl_entries_<month>.csv` | `ledger.csv` | `fedex`: `gl_account`, `department`, `vendor_no`, `refund_document_prefix`, `charges_cents`, `refunds_cents` (positive), `net_cents`, `entries`, `entries_left_out` | V3.5 |
| `bank_0101` | `bank_activity_0101_<month>.csv` | rows of `bank.csv` with `account` `0101` | `carriers`: `bank_account`, `osm` / `pb` / `easypost` (each `bank_text`, `cents`, `payments`), `total_cents`, `lines`, `other_debits` | V3.7 |
| `goodwillbooks` | `goodwillbooks_statement_<prior month>.csv` | `statements.csv` | `goodwillbooks`: the statement's columns, plus `bank_account` and `bank_text` of its payment | V3.9 |
| `jewelry` | `jewelry_report_<month>.csv`, `jewelry_supplier_lookup_<month>.csv` | `jewelry.csv` | `jewelry`: `items`, `sales_cents`, `by_supplier` (`{"Store 01": {"cents": ..., "items": ...}}`), `missing_supplier` (`items`, `cents`) | V3.10 |
| `shopgoodwill_periodic` (**on request**) | `shopgoodwill_periodic_<month>.csv` | ShopGoodwill rows of `payouts.csv` | `shopgoodwill_periodic`: a list of `period_from`, `period_to`, `paid_date`, `amount_cents`, `reference` | V3.8 |

**Why the periodic report is on request.** Its simulator adds up the simulated Upright orders of the month, so it agrees with an inbox filled by `engine fetch --simulate --from D1 --to D2` and with nothing else. The sample months have their own report, which agrees with their bank file; a second one beside it would disagree (the close refuses two files of the same name).

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
- v0.6 (2026-10-04, Victor, V3.10): `jewelry.csv` built: the Jewelry Report joined with the supplier lookup, `missing_supplier` for an item the lookup does not know.
- v0.5 (2026-10-04, Victor, V3.8): ShopGoodwill's periodic report becomes payout rows with `period_from` and `period_to`. A simulator for months without a sample report, on request only.
- v0.4 (2026-10-04, Victor, V3.7 and V3.9): `statements.csv` built; the simulated bank feed of account `0101` (carriers, and the Goodwill Books payment as a credit) lands in `bank.csv`.
- v0.3 (2026-10-04, Victor, V3.5): `ledger.csv` built, with `entry_no` added as its first column. `engine fetch --simulate --close-month` and `expected_close_sources.json` built, with `bc_ledger` as the first source. `days_missing` may be `null`.
- v0.2 (2026-10-04, Victor, V3.3): `source_coverage.json` built. Additions to the planned shape: `through`, and `basis` on each file. Simulated files are recorded in `<inbox>/_simulated.json`.
- v0.1 (2026-10-04, Victor, V3.2): `payouts.csv` and `bank.csv` built; the other shapes copied from the plan's section 4 as planned.
