# Sample data (Orlando, tasks O1 and P-O1)

**All of this is synthetic.** No Goodwill Michiana data is used. The eBay and Amazon layouts are modeled on their public seller reports (eBay *Transaction report*, Amazon *Date Range Report*). The ShopGoodwill layout is a guess. Column names will change once Amanda sends real or anonymized exports.

```
python data/generate.py      # rewrites data/sample/ (seeded: same bytes every run)
```
Needs `openpyxl` and `tzdata` (already in `engine/requirements.txt`).

## Scenarios
Each scenario is one inbox, the way staff would download it, plus an answer key.

```
data/sample/<scenario>/inbox/*      -> point the engine here
data/sample/<scenario>/expected.json -> what a correct pipeline should report
```

| Scenario | Business date | Files | What's in it |
|---|---|---|---|
| `clean_month` | Sep 2026 (all days) | 1 per source | Format quirks only. 3 refunds. 23 Amazon rows stamped late evening PDT that belong to the next ET day. |
| `day_clean` | 2026-10-01 | 1 per source, covering Sep 30 to Oct 1 | Normal nightly download. |
| `day_refund` | 2026-10-02 | 1 per source | One eBay refund and one Amazon refund issued Oct 2. The Amazon refund's original sale (Sep 30) is not in the inbox. |
| `day_ebay_missing` | 2026-10-03 | no eBay file | eBay must show `missing`, never $0. |
| `day_duplicates` | 2026-10-04 | eBay twice | `ebay_transactions_2026-10-04 (1).csv` re-downloads Oct 2-4 and overlaps the first file. One Amazon line pasted twice. |

Day scenarios cover the business date and the day before, so the day-over-day delta can be computed.

### Goodwill's real report tools (`gw_*`)
The scenarios above imitate the seller-portal reports. Goodwill's nightly numbers come from two tools instead (`docs/contracts/source-formats.md`), delivered as emailed Excel files (decision 004). These scenarios use them:

