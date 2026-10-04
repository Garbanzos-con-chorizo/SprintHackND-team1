# Assumptions: what we assumed, why, and what would settle it

Our brief is broad and we have no real Goodwill files yet, so we decided early to **state every assumption instead of hiding it**. Each one is cheap to change: it lives in one place in the code (named below), and a real file or one answer from Amanda replaces it. This list is meant to be read in the pitch and in "built versus used".

**Confidence:** `from the deck` = read off the SprintHack slides (slide number given) · `default` = we picked the most common reading and it is a one-line change · `guess` = nothing we have shows it · `decision` = a choice we made as a team.

## 1. What we are solving (scope)
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 1.1 | The **nightly pulse is the first deliverable** and the month-end close is the real prize. We build the pulse end to end first. | It is the smallest piece that runs live in a demo, and its parsing and cleaning are reused by the close. | decision |
| 1.2 | Output is a **Business Central-ready import file, not a live posting**. | We have no sandbox and no credentials. Overclaiming "integration" is penalized, so we say what is real. | decision |
| 1.3 | All demo data is **synthetic and labelled so**. | No real data yet. Disclosure is a judging criterion. | decision |
| 1.4 | **Brick and mortar is out of scope.** It is independent of the e-commerce work, so we ingest no B&M reports and the **enterprise total is the e-commerce total**. | Decided in the meeting; slide 31 also titles the total "Total e-commerce". | from the meeting |

## 2. Where the data comes from
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 2.1 | The nightly **ShopGoodwill** numbers come from **Upright's "Paid orders" report**. | Slide 26 shows that spreadsheet with a `Channel` column reading `Shopgoodwill`, and staff count customers from it. | from the deck |
| 2.2 | The nightly **eBay, Amazon and "Other"** numbers come from **one Cash Monkey "Orders Report"** filtered by channel (Amazon-MF, eBay, Goodwillbooks). | Slide 30 shows that form, "orders across all market places", with exactly those channels. | inferred from the deck, **needs Amanda to confirm** |
| 2.3 | The seller-portal reports on slide 38 (eBay "Listing sales", Amazon "Payments summary", ShopGoodwill periodic, Goodwill Books statement) are **month-end inputs, not nightly**. | They are listed under the monthly close and are described as monthly or periodic. | inferred |
| 2.4 | **"Other" = Goodwillbooks only.** | It is the only other channel on the Cash Monkey form. | default |
| 2.5 | Upright rows have a **payment date** (header spelling guessed: `Payment Date`), written **without a timezone in Pacific time**, the report form's default (slide 24: "Use America/Los_Angeles for SGW"). We convert it to Eastern. If the file has no date column, the day falls back to the file name. | The form's timezone field defaults to Pacific; exported timestamps carry no zone. If staff pick another zone, it is one line in `engine/sources/upright.py`. | guess |
| 2.6 | **Other Upright channels are ignored**: only `Shopgoodwill` rows count. | If Upright also carried eBay or Amazon orders, counting them would double-count against Cash Monkey. | decision |
| 2.7 | **Cash Monkey's eBay and Amazon rows are the whole eBay and Amazon story for the pulse.** Slide 27's caption says "Books: open Cash Monkey reports", so it may cover only the Goodwill Books operation, and Upright's "eBay listings" and "Goodwillfinds" channels are ignored (2.6). If either carries sales Cash Monkey does not, the pulse **under-counts** eBay and Other. | We can't tell from the deck. Counting Upright's other channels risks double counting against Cash Monkey; ignoring them risks under-counting. | **risk, to confirm with Amanda** (`docs/PHASE1_ALIGNMENT.md`) |
| 2.8 | **Cash Monkey, Amazon and eBay all deliver in the Cash Monkey report layout** (header in row 1, one line per unit, a `Channel` column, UTC order dates), so one parser reads them and a column or two is dropped to make the table. Each provider covers its own channel: Cash Monkey's own store (Goodwillbooks, the `other` row), Amazon (`Amazon-MF`), eBay (`eBay`). | Simplification agreed with the team. It matches the one real layout we have evidence for (slides 27-30) and keeps the three providers from overlapping. In reality Cash Monkey's report may carry all three channels in one file (slide 30), which the same parser also reads. | decision (simplification) |

