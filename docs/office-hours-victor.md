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
