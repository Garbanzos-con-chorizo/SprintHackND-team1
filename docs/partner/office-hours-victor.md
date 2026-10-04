# Office hours questions: Victor (data acquisition and engine)

Asked of Amanda Baumer, 2026-10-03. Priority order; answers go in Orlando's `docs/decisions/001-partner-answers.md`. Based on what the deck shows (`docs/contracts/source-formats.md`). The general list is in `docs/OFFICE_HOURS.md`.

## Ask first: these unblock the build
1. **One real file of each report**, names scrambled if needed: the Upright Paid Orders download, the Cash Monkey Orders CSV, plus whatever they use for eBay and Amazon. One Cash Monkey CSV settles columns the deck never shows. A screenshot of the header row beats nothing.
2. **Where does each nightly number come from?** Our reading: ShopGoodwill from Upright Paid Orders; eBay, Amazon and Goodwillbooks from one Cash Monkey Orders Report filtered by channel. Or do they use Seller Center / Seller Central for the nightly numbers?
3. **A read-only or sandbox login for Upright and Cash Monkey**, or a HAR file (browser network export, secrets removed) from one staff run, to automate the downloads. Can Upright email the report on a schedule (slide 38 mentions email delivery)? That could replace scraping.
4. **Who runs this, on what machine, and is there IT policy** on installing software, storing credentials, or sending data to cloud services?

## Definitions: these change the numbers
5. **Revenue:** staff sum the `Subtotal` and `Shipping` columns. Is headline revenue Subtotal, or Subtotal plus shipping (and handling)? Net of refunds? Before or after marketplace fees?
6. **Day boundary:** Upright's report has a timezone field (default Pacific), Cash Monkey is UTC. Which day counts: Eastern, Pacific, or the export's own? When do they run it, and by what time must the report be ready?
7. **Customers:** we read the deck as counting rows, not distinct buyers. Confirm. With Cash Monkey's one-line-per-unit rows, do they count orders or lines?
8. **What goes in "Other"?** Only Goodwillbooks, or also in-store and anything else? Does the enterprise total include non-e-commerce revenue?

## If there's time
9. **Refunds:** do they come from Upright's "Refunds" report, and are they counted on the day issued?
10. **Missing or late download:** show "no data" and send anyway, or hold the report?
11. **Who reads the nightly pulse, and how:** email, PDF or a page?

## Status after the meeting (2026-10-03)
- **Answered:** Q3 (assume an Upright API; reports arrive as emailed Excel, we convert or read it directly), Q6 in part (e-commerce finalizes at 9 PM Pacific = midnight Eastern). Recorded in decisions 004 and 005.
- **Not answered:** Q1 (no real files yet), Q2, Q4, Q5 (revenue), Q7 (customers; the deck says staff count Upright rows), Q8 (what is Other), Q9 to Q11.

## New questions from checking phase 1 against the deck (see `docs/PHASE1_ALIGNMENT.md`)
12. **Cash Monkey customers:** do staff count rows (units) or orders?
13. **Daily Summary Spreadsheet** (slide 26): can we see its layout, so the pulse CSV can mirror it?
14. **Is the Cash Monkey report only Goodwill Books?** Where do non-book eBay and Amazon sales come from, and does Upright carry eBay or Goodwillfinds orders we should count under Other?
15. **Revenue:** `Subtotal` only, or plus shipping? Staff total both columns today.
16. **Run time:** the manual run is the next day around 1:22 PM. Do they want the automated report earlier (after midnight) or at the same time?
