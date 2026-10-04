# Month-close: what files the picker accepts

Quick reference for anyone adding downloaded files on the close page (`/close/<month>.html`, the picker beside each source). Summary of `docs/contracts/close-inputs.md` and `docs/contracts/source-formats.md`; those two are the source of truth.

**There is no single form.** The engine recognizes each file by its own name and layout, whichever source's row it was chosen beside.

## Upload rules (`reports/close_upload.py`)
- Only `.csv` and `.xlsx`, 10 MB at most, not empty.
- A file whose name is already in the run is refused, not counted twice.
- The folder part of a name is dropped.
- Added files are kept in `out/uploads/<month>/`; "Remove the added files" clears them.
- The page needs the server: `python server.py`, then open `http://127.0.0.1:8000/close/<month>.html`. Opened from disk, the pickers are disabled.

## Layouts per source

"Ours" = a layout we made up, because Goodwill has shown us no real file. Everything in the samples and simulators is synthetic.

| Source | File name | Columns |
|---|---|---|
| Amazon | `amazon_daterange_<from>_<to>.csv` | Amazon's Date Range report (title lines first, then data) |
| ShopGoodwill / Upright | `paid_orders_<MM-DD-YYYY>_<MM-DD-YYYY>.xlsx` or `.csv` | Upright's Paid orders report; header is row 1 (`Channel`, `Subtotal`, `Total`, ...) |
| eBay | the eBay Transaction report | `Payout` rows give the deposits |
| Cash Monkey | `orders2023-<YYYYMMDD>-<HHMMSS>-<n>.csv` | one line per unit, with a `Channel` column |
| Bank (OSM / PB / EasyPost) | `bank_activity_0101_<month>.csv` | `Posting Date`, `Description`, `Debit`, `Credit`, `Account`, optional `Balance` (ours) |
| FedEx, from the BC ledger | `bc_gl_entries_<month>.csv` | `Entry No.`, `Posting Date`, `Document Type`, `Document No.`, `G/L Account No.`, `Department Code`, `Vendor No.`, `Description`, `Amount` (ours) |
| Goodwill Books | `goodwillbooks_statement_<prior month>.csv` | `Statement Period Start`, `Statement Period End`, `Gross Sales`, `Fees`, `Net Payment`, `Payment Date`, `Payment Reference` (ours) |
| Jewelry | `jewelry_report_<month>.csv` | `Item ID`, `Order ID`, `Sold Date`, `Description`, `Sale Amount` (ours) |
| Jewelry supplier lookup | `jewelry_supplier_lookup_<month>.csv` | `Item ID`, `Supplier` (ours). Without it every jewelry row has no supplier and is a warning |
| ShopGoodwill periodic (payouts) | `shopgoodwill_periodic_<month>.csv` | `Period Start`, `Period End`, `Paid Date`, `Payout Amount`, `Reference` (ours) |

## How names and duplicates are treated
- Dates in the file name tell the close which days the file covers. A missing or odd name falls back to the first and last dates in the rows.
- Overlapping downloads are fine: the same order, payout, bank line or ledger entry in two files counts once; the second copy is a warning.
- A file the engine cannot read is listed with a warning, never silently dropped.

## Working examples
- `data/sample/messy_month/late/`: the two files that fill that month's gaps.
- `python -m engine fetch --simulate --close-month 2026-09 --inbox DIR --out DIR2`: writes the simulated month-end sources.

## What turns the page from red to green
The "To be complete, this month needs..." box turns green ("Complete") once no `missing_report` exceptions remain. A control-totals pill turns green when its source reconciles. A file for the wrong source or period, or an unmatched deposit, leaves it red.