## 2b. Goodwill's internal data (the internal API)
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 2b.1 | **All of Goodwill's internal company data comes from an internal API**: inventory and backlog, listings, donation and listing dates, labor hours and employee headcount, cost of goods, product categories, the Business Central chart of accounts. | The marketplace exports contain none of it, and 11 of the 15 scorecard KPIs (slide 35) need it. Assuming one API keeps every such input in one replaceable place. | decision (`006` point 9, `007`), **not confirmed with Amanda** |
| 2b.2 | **We have not seen that API, so it is a mock with synthetic values.** Every response carries `"source": "mock"` and every number built on it is badged "Simulated internal data" on the page, in the PDF and in the CSV. | Inventing figures and presenting them as Goodwill's would be an overclaim. | decision (`reports/mock_api.py` today, `engine/internal_api/` in the plan) |
| 2b.3 | The API answers **read-only JSON for a date or a date range**, and for stock-like figures (backlog, active listings, headcount) it gives **only the current state**. The nightly run stores a snapshot in our database so those figures have history. | Typical of operational systems; it is also why the KPIs read the database and never call the API directly. | guess |
| 2b.4 | The synthetic values are **sized to the sample order volume**, not to Goodwill's real operation. | So the simulated ratios look plausible next to the sample revenue; they prove the calculation, not the result. | decision |
| 2b.5 | **August's orders are simulated too.** The demo store holds September from the `clean_month` sample and August from the provider simulators (`engine fetch --simulate --from --to`), so September's Revenue Growth has a month to compare with. | The simulators use their own daily volumes (about 1.5 times the sample's), so the growth shown (about -33%) is an artefact of two synthetic sources, **not a trend**. | Say so if asked; never present it as a real month-on-month change. A real August replaces it. |

## 2c. Month-end sources we have never seen (the close)
Decided by Dani, 2026-10-04, for phase 3 (`docs/PLAN_PHASE_3.md`, decision 009). **Planned, not yet built**: each row becomes true of the code when its task lands (V3.5, V3.7 to V3.10, D3.14), and the close page marks each of these sources "simulated API". **To ask Debie on Sunday** (plan, section 6, question 16 first).

| # | Assumption | Why | Confidence |
|---|---|---|---|
| 2c.1 | **Each month-end source we have no file for can be fetched through an API** (or a report that is scheduled and emailed, which lands in the same inbox): Cash Monkey's full-month Orders report, the Jewelry report, the bank's activity for account 0101 (OSM, PB, EasyPost), Business Central's ledger entries (FedEx), ShopGoodwill's periodic reports, the Goodwill Books statement. | Amanda told us to assume an API for Upright (3.1); we extend that to the six sources of slide 38 nobody has shown us. Cash Monkey's form has a "Scheduled Report" box (slide 29); the slide itself says the Books statement is a "monthly email attachment". | decision, **not confirmed: ask Debie** |
| 2c.2 | **None of those APIs has been seen, so each is a simulator with synthetic values and a layout we made up.** `python -m engine fetch --simulate --close-month M` writes the files, the fetch log marks each `simulated: true`, and the close page says "simulated API" beside the source. | Presenting an invented file as Goodwill's would be an overclaim. | decision |
| 2c.3 | **"Supplier" on the Jewelry report is the Goodwill store that supplied the item**, and "Co-Pivot populates Supplier" is a lookup that fills it in. | Upright's home page shows "Weekly supplier sales by store" (slide 21) and has a Suppliers report. What the close does with the supplier is unknown, so we only show jewelry sales by supplier. | guess |
| 2c.4 | **"1st Source acct 0101 • GL 10009" is a bank account at 1st Source whose account in Business Central is G/L 10009**, and the carriers (OSM, PB, EasyPost) are paid from it. We treat it as a second account, separate from the one the marketplaces pay into. | The slide gives the two codes side by side under "shipping amounts". | guess |
| 2c.5 | **FedEx's month is the ledger entries on G/L 40356, department 180, vendor V00122, minus the refunds that came back as bank deposits (documents marked BNKDEPOSIT).** | The four codes are on slide 38; how they combine is our reading of "net BNKDEPOSIT refunds". | codes from the deck, meaning guessed |
| 2c.6 | **ShopGoodwill's periodic report lists its payouts with the period each one covers**, and the Goodwill Books statement lists the prior month's sales, fees and net payment, posted in the month it is paid. What "Period 1" and "Period 3" mean is unknown and not modeled. | Slide 38 names both reports and shows neither. | guess |
| 2c.7 | **Cash Monkey's month file is a cross-check, not a second count.** eBay and Amazon post from their own reports; Cash Monkey's totals for the same marketplaces are shown beside them. | Both files hold the same sales; adding them would double the revenue. Which one Goodwill's workbook uses is unknown. | default, **open** |

## 3. How the data gets in (acquisition)
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 3.1 | **An API exists for Upright** and can generate the Paid orders report; Upright then **emails it as an Excel attachment**. | Amanda told us to assume this (office hours, 2026-10-03). The deck agrees: "generate; email delivery" (slides 24-25, 38). | **from Amanda** (`docs/decisions/005-api-email-delivery-and-run-schedule.md`) |
| 3.2 | We **do not know the API's endpoint or fields**, so the Upright client is a stub that says "not configured" instead of pretending. | Nobody has seen the API. Inventing it would be an overclaim. | decision |
| 3.3 | **The email arrives in a folder**: an email rule saves the attachment into `inbox/`, and the engine reads the folder. Reading a live mailbox is a later step that needs Goodwill's approval. | Lightest bridge, no mailbox credentials needed, same code path as a manual drop. | decision |
| 3.4 | **Excel is read directly; there is no Excel-to-CSV step.** The engine writes the CSV (and two JSON files) that Dani's code reads. | A converter would add a step with no benefit. Amanda said converting to CSV is fine if CSV isn't offered, so we remain compatible either way. | decision |
| 3.5 | **Browser automation was removed.** | With an API assumed there is no login screen to automate; the dependency and its code were dead weight. | decision (`005`) |
| 3.6 | **File drop stays as the fallback** for any source whose API or email isn't set up. | A demo must not depend on an integration we can't test. | decision |
| 3.7 | **An ERP drop is a CSV or Excel file** and works only if a parser exists for its columns. | No ERP details were given. | default |
| 3.8 | The **mock scraper is a stub**: it is handed the records a scraper would extract and runs them through the same parser as a file. No login, network, paging or retries. | It demonstrates the pluggable design without touching a live site. | decision (`engine/ingest/scraper_adapter.py`) |
| 3.8b | **Each provider has an API simulator** (`python -m engine fetch --simulate`): Upright, Cash Monkey, Amazon, eBay. A simulator writes the report the provider would have emailed (an `.xlsx`, synthetic, the same for the same date) into the inbox, and the normal pipeline reads it. The fetch log marks every such entry `simulated: true`. Without `--simulate` the real API stubs still say "not configured". | A demo that shows the whole path (request, emailed report, pulse) without an API we have never seen. Marking the log means a run can't pass synthetic data off as real. | decision (`engine/scrapers/simulation.py`) |
| 3.9 | Supported inputs are **.csv, .tsv, .txt, .xlsx**. Legacy **.xls is reported as a warning, not read**. First sheet only. | Standard library plus `openpyxl`; a silent skip would hide a missing report. | decision |
| 3.10 | **Credentials come from the environment or an ignored `.env`.** No agent types them and nothing is committed. | Safety and the "no secrets in git" rule. | decision |

## 3b. When it runs (schedule)
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 3b.1 | **The pipeline runs once a day at a fixed time**, so the e-commerce pulse is produced at the same moment the brick-and-mortar report goes out. | Staff get both reports together; one run is simplest to explain and to operate. | from the meeting |
| 3b.2 | **E-commerce reports finalize at 9:00 PM PT = 12:00 AM ET**, every day of the year. A business day is complete only after midnight ET. | From the meeting. PT and ET change clocks together, so the offset never moves. | from the meeting |
| 3b.3 | **Default run time: just after 12:00 AM ET, reporting the day that just ended.** | The e-commerce day is final only after midnight ET, and B&M's 10 PM report is already in by then. Matches decision 004. Alternatives (1 PM next-day, or 10 PM partial day) are in decision 005. | assumption, **time to confirm with Amanda** |
| 3b.4 | **`python -m reports.run_nightly` stands in for the scheduler** and runs once when called. Windows Task Scheduler or cron would call it in production. We disclose it as a stand-in, not a real scheduler. | A real scheduler needs a server we don't have for the demo. | decision (Orlando's O4) |
| 3b.5 | **No "late" state.** A report that hasn't arrived by the run is shown as "no data" and the next run picks it up. | With one run a day, "late" and "missing" look the same to the reader, and a separate state would need a contract change for no gain. | decision |
| 3b.6 | **Today staff pull the previous day's data the next day, around 1:22 PM.** The report form is set to 9/30 (slide 23) and the Cash Monkey file is stamped `20261001-132256` (slide 30); the zone of that stamp is unknown. Our automated run (just after midnight Eastern) is therefore earlier than the manual process, not the same. | Evidence read off the slides. It also makes the 1 PM option in decision 005 the one that mirrors today's practice. | inference from the deck |

