# Assumptions: what we assumed, why, and what would settle it

Our brief is broad and we have no real Goodwill files yet, so we decided early to **state every assumption instead of hiding it**. Each one is cheap to change: it lives in one place in the code (named below), and a real file or one answer from Amanda replaces it. This list is meant to be read in the pitch and in "built versus used".

**Confidence:** `from the deck` = read off the SprintHack slides (slide number given) · `default` = we picked the most common reading and it is a one-line change · `guess` = nothing we have shows it · `decision` = a choice we made as a team.

## 1. What we are solving (scope)
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 1.1 | The **nightly pulse is the first deliverable** and the month-end close is the real prize. We build the pulse end to end first. | It is the smallest piece that runs live in a demo, and its parsing and cleaning are reused by the close. | decision |
| 1.2 | Output is a **Business Central-ready import file, not a live posting**. | We have no sandbox and no credentials. Overclaiming "integration" is penalized, so we say what is real. | decision |
| 1.3 | All demo data is **synthetic and labelled so**. | No real data yet. Disclosure is a judging criterion. | decision |

## 2. Where the data comes from
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 2.1 | The nightly **ShopGoodwill** numbers come from **Upright's "Paid orders" report**. | Slide 26 shows that spreadsheet with a `Channel` column reading `Shopgoodwill`, and staff count customers from it. | from the deck |
| 2.2 | The nightly **eBay, Amazon and "Other"** numbers come from **one Cash Monkey "Orders Report"** filtered by channel (Amazon-MF, eBay, Goodwillbooks). | Slide 30 shows that form, "orders across all market places", with exactly those channels. | inferred from the deck, **needs Amanda to confirm** |
| 2.3 | The seller-portal reports on slide 38 (eBay "Listing sales", Amazon "Payments summary", ShopGoodwill periodic, Goodwill Books statement) are **month-end inputs, not nightly**. | They are listed under the monthly close and are described as monthly or periodic. | inferred |
| 2.4 | **"Other" = Goodwillbooks only.** | It is the only other channel on the Cash Monkey form. | default |
| 2.5 | A single Upright file covers **one business day** and its rows carry **no date column**, so the day comes from the file name (`paid_orders_MM-DD-YYYY_...`). | No date column is visible in the slide-26 screenshot, and the report is generated for a date range. | guess (`engine/sources/upright.py`) |
| 2.6 | **Other Upright channels are ignored**: only `Shopgoodwill` rows count. | If Upright also carried eBay or Amazon orders, counting them would double-count against Cash Monkey. | decision |

## 3. How the data gets in (acquisition)
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 3.1 | We **automate what staff do by hand** (log in, run the report, download) per portal, and keep **file drop as the fallback**. | The deck's target is to automate downloads and rules. A scraper that is blocked or unfinished must not stop the demo. | decision (`docs/decisions/003-portal-acquisition.md`) |
| 3.2 | Each portal uses **plain HTTP or a real browser, chosen after one discovery pass**. | We cannot tell from the deck whether a download is one replayable request or needs clicks, MFA or a login token. | decision |
| 3.3 | Upright reports are **asynchronous**: generate, wait, download from "Past reports". | Slides 7-9 and 38 ("generate; email delivery"). | from the deck |
| 3.4 | **Credentials come from the environment or an ignored `.env`**. No agent types them and nothing is committed. | Safety and the "no secrets in git" rule. | decision |
| 3.5 | **"Email" means a folder**, not a mailbox connection: someone saves the attachment (or an email rule does) into `inbox/`. | Reading a live mailbox needs Goodwill IT approval we do not have. Slide 38 says Upright can email the report, so a folder rule is the lightest bridge. | decision (an IMAP adapter is the next step if IT allows) |
| 3.6 | An **ERP drop is a CSV or Excel file** and works only if a parser exists for its columns. | No ERP details were given. | default |
| 3.7 | The **mock scraper is a stub**: it is handed the records a scraper would extract and runs them through the same parser as a file. No login, network, paging or retries. | It demonstrates the pluggable design without touching a live site. | decision (`engine/ingest/scraper_adapter.py`) |
| 3.8 | Supported inputs are **.csv, .tsv, .txt, .xlsx**. Legacy **.xls is reported as a warning, not read**. First sheet only. | Standard library plus `openpyxl`; a silent skip would hide a missing report. | decision |

## 4. What the numbers mean (definitions)
Open questions for Amanda are in `docs/OFFICE_HOURS.md` and `docs/office-hours-victor.md`. Until answered:

| # | Assumption | Why | Confidence |
|---|---|---|---|
| 4.1 | **Revenue = merchandise amount** (Upright `Subtotal`, Cash Monkey `Item Price`), **excluding shipping, handling and tax**. | Slide 26 shows Total = Subtotal + shipping + handling + tax, and staff total the Subtotal column. Shipping and tax are not Goodwill's sales revenue. | default, partly from the deck (`engine/sources/*.py`) |
| 4.2 | Revenue is **net of refunds**, and a **refund counts on the day it is issued**, not the original order day. | The pulse is a daily view of what happened that day. | default |
| 4.3 | **Marketplace fees are reported separately**, never subtracted from revenue. | Keeps revenue comparable to the staff's figure and shows fees on their own. | default |
| 4.4 | **Customer count = number of orders** where we have no buyer id, and **unique buyers** where we do. The report labels which. | Slide 26: "Customer Count is the Count of the Rows minus the Title Row", so staff count rows today. | from the deck (orders) + default (buyers) |
| 4.5 | **Enterprise customers = the sum of the marketplace counts.** | The same person can't be matched across marketplaces. | default |
| 4.6 | **The business day is the Eastern day.** | Goodwill Michiana is in Indiana. The sources disagree: Cash Monkey writes UTC, Upright lets the user pick a zone (default Pacific). | default (`engine/contract.py`, per-source zone in each parser) |
| 4.7 | **Unit amounts are USD.** Non-USD rows are rejected with a warning. | Cash Monkey auto-converts to USD (slide 30 note). | from the deck |
| 4.8 | A **missing or empty source is shown as "no data", never as $0**. | A $0 would look like a real quiet day and hide a failed download. | decision |

## 5. How we clean the data
| # | Assumption | Why | Confidence |
|---|---|---|---|
| 5.1 | The **same transaction in two files counts once** (the first copy wins, the rest are logged). If two copies disagree on amount or date, the log says so. | Staff re-download and ranges overlap. Counting twice inflates revenue; silently choosing hides a conflict. | decision (`engine/dedupe.py`) |
| 5.2 | **Several lines of one order become one row** (Cash Monkey is one line per unit). | The pulse counts orders, not units. | from the deck |
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
3. **Amanda's answers** on revenue, the day boundary and customers settle section 4.
4. **A read-only login or a HAR file** settles 3.2.
