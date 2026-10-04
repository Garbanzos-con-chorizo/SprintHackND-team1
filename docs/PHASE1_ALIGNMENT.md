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
| 9 | Manual download steps (21-25, 27-30) | Automated by Amanda's assumed API and emailed Excel; the engine reads the attachment. The Upright API client is a stub. Cash Monkey's report form has a **"Scheduled Report"** option (slide 30), so it may need no API at all. | **Aligned by assumption**, disclose |
| 10 | Day boundary | Eastern midnight to midnight. Upright's form defaults to Pacific (slide 24) and Cash Monkey is UTC (slide 30); both are converted per source. 9 PM Pacific is midnight Eastern, so the cutoff Amanda gave lines up. | **Aligned** |
| 11 | When the report is produced | The slides' own evidence: the report form is set to **9/30** (slide 23) and the Cash Monkey file is stamped **20261001-132256** (slide 30). So today staff pull the previous day's data the **next day, around 1:22 PM** (the zone of that stamp is not stated). Our run is just after midnight Eastern (decision 004), earlier than today. | **Better than today, but not what staff do now**; run time still to confirm |
| 12 | "Revenue for the day" (31) | Not defined on the slide. Staff total the `Subtotal` **and** `Shipping` columns separately (slide 26, row 130). We report merchandise revenue (`Subtotal`), net of refunds, with fees separate, and **do not report shipping at all**. | **Open** (revenue definition, Q5) |
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
| Decide whether to report shipping separately (row 12) | Dani, after Amanda answers | S |
| Mention in the pitch that adding a marketplace needs a contract change (row 5) | Orlando | S |

## Questions for Amanda (added to `docs/office-hours-victor.md`)
1. **Cash Monkey customers:** do staff count rows (units) or orders? (row 7)
2. **Daily Summary Spreadsheet:** can we see its layout, so the pulse CSV can mirror it? (row 8)
3. **Is the Cash Monkey report only Goodwill Books,** and where do the non-book eBay and Amazon sales come from? Does Upright carry eBay or Goodwillfinds orders we should count under Other? (risks 1 and 2)
4. **Revenue:** `Subtotal` only, or `Subtotal` plus shipping (row 12)? And what time do staff want the report (row 11)?

## Phase 2 starts at slide 32
Slide 32 names five pillars: **Growth, Profitability, Productivity, Inventory, Engagement**. Slides 33-35 turn them into the KPI framework, and the 15-KPI COO scorecard on slide 35 is grouped as Financial, Productivity, Inventory, Sales, Category + Customer. Our KPI contract and decision 006 follow slide 35's grouping. The pillar names on slide 32 are not used as headings anywhere, so the dashboard should either show them or state the mapping (Growth and Profitability sit inside Financial, Engagement is Customer). That is a phase 2 point for Dani and Orlando.
