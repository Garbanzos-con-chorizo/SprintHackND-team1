# Contract: canonical transaction, phase 1 (task 0.1)

- **Owner:** Victor (`engine/`). **Consumers:** Dani (pulse calculation), Orlando (pulse rendering, and later the dashboard).
- **Status:** agreed (v0.5: `occurred_at` appended, non-breaking; v0.4: three columns appended). In use by `recon/` (pulse) and `reports/`; the engine implements it.
- **Scope:** phase 1 only, the nightly pulse. Phase 3 (close) adds columns later (`fee`/`payout`/`bank` types, `net_cents`, `memo`, GL fields). Adding columns is not a breaking change: consumers ignore columns they don't know.

## What this contract does
Turns messy exports into one clean table that Dani can aggregate and Orlando can show without handling any source quirks. Everything messy is dealt with **before** this file, by Victor's engine.

```
inbox/<anything>.csv|xlsx -> engine (parse, clean, dedupe) -> out/transactions.csv
                                                           -> out/source_status.json
                                                           -> out/warnings.json
```
The engine rewrites all three on each run from everything in `inbox/`. Phase 2 reads the same `out/transactions.csv` over a month, so the schema does not change between phases.

## `out/transactions.csv`
CSV, UTF-8 (no BOM), header row, RFC 4180 quoting, `\n` line endings. One row per sale or refund.