| Scenario | Business date | Files | What's in it |
|---|---|---|---|
| `gw_day_clean` | 2026-10-01 | `paid_orders_09-29-2026_10-01-2026.xlsx` (Upright), `orders2023-20261002-001512-96170.xlsx` (Cash Monkey) | Normal night. |
| `gw_day_cashmonkey_missing` | 2026-10-03 | Upright only | eBay and Amazon both missing, never $0. |
| `gw_day_duplicates` | 2026-10-04 | Upright twice (`... (4).xlsx`, as on the deck's title bar) | Every ShopGoodwill order appears twice. |

| Tool | Feeds | Layout |
|---|---|---|
| Upright "Paid orders" | ShopGoodwill | Header in row 1. One row per order. `Payment Date` is a plain timestamp in **Pacific** (the report's timezone setting). `Total` = `Subtotal` + `Shipping Charged` + `Handling` + `Tax Total`; revenue = `Subtotal`. Columns from the deck screenshot; `Secondary Order ID`, `Payment Date`, `Shipping Discount` are guesses for truncated headers. |
| Cash Monkey "Orders Report" | eBay (`eBay`), Amazon (`Amazon-MF`) | Header in row 1. **One line per unit**: a multi-item order repeats its `Order ID`; shipping and fees are pro-rated per unit. `Order Date` is a plain timestamp in **UTC**. No buyer column. **Every column name is a guess**: the deck never shows the file. |

Reports are pulled at 00:15 Eastern, after e-commerce closes at 9 PM Pacific. Upright is filtered by Pacific dates, Cash Monkey by UTC dates, with ranges wide enough to cover both Eastern days. No refunds: they are a separate download in both tools. Customers are counted by **order** for all three marketplaces: that is what staff do with Upright today, and Cash Monkey has no buyer id.

## Format quirks the parsers must handle
| Source | File | Quirks |
|---|---|---|
| ShopGoodwill | `.xlsx`, sheet `Orders` | 3 title rows before the header. `Close Date` is mostly a real Excel datetime (Eastern, no tz) but about 12% are text like `10/1/26 6:14 AM`. Some `Winning Bid` cells are text `$27.00`. No marketplace fee. Revenue = `Winning Bid` (shipping and handling excluded). |
| eBay | `.csv`, UTF-8 **with BOM**, CRLF | 4 preamble lines before the header. Date only (`Oct 1, 2026`), no time; treated as the ET date. `--` means empty. `Type` is `Order`, `Refund` or `Payout`; skip `Payout`. Fee = `Final Value Fee - fixed` + `Final Value Fee - variable` (both negative). Revenue = `Item subtotal`. |
| Amazon | `.csv`, UTF-8, LF | 7 preamble lines. `date/time` is Pacific with the zone name (`Oct 2, 2026 9:33:00 PM PDT`), so convert to ET before taking the date. Thousands separators (`1,234.50`). `type` is `Order`, `Refund` or `Transfer`; skip `Transfer`. **One row per item: multi-item orders repeat the order id with a different `sku`; those are not duplicates.** No buyer id, so customers are counted by order. Fee = `-selling fees`. Revenue = `product sales`. |

## `expected.json`
```json
{
  "scenario": "day_refund",
  "business_date": "2026-10-02",
  "definitions": { "...": "how each number is defined" },
  "days": {
    "2026-10-02": {
      "ebay": { "status": "ok", "sales_cents": 0, "refunds_cents": 0, "revenue_cents": 0,
                "fees_cents": 0, "orders": 0, "customers": 0, "customer_basis": "buyer" },
      "amazon": { "...": "..." },
      "shopgoodwill": { "...": "..." },
      "enterprise": { "sales_cents": 0, "refunds_cents": 0, "revenue_cents": 0, "fees_cents": 0,
                      "orders": 0, "customers": 0 }
    }
  },
  "mess": "what is wrong with this inbox"
}
```
A missing source is `{"status": "missing"}` with no numbers. Enterprise totals only add sources that have data. Definitions follow the defaults in `docs/contracts/transaction.md` (revenue net of refunds, fees separate, ET order date). Refunds count on the day they are issued.

## Messy month (`messy_month`, task O2, for phase 3)
September again (the same orders as `clean_month`), downloaded the messy way, plus the money side. `expected.json` has the usual `days` plus a `close` section: month totals from the files, every payout (amount, activity window, deposit date or `in_transit`, and `data_gap_cents` = money paid for activity missing from our files), every bank deposit with the payouts it matches, and the list of planted exceptions.

| File(s) | Mess |
|---|---|
| `paid_orders_MM-DD-YYYY_MM-DD-YYYY.xlsx` (Upright, one per Pacific day) | Sep 7 never downloaded; Sep 15 saved twice (`(4)`). |
| `ebay_transactions_<from>_<to>.csv` (weekly) | A re-download (`(1)`) overlapping two weeks; one row with `#VALUE!` amounts and one dated Sep 31. Payout rows carry the real daily payout. A refund of an **August** order. |
| `amazon_daterange_<from>_<to>.csv` | Sep 21-22 (Pacific) not downloaded. Transfer rows carry the real settlements (Sep 1-14, Sep 15-28). A refund of an **August** order. |
| `bank_activity_2026-09.csv` | Operating account: Debit/Credit columns, running balance. eBay deposits that land on a weekend or Labor Day are combined into one deposit (several payouts). One deposit nobody can explain (Sep 17, $412.37). Payroll and a service charge as noise. Payouts after Sep 25 are still in transit on Sep 30. |

Payout model (a simplification, stated so nobody mistakes it for fact): eBay pays daily for the Eastern day, Amazon settles every 14 days, ShopGoodwill pays weekly on Monday; money reaches the bank 2-4 days later on business days. Net = merchandise + shipping (+ handling for ShopGoodwill) - marketplace fees; tax is remitted by the marketplace.

## Tidy month (`tidy_month`, task D3.6, for phase 3)
The same September events as `messy_month`, with every report downloaded once: the clean example for the month-end close. Same file formats and names, same payout model, so the same parsers and `reports/config/bc_mapping.csv` read it. **Synthetic like everything else here**: the layouts are the same guesses as above, and the bank file is invented.

| File(s) | What's in it |
|---|---|
| `paid_orders_MM-DD-YYYY_MM-DD-YYYY.xlsx` (Upright, one per Pacific day) | All 30 days, each once. |
| `ebay_transactions_<from>_<to>.csv` (weekly) | Sep 1-7, 8-14, 15-21, 22-30: no overlap, no broken row. Payout rows carry the real daily payout. |
| `amazon_daterange_<from>_<to>.csv` | Sep 1-20 and Sep 21-30 (Pacific): no gap. Transfer rows carry the real settlements. |
| `bank_activity_2026-09.csv` | The same account without the deposit nobody can explain. Payroll and the service charge stay. |

What `messy_month` has and this month does not: the two refunds of August orders (so the eBay and Amazon amounts differ between the two months), the skipped days, the file saved twice, the overlapping re-download, the two broken rows, the unexplained deposit.

`expected.json` has the same shape as the messy month's (`days`, and `close` with `month`, `marketplace_totals_from_files`, `payouts`, `bank_deposits`, `exceptions`, `not_modeled`), computed from the generated events, never by running the engine. Every payout has `data_gap_cents` 0. `close.exceptions` holds only what a tidy month really has: activity earned in September and not paid out yet (`unpaid_at_month_end`), and payouts that reach the bank in October (`in_transit`). `reports/tests/test_close_tidy_month.py` runs the close on it: three sources `OPEN`, nothing unexplained.

The name is `tidy_month` because `clean_month` is taken (older formats, no bank file), and because `reports.run_scheduled.month_inbox` takes the first sample in name order whose key has `close.month`: a name after `messy_month` keeps the scheduled close on the messy month.

### Side folders of both months (`periodic/`, `cashmonkey/`)
`messy_month` and `tidy_month` each have two more folders **beside** `inbox/`, not inside it, so nothing that reads the inbox today changes. They are for the close to add as extra inboxes once it has a rule for them. Both files are byte for byte the same in the two months, and complete in the messy one too: they come from the marketplace and from the tool, not from what staff happened to download. **Both layouts are synthetic guesses.** No answer key counts them: `close.marketplace_totals_from_files` is the `inbox/` only.

| File | What it is |
|---|---|
| `periodic/shopgoodwill_periodic_2026-09.csv` | ShopGoodwill's periodic report **as we imagine it: the layout is ours, nobody on the team has seen the real one**, and what the deck calls "Period 1" and "Period 3" is not modeled. One row per ShopGoodwill payout, columns `Period Start`, `Period End`, `Paid Date`, `Payout Amount`, `Reference` (dates `MM/DD/YYYY`, periods in Pacific days, amount with 2 decimals, reference = the payout id, `SGW-0906`). Its four rows equal the `SGW-*` entries of `close.payouts` and the four ShopGoodwill deposits in the bank file. |
| `cashmonkey/orders2023-20261001-001512-96170.xlsx` | The Cash Monkey "Orders Report" for eBay and Amazon, one file for the month, in the layout of the `gw_*` scenarios (one line per unit, UTC, every column name a guess). Pulled at 00:15 Eastern on Oct 1 for UTC dates Sep 1 to Oct 1, wide enough for the Eastern month: 1,212 orders, 1,258 lines. |

Two things to know before comparing the Cash Monkey file with the marketplace reports:
- **No refunds.** `write_cashmonkey` writes orders only (refunds are a separate download in the tool), so the three September refunds, and the two August refunds of the messy month, are not in it. Compare sales, not revenue net of refunds.
- **One Amazon order more.** eBay sales are equal to the tidy month's eBay reports ($20,052.32, 768 orders). Amazon is one order above the tidy month's Amazon reports ($10,321.60 against $10,289.61): order `112-6987455-5957234`, sold at 00:03 Eastern on Sep 1, is Aug 31 in Pacific time, so no September Date Range report holds it. Against the messy month the difference also includes the Amazon sales of Sep 21-22 (Pacific), which that inbox never downloaded.

### Late reports of the messy month (`late/`, task D3.9)
The two reports the messy inbox never downloaded, found later. They sit beside `inbox/`, so the first close still misses them; add the folder as a second inbox to see the close once they arrive (`python -m reports.close --inbox data/sample/messy_month/inbox --inbox data/sample/messy_month/late --month 2026-09`).

| File | What it is |
|---|---|
| `late/paid_orders_09-07-2026_09-07-2026.xlsx` | Upright "Paid orders" for September 7 (Pacific): the day payout `SGW-0913` paid for and no file held. |
| `late/amazon_daterange_2026-09-21_2026-09-22.csv` | Amazon Date Range report for September 21-22 (Pacific): the two days settlement `AMZN-0928` paid for and no file held. |
| `expected_after_late.json` | The answer key of the month once both are in the inbox, from the same generated events: no payout has a data gap, and the two `missing_file` exceptions are gone. The rest of the mess stays (the duplicate file, the overlapping download, the two broken rows, the two refunds of August orders, the unmatched deposit). `expected.json` is not touched. |
