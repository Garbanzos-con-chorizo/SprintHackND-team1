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
