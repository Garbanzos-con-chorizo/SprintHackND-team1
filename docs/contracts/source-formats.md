# What we actually know about the real source files

Evidence for the synthetic-data generator (`data/generate.py`, Orlando) and the parsers (`engine/sources/`, Victor). Everything here is read off the SprintHack deck (`innovationsprintlab.com/sprinthack-deck/sprinthack.html`, slide numbers given), not from real files. **Confidence is stated per fact. Anything marked UNKNOWN must not be invented as if it were known; if a generator needs a value, it is labelled a guess.** Real or anonymized exports from Amanda replace all of this.

## The nightly pulse most likely comes from two reports, not the three our samples imitate
| Pulse marketplace | Real source (evidence) | Our current synthetic file |
|---|---|---|
| ShopGoodwill | **Upright, "Paid orders" report** (slides 21-26). The `Channel` column reads `Shopgoodwill`; the file is opened in Excel and customers are counted as rows minus the title row, then typed into the Daily Summary Spreadsheet (slide 26). | `ShopGoodwill_Orders_*.xlsx`, a guess of a ShopGoodwill seller export |
| eBay, Amazon, Other | **Cash Monkey "Orders Report"** (slides 27-30): "Showing orders across all market places, with profit information where available. One line per unit." Channels offered: `Amazon-MF`, `eBay`, `Goodwillbooks`. | `ebay_transactions_*.csv` (eBay Transaction report) and `amazon_daterange_*.csv` (Amazon Date Range report) |
| eBay, Amazon (close only) | Seller Center "Listing sales report", Seller Central "Payments summary" (slide 38). These feed the **month-end close**, not necessarily the nightly numbers. | not modeled |

Inference, not stated in the deck: that the nightly eBay and Amazon numbers come from Cash Monkey rather than the seller portals. Confirm with Amanda (office-hours question: where does each nightly number come from?).

## Upright, Paid orders report
- **How it is produced** (slides 21-25, 7-9 screenshots): Reports, Downloads menu, Paid orders; set a date range; a **Timezone** field (default `Pacific Daylight Time`, "Use America/Los_Angeles for SGW"); Channel (default `All`); Payment status (`Paid`); Generate report. It is **asynchronous**: "We'll email the report when it's ready"; finished reports appear under *Past reports* (Created by, Created, Status `Complete`, a Download link). Other downloads in the same menu: Paid order items, Orders, **Refunds**, Shipments, Products, Manifest items. Slide 38 says "Generate; email delivery; save as Excel".
- **Day boundary:** the report's own timezone is chosen by the person running it. Our business day is Eastern (default). The report's day and our day can differ. UNKNOWN which timezone staff actually use.
- **File:** saved from Excel (the title bar shows `paid_orders_09-30-2026_09-30-2026 (4)`), so the name pattern is `paid_orders_<MM-DD-YYYY>_<MM-DD-YYYY>` and the format is probably `.csv` opened in Excel. UNKNOWN whether staff keep it as CSV or Excel.
- **Columns as far as the screenshot (slide 26) shows them; left to right, several headers truncated:**
  `Upright Order ID` (digits, e.g. 24224278) · `Channel` (`Shopgoodwill`) · `Channel Order ID` (digits, e.g. 65748407) · `Secondary…` (truncated, empty in view) · `Channel Buyer` (a username, e.g. `Okeye904`, `jvasseur`) · `Order Items` (count: 1, 10…) · `Payment …` · `Payment Type` (`ApplePay`, `CreditCard`, `PayPal`) · `Total` · `Subtotal` · `Shipping Charged`(?) · `Shipping …`(truncated) · `Handling` · `Tax Total` · `Donation` · `Currency` (`USD`) · `Final Value Fee`(?) · `Payment …` (truncated, small numbers).
- **Arithmetic visible in the data (row 122):** Subtotal 32.47 + Shipping 11.44 + Handling 3 + Tax 2.67 = Total 49.58. So `Total` includes shipping, handling and tax; **`Subtotal` is the merchandise amount.**
- **One row per order** (the `Order Items` column carries the item count). The header is **row 1**: "Customer Count is the Count of the Rows minus the Title Row" (slide 26). Staff put a `SUM` under the Subtotal and Shipping columns (row 130 shows 13,247.47 and 1,452.03), so the daily figures they report are those column sums.
- **Customers:** `Channel Buyer` exists, but staff count **rows** (orders), not distinct buyers. This is the first real answer to the customer-count question (Q6): the current practice is orders.

## Cash Monkey, Orders Report
- **How it is produced** (slides 27-30): CashMonkey Console, Reports, Orders. Form fields: Order Date From / To (**"required - inclusive - UTC"**, shown as `2026-09-30`), Accounts (`276 - Goodwill Michiana`, `277 - Goodwill Michiana (Stores)`), Channel (multi-select: `Amazon-MF`, `eBay`, `Goodwillbooks`), Order IDs, SKUs, checkboxes (Tax Columns, Debug TZ, Include Non-CM orders, Include Non-standard channel info), Format `csv`, Scheduled Report. Submit; the page then shows "file download: `orders2023-20261001-132256-96170.csv`" as a link.
- **File name pattern:** `orders2023-<YYYYMMDD>-<HHMMSS>-<number>.csv`.
- **"One line per unit"**, with "shipping costs and market fees pro-rated to each unit" and non-USD orders auto-converted to USD ("2024-08-20: Orders in Non-USD orders are now auto-converted into USD"). So **a multi-item order is several rows**, and fees are already split per row.
- **Dates are UTC.** A UTC date near midnight belongs to a different Eastern day, which is exactly the day-boundary problem the pulse has to get right.
- **Columns: UNKNOWN.** The deck never shows the CSV. The report description says it has order, source, quantity, net revenue, profit (slide 28 text: "items ordered, source, quantity, net revenue, profit"). Any column list in a generator is a guess.

## ShopGoodwill (direct) and Goodwill Books
- Slide 38: ShopGoodwill = "Periodic marketplace reports; filter year/month; Period 1 periodic only; Period 3 all reports". Goodwill Books = prior-month payment statement, a monthly email attachment. Neither is shown. Both appear to be **month-end** inputs. UNKNOWN whether either is used nightly.

## What this changes
1. The nightly **ShopGoodwill** file is Upright Paid Orders, not a "ShopGoodwill Orders" export. Its layout is partly known (above).
2. The nightly **eBay and Amazon** numbers probably come from one Cash Monkey file with a `Channel` column, not two seller-portal reports. If so, one parser splits by channel; the sample set should be one multi-channel `orders2023-*.csv`.
3. Dates arrive in **different timezones per source** (Upright: chosen by the user, Pacific by default; Cash Monkey: UTC). The day boundary must be a per-source setting.
4. Customer count today = rows, so `customer_basis = order` is the faithful default for ShopGoodwill, not `buyer`.
5. Acquisition is **asynchronous** on Upright (generate, wait, download). A scraper must poll *Past reports*.

## How to make the synthetic files as close as possible
- Follow this document, and mark every guessed column in the generator as a guess.
- Reproduce the **mess the deck proves**, not invented mess: a title/header row 1, a totals row under the data (Upright), multi-row orders (Cash Monkey, one line per unit), UTC timestamps, mixed payment types, `USD` currency column, a `(4)` style duplicate-download suffix in the file name.
- Ask Amanda for **one real file of each** (even with names scrambled). A single Cash Monkey CSV settles the column list that nothing else can.
