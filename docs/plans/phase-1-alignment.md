# Phase 1 against the deck: does the nightly pulse give Goodwill what the slides ask for?

Checked 2026-10-03 against slides 19-31 of the SprintHack deck (`innovationsprintlab.com/sprinthack-deck/sprinthack.html#19` to `#31`; slide 32, the monthly dashboard, is where phase 2 starts) and the code on `main`. **Verdict: the core of the nightly pulse matches the slides. Two wording and layout gaps are cheap to close, and four questions only Amanda can settle.** Nothing here is based on a real Goodwill file; see `docs/ASSUMPTIONS.md`.

## What the slides ask for
- **Slide 19 (Debie, in her words):** "A nightly report creates a daily pulse. Each nightly report should show both revenue and customer count by marketplace, followed by enterprise totals."
- **Slide 31 (the report layout):** a table with rows **ShopGoodwill, Amazon, eBay, Other e-commerce channels, Total e-commerce**, and columns **Daily revenue** and **Daily customers**. Footnote: "Other marketplaces can be added as separate rows as the channel mix evolves."
- **Slides 21-30 (how staff do it today):** Upright (6 steps: Reports, Paid orders, set the date, generate, download, count) and Cash Monkey (4 steps: Orders Report, pick dates, click the link). Slide 26: "Customer count = rows minus the title row. Then these numbers are entered on the Daily Summary Spreadsheet."