## 4. What the numbers mean (definitions)
Open questions for Amanda are in `docs/OFFICE_HOURS.md` and `docs/office-hours-victor.md`. Until answered:

| # | Assumption | Why | Confidence |
|---|---|---|---|
| 4.1 | **Revenue = merchandise amount** (Upright `Subtotal`, Cash Monkey `Item Price`), **excluding shipping, handling and tax**. | Slide 26 shows Total = Subtotal + shipping + handling + tax, and staff total the Subtotal column. Shipping and tax are not Goodwill's sales revenue. | default, partly from the deck (`engine/sources/*.py`) |
| 4.1b | **Shipping and handling are reported separately and are never revenue.** The engine outputs them on every row (`shipping_cents`, `handling_cents`) and the month-end close uses them to work out what each marketplace owes (the close reads only the engine's files, never an answer key). The pulse page does not show them. Staff total the `Subtotal` and `Shipping` columns separately (slide 26, row 130). | Shipping is not Goodwill's sales revenue, but they track it, so they may want it on the pulse. eBay reports shipping and handling as one amount, so all of it counts as shipping. | default, **open** (Q5) |
| 4.2 | Revenue is **net of refunds**, and a **refund counts on the day it is issued**, not the original order day. | The pulse is a daily view of what happened that day. | default |
| 4.3 | **Marketplace fees are reported separately**, never subtracted from revenue. | Keeps revenue comparable to the staff's figure and shows fees on their own. | default |
| 4.4 | **Customer count = number of orders** for Upright (staff count rows even though a buyer column exists) and for Cash Monkey (no buyer column), **unique buyers** only where a source gives a buyer id and staff don't count rows. The report labels which. | Slide 26: "Customer Count is the Count of the Rows minus the Title Row", so staff count rows today. | from the deck (orders) + default (buyers) |
| 4.5 | **Enterprise customers = the sum of the marketplace counts.** | The same person can't be matched across marketplaces. | default |
| 4.6 | **The business day is the Eastern day.** | Goodwill Michiana is in Indiana. The sources disagree: Cash Monkey writes UTC, Upright lets the user pick a zone (default Pacific). | default (`engine/contract.py`, per-source zone in each parser) |
| 4.7 | **Unit amounts are USD.** Non-USD rows are rejected with a warning. | Cash Monkey auto-converts to USD (slide 30 note). | from the deck |
| 4.8 | A **missing or empty source is shown as "no data", never as $0**. | A $0 would look like a real quiet day and hide a failed download. | decision |
| 4.9 | **Cash Monkey customers are counted as distinct orders.** Its export is one line per unit, so if staff count its rows (as they do Upright's), a 3-unit order is 3 customers to them and 1 to us. | Slide 26 only says how Upright is counted. | **open question** (`docs/PHASE1_ALIGNMENT.md`) |

## 4b. What the scorecard KPIs mean
The open definitions of the 15 KPIs (growth against the prior period, what "unsold" means, who counts as an employee, what margin includes) are listed with their defaults in `docs/contracts/kpi.md`, "Open questions". One is a real assumption about the data:

| # | Assumption | Why | Confidence |
|---|---|---|---|
| 4b.1 | **Which listing a sale came from is taken from the listing system, which today is the mock.** Sell-through's two boxes ("Listed in the period", "Left from earlier") split what sold by listing date, using the internal API's sales by days since listing (`listing_to_sale_days`). That data is simulated, and the boxes are badged like every simulated number. If the metric is missing for a period, the calculator falls back to assuming that what was listed in the period sells first, and the note on the page says so. | No export says which listing a sale came from. Goodwill's listing system knows each item's listing date; we have not seen that data. | assumption (`recon/kpi/kpis.py`, `_boxes`; `engine/internal_api/mock.py`) |

## 5. How we clean the data
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 5.1 | The **same transaction in two files counts once** (the first copy wins, the rest are logged). If two copies disagree on amount or date, the log says so. | Staff re-download and ranges overlap. Counting twice inflates revenue; silently choosing hides a conflict. | decision (`engine/dedupe.py`) |
| 5.2 | **Several lines of one order become one row** (Cash Monkey is one line per unit). | The pulse counts orders, not units. | from the deck |
| 5.2b | **In a one-line-per-unit export (Cash Monkey), identical lines in one file are separate units, not duplicates.** Two units of the same item at the same price are two identical lines and both count. Re-downloaded files are still deduplicated across files. | Dropping one would understate revenue. The cost: a line pasted twice by hand into one Cash Monkey file would be double counted (not logged). | decision (`engine/sources/cashmonkey.py`) |
| 5.3 | A **bad row never stops a run**: it is skipped and recorded in `warnings.json`. | A nightly job that dies on one bad cell produces no report at all. | decision |
| 5.4 | **Buyer emails are hashed** before they reach the output. | Donor and customer privacy (office-hours question 27). | decision |
| 5.5 | **Payout and transfer rows are not sales** and are skipped. | They are money movement for the close, not revenue. | default |

## 6. The files we test with
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 6.1 | **Synthetic files copy only what the deck proves**: header in row 1, one row per order (Upright), one line per unit and UTC timestamps (Cash Monkey), a `(1)` suffix on re-downloads. | Inventing realistic-looking detail we cannot back up would make our tests agree with ourselves. | decision (`docs/contracts/source-formats.md`) |
| 6.2 | **Cash Monkey's column names are guesses.** The deck never shows that CSV. Upright's header spelling is partly guessed (some headers are cut off). | One real file settles it; each parser holds the names in one block. | guess |
| 6.3 | **Refunds in Cash Monkey are rows with a negative item price.** | Unknown how it really exports refunds. | guess |
| 6.4 | **The answer key is computed from the generated orders, not by our engine.** | A check that reuses the engine's own logic proves nothing. We also test that the check *fails* when the key or the timezone logic is wrong. | decision (`engine/tools/make_sample.py`) |

## 7. How we work
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 7.1 | The engine is **Python**, and teammates read **files, not code**. | Fastest to build; the contract is the files, so Dani and Orlando may use anything. | decision (`002`) |
| 7.2 | Ingestion lives in **`engine/`** (not a new top-level folder). | Our rules allow new top-level folders only through a decision record. | decision |

## What would change the most
1. **One real Cash Monkey CSV** replaces 2.2, 6.2 and 6.3 with facts.
2. **One real Upright download** settles 2.5 and the Upright column names.
3. **The Upright API documentation** replaces 3.1 and 3.2 with facts.
4. **Amanda's answers** on revenue, the day boundary, customers and the run time (3b.3) settle sections 3b and 4.
5. **Where the internal data really lives** (Upright's listing and productivity reports, payroll hours, cost data) replaces section 2b: each real source becomes one client behind the same interface as the mock.