| Column | Type | Required | Rule |
|---|---|---|---|
| `txn_id` | string | yes | Unique and deterministic: `<source>:<order id>:<type>`. Same input always gives the same id. |
| `source` | enum | yes | The export it came from: `upright`, `cashmonkey`, and the older single-marketplace layouts `shopgoodwill`, `amazon`, `ebay`. Other sources join the enum when we have samples. The pulse buckets by `marketplace`, not `source`, because one Cash Monkey file carries several marketplaces. |
| `marketplace` | enum | yes | Pulse bucket: `shopgoodwill`, `amazon`, `ebay`, `other`. Mapping from `source` is engine config (P-V1). |
| `type` | enum | yes | `sale` or `refund`. |
| `business_date` | date | yes | `YYYY-MM-DD`. The day the row counts toward (P-V3). Default: order date in `America/New_York`; timezone and cutoff are engine config. |
| `order_id` | string | yes | Marketplace order id, trimmed. A refund carries the id of the order it refunds. |
| `customer_id` | string | no | Buyer key where the source exposes one. Never raw emails or addresses (hash if that's all there is). Empty if none. |
| `customer_basis` | enum | yes | `buyer` if `customer_id` is set, else `order` (count distinct `order_id`). Lets the report label the metric (P-V2). |
| `gross_cents` | integer | yes | USD cents, signed. `sale` positive, `refund` negative. Excludes shipping and tax. |
| `fee_cents` | integer | yes | Marketplace fee in USD cents, positive = cost to us. 0 if the source doesn't report one. Reported separately; never subtracted from `gross_cents`. |
| `source_file` | string | yes | Input filename. |
| `source_row` | integer | yes | 1-based data row in that file. |
| `shipping_cents` | integer | yes (v0.4) | What the buyer paid for shipping, USD cents, signed like `gross_cents` (a refund row carries the shipping refunded, negative). Not revenue; the close posts it. A source with one combined "shipping and handling" column (eBay) puts it all here. Upright: `Shipping Charged` minus `Shipping Discount`. 0 if the export has no shipping column. |
| `handling_cents` | integer | yes (v0.4) | What the buyer paid for handling, same rules (Upright `Handling`, ShopGoodwill `Handling Fee`). 0 if the export has none. |
| `units` | integer or empty | no (v0.4) | Units sold, on `sale` rows (summed over the lines of the order); `0` on `refund` rows. **Empty when the export has no unit count**, never 0, so readers fall back to per-order figures. Upright `Order Items`, Cash Monkey / eBay / Amazon `Quantity`, ShopGoodwill one per row. |
| `occurred_at` | datetime or empty | no (v0.5) | The moment of the sale or refund, ISO 8601 with its offset, e.g. `2026-09-01T01:28:05-07:00`. The offset is the one the export wrote (Amazon `PDT` gives `-07:00`), or the zone the engine assumes for that source when the export writes none (Upright: Pacific; Cash Monkey: UTC; anything else: Eastern). **Empty when the export gives only a date (eBay's Transaction report) or the day comes from the file name.** Several lines of one order: the first line's time. `business_date` is this moment read in Eastern time. The close uses it to rebuild payout windows that run on Pacific days (`docs/PLAN_PHASE_3.md`, V3.1, D3.1). The store ignores it. |

Revenue by default (`OFFICE_HOURS.md` Q5): sum of `gross_cents` over `sale` and `refund` rows for a `business_date`, so net of refunds. Fees are summed separately. Changing the definition changes Dani's calculation only.

## Cleaning rules (what "messy" becomes)
The engine applies these in order. Anything it can't fix is skipped and listed in `warnings.json`; **a bad row never crashes the run and is never silently dropped** (V6).

| Mess in the export | Clean result |
|---|---|
| Money as `$1,234.50`, `1234.5`, `(12.00)`, `12.00-` | Integer cents. Parentheses or trailing minus mean negative. |
| Refund shown as a positive number or in a separate refunds column | `type=refund`, `gross_cents` negative. |
| Dates in mixed formats (`10/2/26`, `2026-10-02`, `Oct 2, 2026`), with or without time, any timezone | `business_date` as `YYYY-MM-DD` in the configured timezone. Ambiguous or unparseable: warning `bad_date`, row skipped. |
| Same order exported twice (overlapping or re-downloaded files) | One row. Dedupe key is `txn_id`. Dropped rows are listed as `duplicate` warnings (P-V5). |
| Extra whitespace, mixed case ids, stray BOM, blank trailing rows | Trimmed, ids kept case-as-given but compared trimmed, BOM stripped, blank rows ignored without a warning. |
| Missing required column in a file | Whole file rejected with a `missing_column` warning; the source becomes `missing` or `stale` in `source_status.json`, never `$0`. |
| Missing buyer id | `customer_id` empty, `customer_basis=order`. |
| Non-USD currency | Row skipped with an `unsupported_currency` warning. |
| Source name varies (`eBay`, `EBAY`, `ebay-us`) | Normalized to the `source` enum via the detection rules in engine config (V2). |

## `out/source_status.json` (P-V4)
Lets the pulse show "no data" instead of `$0`. **Keyed by marketplace**, because one file can feed several marketplaces (a Cash Monkey export carries Amazon, eBay and Goodwillbooks) and the pulse is organized by marketplace.
```json
{
  "generated_at": "2026-10-03T13:00:00-04:00",
  "business_date": "2026-10-02",
  "sources": {
    "shopgoodwill": { "status": "ok",      "files": ["paid_orders_10-02-2026_10-02-2026.csv"], "rows": 24 },
    "ebay":         { "status": "ok",      "files": ["orders2023-20261002-132256-96170.csv"],  "rows": 17 },
    "amazon":       { "status": "stale",   "files": ["orders2023-20261002-132256-96170.csv"],  "rows": 0 }
  }
}
```
- `ok`: a file that feeds this marketplace was read and has at least one row for `business_date`. `files` lists the files that contributed rows.
- `stale`: a file that feeds it was read but has no rows for `business_date` (a quiet day and an old export look the same). `files` lists the candidate files.
- `missing`: no file that could feed it was read: never downloaded, or unreadable (see `warnings.json`).
- Expected marketplaces come from `EXPECTED_MARKETPLACES` in `engine/contract.py` (`shopgoodwill`, `amazon`, `ebay`). **`other` is listed only on a day it has rows**; otherwise it is left out and the pulse treats it as not configured.
- The top-level key is still named `sources` so Dani's loader needs no change; its values are marketplaces.

## `out/warnings.json`
```json
[ { "source_file": "ebay_2026-10-02.csv", "source_row": 12, "kind": "duplicate", "reason": "same order id as row 9" } ]
```
`kind` is one of `duplicate`, `bad_date`, `bad_amount`, `missing_column`, `unsupported_currency`, `unparseable`. Orlando may show a count as a data-quality footnote.

## Example (also in `examples/transactions.sample.csv`)
```csv
txn_id,source,marketplace,type,business_date,order_id,customer_id,customer_basis,gross_cents,fee_cents,source_file,source_row
ebay:12-34567-89012:sale,ebay,ebay,sale,2026-10-02,12-34567-89012,buyer_ab12,buyer,2599,336,ebay_2026-10-02.csv,14
ebay:12-34567-89012:refund,ebay,ebay,refund,2026-10-02,12-34567-89012,buyer_ab12,buyer,-2599,0,ebay_2026-10-02.csv,31
amazon:114-2345678-9012345:sale,amazon,amazon,sale,2026-10-02,114-2345678-9012345,,order,3299,495,amazon_2026-10-02.csv,5
shopgoodwill:SG-883210:sale,shopgoodwill,shopgoodwill,sale,2026-10-02,SG-883210,sgbidder77,buyer,8400,0,sg_orders_oct02.xlsx,3
```

## Mock for parallel work
Until the engine runs, Dani and Orlando code against `examples/transactions.sample.csv` and a hand-written `source_status.json` that follow this contract. Orlando's P-O1 sample days replace it.

## Open questions (default applies until Amanda answers)
- Revenue gross, net of refunds, or net of fees (Q5): default net of refunds, fees separate.
- Customer is unique buyer or orders (Q6): default buyer, fall back to order, labelled.
- Day definition and timezone (Q7): default order date, `America/New_York`.
- What counts as `other` (Q9): not produced in phase 1 until we have a sample; the enum value is reserved.
- Which marketplaces expose a buyer id (Q6): unknown until sample exports exist.

## Rules confirmed after integration (v0.3)
- **A refund counts on the day it is issued**, not the day of the original order: its `business_date` is the refund's own date. (Asked by Orlando; this is how the sample answer keys count it.)
- **Several lines of one order in the same file become one row.** Amazon lists one row per item and Cash Monkey one line per unit, so a multi-item order is summed into one `sale` row per order, per file. The same order appearing again in another file is a duplicate and is counted once (first copy wins, the rest are logged).
- **`customer_basis` can be `order` even when `customer_id` is filled.** Upright has a buyer column, but staff count rows (deck slide 26), so its rows say `order` and the pulse counts orders. The buyer id is kept.
- **`source` values in use:** `upright`, `cashmonkey`, `shopgoodwill`, `amazon`, `ebay`. `marketplace` is what the pulse groups by; a Cash Monkey file carries `amazon`, `ebay` and `other` rows.
- **`source_status.json` is keyed by marketplace** (see its section above).

## Changelog
- v0.5 (2026-10-04, Victor, task V3.1): `occurred_at` appended. On `messy_month` the rows whose `occurred_at`, read in Pacific time, falls in each Amazon and ShopGoodwill payout window sum (gross + shipping + handling - fee) to the answer key's `net_in_files_cents` for all six windows (`engine/tests/test_occurred_at.py`).
- v0.4 (2026-10-04, Victor): `shipping_cents`, `handling_cents`, `units` appended (Orlando's request for the close; `units` for KPIs 10 and 11). Appended at the end, so v0.3 readers keep working. On `messy_month` the shipping and handling totals per marketplace equal the answer key to the cent.
- v0.3: status agreed; rules above written down; sources and `source_status.json` keyed by marketplace; Upright and Cash Monkey added.
- draft v0.2: narrowed to phase 1; added cleaning rules; dropped close-only columns and sources.
- draft v0.1: initial (superseded).