## Requirement by requirement
| # | The slides ask for | What phase 1 does | Status |
|---|---|---|---|
| 1 | Revenue and customer count **by marketplace**, then **enterprise totals** (19, 31) | The pulse (`out/pulse/<date>.json`, the HTML page, the CSV, the email copy) shows revenue, customers, orders, refunds and fees per marketplace and an enterprise total. Extra columns are additions, not changes. | **Aligned** |
| 2 | Four rows: ShopGoodwill, Amazon, eBay, **Other e-commerce channels** (31) | Four rows in the same order (`shopgoodwill`, `amazon`, `ebay`, `other`). | **Aligned** |
| 3 | The row is called **"Other e-commerce channels"** and the total is **"Total e-commerce"** (31) | The page says "Other" and "Enterprise total" (`reports/pulse.py`, `LABELS`). | **Wording gap** (Orlando's renderer) |
| 4 | An "Other" row that is always there (31) | `other` is shown only when a source feeds it. With no Goodwillbooks rows the pulse marks it `not_configured` and the renderer may hide it (`docs/contracts/pulse.md`). | **Layout gap**: show the row with a dash |
| 5 | "Other marketplaces can be added as separate rows" (31) | Adding a **source** is one file in `engine/sources/`. Adding a **marketplace** needs a contract change, because the pulse always has exactly four keys. | **Partly**: fine for this weekend, state it as a limit |
| 6 | **Customer count = rows** of the Upright report (26) | Upright: `customer_basis = order`, so the pulse counts orders, matching the staff practice. The buyer id is still kept. | **Aligned** |
| 7 | The same rule for Cash Monkey | Cash Monkey exports **one line per unit**. We count **distinct orders**. If staff count rows there, a 3-unit order is 3 customers to them and 1 to us. | **Open question** (Q below) |
| 8 | Numbers go into a **Daily Summary Spreadsheet** (26) | Our CSV and page replace it, but we have never seen its layout. | **Open**: ask for it; the CSV could mirror it |
| 9 | Manual download steps (21-25, 27-30) | Automated by Amanda's assumed API and emailed Excel; the engine reads the attachment. The API clients are stubs, and `python -m engine fetch --simulate` demos all four providers (Upright, Cash Monkey, Amazon, eBay) with synthetic reports. Cash Monkey's report form has a **"Scheduled Report"** option (slide 30), so it may need no API at all. | **Aligned by assumption**, disclose |
| 10 | Day boundary | Eastern midnight to midnight. Upright's form defaults to Pacific (slide 24) and Cash Monkey is UTC (slide 30); both are converted per source. 9 PM Pacific is midnight Eastern, so the cutoff Amanda gave lines up. | **Aligned** |
| 11 | When the report is produced | The slides' own evidence: the report form is set to **9/30** (slide 23) and the Cash Monkey file is stamped **20261001-132256** (slide 30). So today staff pull the previous day's data the **next day, around 1:22 PM** (the zone of that stamp is not stated). Our run is just after midnight Eastern (decision 004), earlier than today. | **Better than today, but not what staff do now**; run time still to confirm |
| 12 | "Revenue for the day" (31) | Not defined on the slide. Staff total the `Subtotal` **and** `Shipping` columns separately (slide 26, row 130). We report merchandise revenue (`Subtotal`), net of refunds, with fees separate. The engine now outputs `shipping_cents` and `handling_cents` on every row (`transaction.md` v0.4) and the month-end close uses them, but **the pulse page does not show shipping**. | **Open** (revenue definition, Q5); shipping is in the data, not on the pulse page |
| 13 | Total is **e-commerce** only (31) | Brick and mortar is out of scope (meeting); the enterprise total is the e-commerce total. | **Aligned** |
| 14 | A missing download | Not on the slides. We show "No data", never $0, and leave the source out of the total. | Our own safeguard |

## Two risks the slides raise that we had not written down
1. **Cash Monkey may be the Books operation only.** Slide 27's caption reads "Books: open Cash Monkey reports". If so, the eBay and Amazon numbers from it cover Goodwill Books sales, not all of Goodwill's eBay and Amazon sales.
2. **Upright's other channels are ignored on purpose.** Its menu also lists "eBay listings" and "Goodwillfinds listings" (slide 24 screenshot). We take only `Shopgoodwill` rows from Upright, to avoid double counting against Cash Monkey. If Upright carries eBay or Goodwillfinds orders that Cash Monkey does not, the pulse **under-counts** eBay and Other.

## What to fix, and who
| What | Who | Size |
|---|---|---|
| Rename the labels to "Other e-commerce channels" and "Total e-commerce" (row 3) | Orlando (`reports/pulse.py`) | S |
| Always show the Other row, with a dash when empty (row 4) | Orlando, and Dani's `pulse.md` wording ("may show a dash or hide") | S |
| ~~Add `shipping_cents` and `handling_cents` to `transactions.csv`~~ **Done.** Decide whether the pulse page shows them, once Amanda answers the revenue question | Dani and Orlando | S |
| Mention in the pitch that adding a marketplace needs a contract change (row 5) | Orlando | S |

## Questions for Amanda (added to `docs/office-hours-victor.md`)
1. **Cash Monkey customers:** do staff count rows (units) or orders? (row 7)
2. **Daily Summary Spreadsheet:** can we see its layout, so the pulse CSV can mirror it? (row 8)
3. **Is the Cash Monkey report only Goodwill Books,** and where do the non-book eBay and Amazon sales come from? Does Upright carry eBay or Goodwillfinds orders we should count under Other? (risks 1 and 2)
4. **Revenue:** `Subtotal` only, or `Subtotal` plus shipping (row 12)? And what time do staff want the report (row 11)?

## Phase 2 starts at slide 32: the KPI contract and the KPI identification (marked for Dani and Orlando)
**Owners.** The KPI contract is `docs/contracts/kpi.md` (Dani, `recon/kpi/`). The **identification of the KPIs** is its 15 stable ids (`fin.revenue`, `prod.listings_created`, ...), their names and their five areas. Orlando renders them (scorecard page, print layout) and decides the headings. Victor only exports the file (CSV, PDF, email). Neither of us should rename an id without a change to `kpi.md`.

**The gap.** Slide 32 names five *pillars*: **Growth, Profitability, Productivity, Inventory, Engagement**. The contract follows slide 35's five *areas* (`financial`, `productivity`, `inventory`, `sales`, `category_customer`). Both are Goodwill's own words, but the pillar names appear nowhere in our contract or page, so the dashboard does not yet say "Growth" or "Engagement" anywhere Debie would look for them.

**Proposed mapping** (Dani and Orlando to confirm or change; the ids are unchanged, only a label is added):
| Slide 32 pillar | KPI ids from `kpi.md` | Note |
|---|---|---|
| Growth | `fin.revenue`, `fin.revenue_growth` | Slide 33 says year over year; we compare with the prior period until 13 months are stored (stated in `kpi.md`). |
| Profitability | `fin.net_margin`, `cat.top_margin` | Needs internal cost data (mock, labelled). |
| Productivity | `prod.listings_created`, `prod.revenue_per_labor_hour`, `prod.listings_per_employee`, `sales.sales_per_employee` | Internal data (mock, labelled). |
| Inventory | `inv.days_donation_to_listing`, `inv.unlisted_backlog`, `inv.unsold_pct`, `sales.sell_through` | Internal data (mock, labelled). |
| Engagement | `cust.repeat_buyer_rate` | The only customer KPI we can compute from real files. Needs a buyer id: Upright has one, Cash Monkey has none (see `docs/PHASE1_ALIGNMENT.md`, row 7). |
| (no pillar) | `fin.revenue`, `sales.asp`, `cat.top_revenue` | Slide 35 groups these under Financial, Sales and Category. Show them under the area name, or attach a pillar if the team prefers. |

**Two things to settle with the mapping.** (1) Either add a `pillar` field per KPI in `kpi.md` (Dani) or keep the mapping as labels on the page (Orlando); one place only, so they cannot disagree. (2) `sales.asp` and `sales.sell_through` need a `units` column that `transactions.csv` does not have yet (the store schema has the column, empty); until it exists those two show as partial.
