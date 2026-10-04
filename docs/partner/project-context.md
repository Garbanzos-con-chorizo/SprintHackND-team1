# SprintHack@ND 2026 — Goodwill Michiana Project Context

> **Purpose of this file.** Context handoff for an AI assistant helping a student team at the SprintHack@ND hackathon. The team chose the **Goodwill Michiana** partner problem. Everything below was extracted from the official 95-slide event deck, the speaker notes embedded in it, the screenshots on the Goodwill slides, the official rubric page and the official problem-statement sheet.
>
> **Sources**
> - Deck: `https://innovationsprintlab.com/sprinthack-deck/sprinthack.html#N` (N = 1..95)
> - Rubric: `https://innovationsprintlab.com/go/rubric`
> - Problem statements: `https://innovationsprintlab.com/go/problems` (Google Sheet, "PROBLEMS" tab)
> - Submission form: `https://innovationsprintlab.com/go/submit`
>
> **Conventions.** Text in quotes or tables is verbatim from the source. Paragraphs marked **[Interpretation]** are the extracting AI's own reading, not something Goodwill or the organizers said. Treat them as hypotheses to verify with the partner.
>
> **Extracted:** Saturday, October 3, 2026 (day 1 of the event).

---

## 0. TL;DR

- **Event:** SprintHack@ND, Oct 3–4, 2026, Innovation Park (Notre Dame). A "reverse pitch" hackathon: partners pitch real operational problems, student teams build a working answer in a weekend.
- **Our partner:** Goodwill Industries of Michiana (e-commerce operation). **Our pod:** Pod B, Room 154.
- **The problem in one line (official brief):** "Reporting. Automate the recurring operations reports that staff put together by hand today."
- **Three sub-problems Goodwill described:**
  1. A **nightly report** — revenue and customer count per marketplace (ShopGoodwill, Amazon, eBay, other), then enterprise totals. Today it is built by hand by downloading reports from Upright and Cash Monkey and typing numbers into a "Daily Summary Spreadsheet".
  2. A **monthly e-commerce dashboard / COO scorecard** — KPIs across growth, profitability, productivity, inventory and customer engagement.
  3. **Month-end close automation** — nine source workflows feed a manually maintained "E-Commerce Allocation" Excel workbook, whose output is copy-pasted into Microsoft Dynamics 365 **Business Central** as General Journal lines and an AR invoice.
- **Key partner constraint named in the rubric:** "Goodwill: tools they already pay for."
- **Hard deadline:** **Code freeze / submission 4:00 PM Sunday Oct 4** (Eastern). Demo 4:30–6:00 PM Sunday in Room 154. Demo is a **recorded video embedded in Google Slides**.
- **Prize:** $750 to the winning team of each partner track; Goodwill's partner judge (Amanda Baumer) picks the Goodwill winner from the judges' ranking.
- **Scoring priorities:** Working Evidence (26), Partner Problem Fit (22), Fits Their Constraints (19), Technical Substance (15), Demo Clarity (11), X-Factor (7). Market size, pricing and polish score zero. Honesty about what is faked is never penalized; overclaiming is.

---

## 1. The Goodwill problem — verbatim statements

### 1.1 Official brief (problem-statement sheet)

> **GOODWILL MICHIANA — In brief:** reporting. Automate the recurring operations reports that staff put together by hand today.
>
> **Full statement (Debie, Oct 3):** From manual reporting to management visibility. A monthly e-commerce dashboard should balance growth, profitability, productivity, inventory management and customer engagement. A nightly report creates a daily pulse: revenue and customer count by marketplace (ShopGoodwill, Amazon, eBay, other), then enterprise totals. From manual month-end close to Business Central integration: today the close combines portal downloads (Cash Monkey, Upright, ShopGoodwill, Books, eBay, Amazon), emailed reports, bank activity, spreadsheet rules and manual Business Central entries; the target automates the rules, not just the downloads.
>
> **Questions today:** Amanda Baumer, office hours 3:00 to 5:00 PM, room 109B.

### 1.2 "The problem, in Goodwill's words" (slide 19)

Teams are told to **copy this into their submission** and to **open the demo with the partner's problem in the partner's own words**.

> "From manual reporting to management visibility. A monthly E-Commerce dashboard should balance growth, profitability, productivity, inventory management and customer engagement."
>
> "A nightly report creates a daily pulse. Each nightly report should show both revenue and customer count by marketplace, followed by enterprise totals."
>
> "From manual month-end close to Business Central integration. The current close combines portal downloads, emailed reports, bank activity, spreadsheet rules and manual Business Central entries."

Speaker note: "Goodwill's problem in Debie's own words, from her deck. The text is editable if she words it differently; teams copy it into their submission."

### 1.3 Title of Goodwill's own deck (slide 20)

**"From manual reporting to management visibility"** — Debie Coble, President and CEO, Goodwill Industries of Michiana.
Speaker note: "Debie Coble presents Goodwill's problem from these slides: how reports are pulled by hand today, and the reporting and month-end close Goodwill wants."

---

## 2. Goodwill people

| Person | Role | Involvement |
|---|---|---|
| **Debie Coble** | President and CEO (also listed as "Chief Executive Officer"), Goodwill Industries of Michiana | Presented the problem Saturday 11:30 AM. Thanked at awards. |
| **Amanda Baumer** | Goodwill Michiana | **Partner judge Sunday** (picks the Goodwill track winner; names the winner at awards). Saturday mentor, office hours **3:00–5:00 PM, Room 109B**. Designated contact for questions. |

---

## 3. Current state A — how the nightly numbers are produced today (slides 21–30)

Two manual report pulls feed a "Daily Summary Spreadsheet". The slides are screenshots of a step-by-step guide; details below were read off those screenshots.

### 3.1 Upright — "Paid orders" report (6 steps, slides 21–26)

Upright is the listing/order platform (header reads "upright — Goodwill Industries of Michiana"). It covers the ShopGoodwill channel (rows in the export show Channel = "Shopgoodwill"); its Downloads menu also lists Goodwillfinds and eBay listings.

| Step | Slide caption | What the screenshot shows |
|---|---|---|
| 1 | Open Reports | Guide text: "Click the Reports icon" in the top nav (Home, New Product, Products, Listings, then icons). The home dashboard shows cards such as Unfulfilled orders (243), Unprocessed manifest items (10,059, "over 2913 manifests"), Purgeable products (454), "6 Shopgoodwill listings failed", and Weekly supplier sales by store (Store09 $1,364.00, Store10 $469.62, Store11 $1,404.70, Store12 $106.50, Store13 $1,940.26). |
| 2 | Click Paid orders | Reports sidebar. **In-app reports:** User productivity, Operational productivity, Poster overview, Poster targets, Manifests, Suppliers, Top sales, Event logs, Sales by category. **Downloads:** Goodwillfinds listings, Shopgoodwill listings, eBay listings, **Paid orders**, Paid order items, Orders, Refunds, Manifest items, Shipments, Products, Embedded listings. The default view is a per-user productivity table with columns User, Accepted, Rejected, Photographed, Posted, Shelved, Purged, Picked… |
| 3 | Set date range | "Paid Order Report — This report includes all orders paid within a given date range. Optionally filter by channel or refund status." Fields: **Between** (start date, end date), **Timezone** = Pacific Daylight Time (hint: "Use America/Los_Angeles for SGW"), **Channel** = All, **Payment status** = Paid. Guide text: "Set the start date to 9/30/2026" (i.e. the prior day; both dates set to the same day). |
| 4 | Generate report | Click "Generate report". Note under the button: "We'll email the report when it's ready." A "Past reports" table lists Created by, Created, Status (Complete), Link. |
| 5 | Download | Click "Download" in the Link column of the newest Past reports row. |
| 6 | Customer count = rows minus the title row. Then these numbers are entered on the Daily Summary Spreadsheet. | Excel file named like `paid_orders_09-30-2026_09-30-2026`. Visible columns: Upright Order ID, Channel, Channel Order ID, Secondary…, Channel Buyer (username), Order Items, Payment…, Payment Type (ApplePay / CreditCard / PayPal), **Total**, **Subtotal**, **Shipping**, Shipping (…), Handling, Tax Total, Donation, Currency (USD), Final Value…, Payment… Data rows run 2–129; a manual `=SUM(...)` row at the bottom shows 13247.47 and 1452.03. |

**[Interpretation]** For Upright, one row = one paid order, so "customer count" = number of data rows (128 in the example). The revenue figure entered appears to be a column sum the staff member adds by hand; the screenshot suggests the summed columns are Subtotal and Shipping, but which column Goodwill calls "revenue" (Total vs Subtotal, with or without shipping/tax) is **not stated** and should be confirmed with Amanda. "SGW" = ShopGoodwill. Note the timezone: Upright reports are pulled in Pacific time.

### 3.2 Cash Monkey / Books — "Orders" report (4 steps, slides 27–30)

Cash Monkey (CashMonkey Solutions) is the platform for the books / Amazon / eBay side. Logged-in user in the screenshot: `gwmich_list`.

| Step | Slide caption | What the screenshot shows |
|---|---|---|
| 1 | Books: open Cash Monkey reports | Guide text: "EBooks Open Cash Money Reports". Sidebar: Manager Dashboard, List Merchant, Fulfill Merchant, FacRec Helper, Workstation Settings, Condition Notes, Channel Settings, Manage Users, **Reports**, Logout. The Reports page shows "The CashMonkey Console" (a data-visualization tool; access requested via Cash Monkey support). |
| 2 | Orders Report | Under **Orders Reports**: "**Orders** — Report showing items ordered, source, quantity, net revenue, profit, automatically factors in profit information from transaction reports" and "**Orders Marketplace Summary (Daily)(Beta)** — Orders report for a single day, rolled up by market." Under **Inventory Reports**: MF Inventory Unit Report, Units Listed by Source. |
| 3 | Select dates from the drop-down | Form "Orders Report — Showing orders across all market places, with profit information where available. One line per unit!" Fields: **Order Date From / To** (required, inclusive, **UTC**; example 2026-09-30 to 2026-09-30); **Accounts** (multi-select): `276 - Goodwill Michiana`, `277 - Goodwill Michiana (Stores)`; **Channel** (multi-select): `Amazon-MF`, `eBay`, `GoodwillBooks`; Order IDs; SKUs; checkboxes Tax Columns, Debug TZ, Include Non-CM orders, Include Non-standard channel info in "Channel" column, **Scheduled Report**; **Format** = csv; Submit. Footnote: each unit appears on its own row with shipping costs and market fees pro-rated to each unit; non-USD orders are auto-converted to USD. |
| 4 | Click the link; the report downloads | After Submit a link appears: "csv file download: `orders2023-20261001-132256-96170.csv`". |

**[Interpretation]**
- Cash Monkey output is **one line per unit**, not per order, so a customer count for Amazon/eBay/GoodwillBooks needs de-duplication by order ID rather than a raw row count. Confirm how Goodwill counts customers on this side.
- Cash Monkey dates are **UTC** while Upright is **Pacific**; a "day" is not the same window in both systems.
- Cash Monkey already offers an "Orders Marketplace Summary (Daily)(Beta)" report and a "Scheduled Report" option, and Upright emails reports when ready. These existing features fit the "tools they already pay for" constraint and may be easier integration points than scraping.

### 3.3 Final manual step

"Then these numbers are entered on the Daily Summary Spreadsheet." (slide 26) — the nightly report is assembled by typing each marketplace's revenue and customer count into a spreadsheet.

---

## 4. Target state A — the nightly report (slide 31)

**"A NIGHTLY REPORT CREATES A DAILY PULSE"** — "Each nightly report should show both revenue and customer count by marketplace, followed by enterprise totals."

| REVENUE SOURCE | DAILY REVENUE | DAILY CUSTOMERS |
|---|---|---|
| SHOPGOODWILL | Revenue for the day | Customers for the day |
| AMAZON | Revenue for the day | Customers for the day |
| EBAY | Revenue for the day | Customers for the day |
| OTHER E-COMMERCE CHANNELS | Revenue for the day | Customers for the day |
| **TOTAL E-COMMERCE** | Total revenue for the day | Total customers for the day |

"Other marketplaces can be added as separate rows as the channel mix evolves."

---

## 5. Target state B — the monthly dashboard and KPIs (slides 32–36)

### 5.1 Monthly dashboard (slide 32)

**"FROM MANUAL REPORTING TO MANAGEMENT VISIBILITY"** — "A monthly E-Commerce dashboard should balance growth, profitability, productivity, inventory management and customer engagement."

Five pillars: **GROWTH · PROFITABILITY · PRODUCTIVITY · INVENTORY · ENGAGEMENT**

### 5.2 KPI framework — "Profitability + productivity lead" (slide 33)

"The operating model begins with economic performance and the throughput required to sustain it." (Footer: "KPI framework • Economics + operating capacity")

| FINANCIAL METRICS | LISTING & PRODUCTION METRICS |
|---|---|
| Total E-Commerce Revenue | Items Identified for E-Commerce |
| Revenue Growth % (YOY) | Items Sent to E-Commerce |
| Gross Margin % | Listings Created per Day |
| Net Margin % | Listings per Employee |
| Revenue per Labor Hour | Average Time to List an Item |
| Profit per Labor Hour | Unlisted Inventory Backlog |

### 5.3 KPI framework — "Commercial KPIs complete the view" (slide 34)

"Sales effectiveness, category economics and customer behavior explain what is driving the headline results." (Footer: "KPI framework • Demand + assortment + loyalty")

| SALES EFFECTIVENESS | CATEGORY PERFORMANCE | CUSTOMER & MARKETPLACE |
|---|---|---|
| Average Selling Price (ASP) | Sales by Category | Number of Buyers |
| Median Sale Price | Margin by Category | Repeat Buyer Rate |
| Sell-Through Rate | Units Sold by Category | New Buyers |
| Days to Sell | Sell-Through Rate by Category | Customer Satisfaction Rating |
| Unsold Inventory % | Average Selling Price by Category | Net Promoter Score (if available) |
| Relisted Inventory % | Top 10 Categories by Revenue | Marketplace Conversion Metrics |
| | Top 10 Categories by Margin | |

### 5.4 COO scorecard — "15 KPIs create one COO operating view" (slide 35)

"A monthly scorecard should combine outcomes, operating drivers and early warning indicators."

| Area | KPI 1 | KPI 2 | KPI 3 |
|---|---|---|---|
| FINANCIAL | Total E-Commerce Revenue | Revenue Growth % | Net Margin % |
| PRODUCTIVITY | Listings Created | Revenue per Labor Hour | Listings per Employee |
| INVENTORY | Days from Donation to Listing | Unlisted Inventory Backlog | Unsold Inventory % |
| SALES | Average Selling Price | Sell-Through Rate | Sales per Employee |
| CATEGORY + CUSTOMER | Top 10 Categories by Revenue | Top 10 Categories by Margin | Repeat Buyer Rate |

"Monthly cadence • One page • Trend and target context should be added as data becomes available"

### 5.5 2027 plan — "Three KPIs anchor the 2027 plan" (slide 36)

"The strategic plan should focus leadership attention on profitable growth, labor leverage and inventory velocity."

1. **INCREASE E-COMMERCE NET MARGIN** — ↑ annually
2. **INCREASE REVENUE PER LABOR HOUR** — ↑ annually
3. **INCREASE SELL-THROUGH RATE** — ↑ annually

"These three measures connect profitability, workforce productivity and the speed at which inventory converts to cash."

**[Interpretation]** Several KPIs need data that the order reports alone do not contain: labor hours (Revenue/Profit per Labor Hour), cost data (margins), donation dates (Days from Donation to Listing) and survey data (CSAT, NPS — "if available"). Upright's in-app reports (User productivity, Operational productivity, Poster overview/targets, Sales by category, Top sales, Suppliers) and downloads (listings, products, manifest items, refunds, shipments) look like the likely sources for listing/production, category and sell-through metrics. Which data the team actually receives this weekend is not stated in the deck — ask.

---

## 6. Current state B — the month-end close (slides 37–39)

### 6.1 Overview (slide 37)

**"FROM MANUAL MONTH-END CLOSE TO BUSINESS CENTRAL INTEGRATION"** — "The current close combines portal downloads, emailed reports, bank activity, spreadsheet rules and manual Business Central entries."

Flow: **SOURCE REPORTS → ALLOCATION + RULES → BUSINESS CENTRAL**

### 6.2 "Nine source workflows feed one month-end close" (slide 38)

"The close depends on different portals, report timings, emails and finance lookups before the allocation workbook can be completed."

| # | SOURCE | MONTH-END INPUT | ACQUISITION / RULE |
|---|---|---|---|
| 1 | CASH MONKEY | Orders • full month | Submit/download CSV; save as Excel |
| 2 | UPRIGHT | Paid order items • full month | Generate; email delivery; save as Excel |
| 3 | JEWELRY | Jewelry Report | Request report; Co-Pivot populates Supplier |
| 4 | OSM / PB / EASYPOST | Shipping amounts | 1st Source acct 0101 • GL 10009 |
| 5 | FEDEX | Shipping charges + refunds | BC GL 40356 • Dept 180 • V00122 • net BNKDEPOSIT refunds |
| 6 | SHOPGOODWILL | Periodic marketplace reports | Filter year/month; Period 1 periodic only; Period 3 all reports |
| 7 | GOODWILL BOOKS | Prior-month payment statement | Monthly email attachment |
| 8 | EBAY | Listing sales report | Seller Center • change date • generate/download |
| 9 | AMAZON | Payments summary | Seller Central • request/refresh/download |

"Current state • Each source has its own access path, timing and business rule"

**[Interpretation] of the shorthand** (unverified — confirm with Goodwill):
- "1st Source acct 0101" likely refers to a bank account at 1st Source Bank; "GL 10009" a general-ledger account. Shipping amounts for OSM / Pitney Bowes ("PB") / EasyPost are looked up in bank activity.
- FedEx: Business Central GL account 40356, department/dimension 180, vendor V00122; refunds found as bank deposits ("BNKDEPOSIT") are netted against charges.
- "Co-Pivot populates Supplier" is written this way on the slide; it may mean a pivot/Copilot step that fills in the Supplier field for jewelry items. Unclear.
- ShopGoodwill "Period 1 / Period 3" refers to ShopGoodwill's periodic report cycles within a month; exact meaning not given.
- Month-end uses Upright **"Paid order items"** (item-level), while the nightly process uses Upright **"Paid orders"** (order-level).

### 6.3 "The allocation workbook is the manual control layer" (slide 39)

"After the source data is gathered, a prior-month workbook is copied forward and becomes the bridge into Business Central."

1. **ARCHIVE INPUTS** — Save all files under `Accounting / Month End / year / month / Journal Entries / E-Commerce JEs`.
2. **ROLL WORKBOOK** — Open the prior-month **E-Commerce Allocation** file and save a current-month copy.
3. **POPULATE TABS** — Enter report data into the **orange-highlighted fields** on the matching source tabs.
4. **GENERATE ENTRIES** — Workbook logic flows data into the **Journal Entry tabs** for each report.
5. **POST GENERAL JOURNAL** — Copy and paste the journal-entry output into a Business Central **General Journal**.
6. **CREATE AR INVOICE** — Use the final **Invoices tab** to create the Business Central **AR invoice** entry.

"The dependency is broader than a single upload: month-end rules, source-specific timing, shipping lookups, journal creation and invoice creation all sit inside the manual process."

---

## 7. Target state C — the automated close (slides 40–42)

### 7.1 "The target close automates the rules, not just the downloads" (slide 40)

"A controlled integration should acquire every input, preserve source rules and create Business Central-ready entries with reconciliation evidence."

| Step | Name | Contents |
|---|---|---|
| 01 | ACQUIRE | Portal reports; email attachments; bank and BC lookups |
| 02 | ARCHIVE | Consistent year / month; source file naming; run history |
| 03 | ENRICH | Supplier assignment; source labels; period metadata |
| 04 | APPLY RULES | Monthly date range; shipping and refunds; period-specific reports |
| 05 | CREATE BC OUTPUT | General Journal lines; AR invoice entry; control totals |
| 06 | POST + RECONCILE | Import/API status; source-to-BC totals; owned exceptions |

> **CONTROL PRINCIPLE:** Business Central receives balanced, traceable journal and invoice payloads; missing reports, failed rules and posting errors remain visible for review.

### 7.2 "Five workstreams define the build" (slide 41)

"The attachment clarifies the required scope: source intake, embedded workbook logic and both Business Central entry types must be addressed."

| WORKSTREAM | WORK TO COMPLETE | DELIVERABLE |
|---|---|---|
| 1 SOURCE INTAKE | Confirm access and automate downloads/email pickup for Cash Monkey, Upright, ShopGoodwill, Books, eBay and Amazon. | Reliable monthly source package |
| 2 SHIPPING + ENRICHMENT | Ingest bank activity; reproduce FedEx filters/refund netting; automate Jewelry Supplier enrichment. | Complete expense and enrichment dataset |
| 3 RULES + MAPPING | Document orange-field inputs, workbook formulas, control totals and source-to-account/dimension mapping. | Approved transformation and BC mapping |
| 4 BUSINESS CENTRAL OUTPUTS | Build General Journal and AR invoice payloads; capture import/API validation and posting response. | Tested journal and invoice interfaces |
| 5 CLOSE CONTROLS + SUPPORT | Reconcile source, workbook-equivalent and posted totals; define exceptions, approvals, archive and ownership. | Auditable month-end operating model |

"Discovery must confirm credentials, report availability, Business Central destinations and existing workbook formulas"

### 7.3 "Implement in waves that protect the month-end close" (slide 42)

"Automation should be introduced source by source, then proven against the existing allocation workbook before manual posting is retired."

1. **BASELINE THE CLOSE** — Inventory files, owners, timing, workbook tabs, formulas, journal output and invoice output.
2. **AUTOMATE ACQUISITION** — Prioritize stable portal/email feeds; add shipping lookups and enrichment after core reports.
3. **REPRODUCE + VALIDATE** — Generate BC-ready outputs and compare every source, total, journal line and invoice to the workbook.
4. **CUT OVER + OPERATE** — Approve production posting, monitor each close and route exceptions to named owners.

> **DEFINITION OF DONE:** Every required source is captured • Period and shipping rules are reproduced • Journal lines reconcile • AR invoice output reconciles • Posting status and exceptions are retained

---

## 8. Systems glossary

| System | What it is in this context |
|---|---|
| **Upright** | Listing/order management platform used by Goodwill Industries of Michiana. Source of ShopGoodwill paid-order data; reports are generated on request and emailed/downloaded. |
| **ShopGoodwill (SGW)** | Goodwill's auction marketplace. Also has its own periodic marketplace reports used at month-end. |
| **Cash Monkey (CashMonkey Solutions)** | Listing/fulfilment platform for the books side; Orders report covers channels Amazon-MF, eBay and GoodwillBooks. Accounts 276 (Goodwill Michiana) and 277 (Goodwill Michiana (Stores)). |
| **Goodwill Books / GoodwillBooks** | Books sales channel; a prior-month payment statement arrives as a monthly email attachment. |
| **Goodwillfinds** | Another Goodwill marketplace; appears in Upright's download list. |
| **eBay Seller Center** | Source of the listing sales report at month-end. |
| **Amazon Seller Central** | Source of the payments summary at month-end. |
| **OSM / PB / EasyPost** | Shipping providers (OSM Worldwide, presumably Pitney Bowes, EasyPost); amounts come from bank activity. |
| **FedEx** | Shipping charges and refunds, looked up in Business Central / bank deposits. |
| **Business Central (BC)** | Microsoft Dynamics 365 Business Central, Goodwill's accounting/ERP system. Destination for General Journal lines and the AR invoice. |
| **E-Commerce Allocation workbook** | Monthly Excel workbook rolled forward from the prior month; source tabs with orange input fields, Journal Entry tabs, and a final Invoices tab. |
| **Daily Summary Spreadsheet** | Spreadsheet where nightly revenue and customer counts are typed by hand. |

---

## 9. Constraints and what the deck does NOT say

**Stated constraint (rubric criterion 3, slide 92):** "Goodwill: tools they already pay for." (Compare: "Beacon: no patient data leaves".)

**[Interpretation]** A solution that lives inside tooling Goodwill already has — Excel/Microsoft 365, Business Central, the portals' own scheduled/emailed reports — will score better on "Fits Their Constraints" than one requiring new paid software. Rubric level 3 names the kinds of limits that count: "time, budget, staff skills or systems". Level 4: "the partner could start using it tomorrow".

**Open questions the deck leaves unanswered** (the kickoff told teams to listen for "what data you get this weekend", but the slides do not record Goodwill's answer):
- What sample data / exports / workbook copies does the team get? Is there any portal or Business Central sandbox access, or only files?
- Exact definition of "revenue" per channel (Total vs Subtotal; shipping, tax, fees in or out).
- Exact definition of "customer count" for Cash Monkey channels (unit rows vs unique orders vs unique buyers).
- What counts as "Other e-commerce channels" (Goodwillfinds? GoodwillBooks? Jewelry?).
- Timezone/day boundary to use (Upright Pacific vs Cash Monkey UTC vs local Eastern).
- Who receives the nightly report and in what form (email, Teams, spreadsheet, dashboard).
- The allocation workbook's actual formulas, orange-field list, GL/dimension mapping and journal/invoice layouts.
- How BC entries may be created (copy-paste, configuration package / Excel import, API).
- Which of the three sub-problems Goodwill values most.

---

## 10. How the team will be judged

### 10.1 Mechanics

- **One round.** Every team demos once, Sunday 4:30–6:00 PM, to its own partner's pod. Goodwill = **Pod B, Room 154**.
- Same timed slot for every team (**demo, questions, buffer**), length set from the team count and announced at the **4:18 PM calibration**. The slot is a **hard cut** when time is up. Slot number comes from the usher; live order at `innovationsprintlab.com/go/order`.
- The demo is a **recorded video embedded inside the team's Google Slides**. The room computer runs the slides; the pod facilitator opens them from the pod folder. Remote judges see the room screen through the pod's video call.
- "Open with the partner's problem in the partner's own words."
- Judges score six criteria, level 0–4 each, weighted to 100, one ballot per team (`innovationsprintlab.com/go/pod-b`).
- Score = average across the pod's judges after a per-judge adjustment to a common average, so tough and generous judges count the same. A judge who did not watch leaves a blank; **blank is never zero**.
- At 6:00 PM judges deliberate with scores on screen; **the partner picks the winner of its own track** from the judges' ranking.
- Ties within 1.5 points break on Partner Problem Fit, then Working Evidence, then number of YES answers to the 30-minute question, then the partner judge's YES.
- **Three winners, one per partner, $750 each.** Awards 7:45 PM in Room 109; each winner re-demos for two minutes (unscored). Goodwill winner is named by Amanda Baumer.
- Every team gets its judges' written comments after the weekend.

### 10.2 Instructions read to judges (slides 66–67)

> "Nobody is pitching a startup. Three partners, Beacon Health System, Goodwill Michiana, and DIU, each handed us a real operational problem on Saturday morning. Every team picked one of those problems and built for it. The teams do not own the idea, so do not score ambition, market size, or founder potential."
>
> "Score what you saw. Six dimensions, 0 to 4 each, weighted to 100 by the sheet… Level 2 is the expected default for a competent team."

Also: "Market size, pricing and polish score zero." / "Say what is faked; an overclaim costs you, honesty never does."

### 10.3 Full rubric (exact level sentences on the judging form)

**1. Working Evidence — 26 pts** — "What does the recorded demo show running, end to end?" (Judges watch the recorded demo and the repo. "Stack size does not count.")
- 4 — Full workflow runs in one take on more than one example, including a messy or edge-case input
- 3 — Full workflow runs on screen in one take, on the team's own example
- 2 — Parts run on screen, but one step is a cut, a screenshot or narration *(solid team)*
- 1 — Mockup, slides or narration only
- 0 — Nothing runs; no demo video

**2. Partner Problem Fit — 22 pts** — "Does it solve the partner's problem with a clear, rational approach?" (Judges look at the problem brief plus the opening slide restating the problem in the partner's words.)
- 4 — Fully solves it in the most efficient way, with the fewest steps for the user
- 3 — Fully solves the partner's problem
- 2 — Right topic, but only partly solves the partner's problem *(solid team)*
- 1 — Solved a different, easier problem
- 0 — No link to the partner's problem

**3. Fits Their Constraints — 19 pts** — "Did they engage the partner and understand the problem beyond the surface?" (Judges look at the demo, slides and the team's answers about the partner's limits. Goodwill: **tools they already pay for**.)
- 4 — Build works within all their key limits, so the partner could start using it tomorrow
- 3 — Build works within one real limit of the partner (time, budget, staff skills or systems)
- 2 — Named a real limit from the partner, but the build does not reflect it yet *(solid team)*
- 1 — Surface understanding, generic talk
- 0 — No sign they engaged the partner

**4. Technical Substance — 15 pts** — "How much of the hard part is real and built by the team?" (Judges look at the "what you built versus what you used" answer, sources cited, and the answer to the room's question. "AI coding tools are fine. Explain your own system.")
- 4 — Hard part is their own work, and they can explain its limits and what they would build next
- 3 — Hard part is real, minor edges simulated and disclosed
- 2 — Most impressive moment is simulated, and they said so *(solid team)*
- 1 — Nobody can explain how a part works
- 0 — Claimed capability does not exist or is not their work

**5. Demo Clarity — 11 pts** — "Did they clearly articulate what they built?" ("Comprehension, not polish.")
- 4 — Clear in the first 30 seconds, on time, and you can repeat their pitch
- 3 — Clear from the start, with one stumble
- 2 — You understood, but only by the end *(solid team)*
- 1 — You still do not understand what they built
- 0 — No demo delivered

**6. X-Factor — 7 pts** — "Did this team stand out? Would you back them?" (The whole demo and the team.)
- 4 — You would back them, and the partner would want to pilot it
- 3 — Stands out, you want to see more
- 2 — Solid, but does not stand out *(solid team)*
- 1 — Forgettable
- 0 — Serious concern or red flag

### 10.4 Three zero-point items on every ballot

- **Eligibility flag** — the build looks like it was made before this weekend. The organizer checks repo history once; a team flagged and upheld is removed from the ranking.
- **Overclaim flag** — checked once against the built-versus-used text and the repo. An upheld overclaim moves Working Evidence to **level 1 on every ballot**.
- "Would you, or your organization, spend 30 minutes with this team next week?" (used as a tie-breaker)

### 10.5 Goodwill pod judges (Pod B, Room 154)

| Judge | Affiliation | Attendance |
|---|---|---|
| **Amanda Baumer** | Goodwill Michiana — **partner judge** | in person |
| Michael Wicks | Notre Dame | in person |
| Shreya Kumar | Notre Dame | in person |
| Tim Connors | PivotNorth | remote |
| Horacio Lopez | Replit | remote |
| Dustin Goodman | ClickUp | remote |
| Reece Atkinson | ClickUp | remote |

Pod B facilitator (receives paper freeze sheets if there is no internet): **Hector**.

**[Interpretation]** To maximize score for this problem: show the real workflow running end to end in a single take on more than one day/month of data including a messy input (missing report, refund, odd row); restate Goodwill's problem verbatim on slide one; make the output land in tools Goodwill already uses; show reconciliation/control totals and visible exceptions, since the "control principle" and "definition of done" emphasize traceability; and state plainly what is simulated (e.g. portal access or BC posting).

---

## 11. Submission requirements

Submit at **`innovationsprintlab.com/go/submit` before 4:00 PM Sunday**. Resubmit any time before 4:00; the last one counts. Nothing pushed after 4:00 PM counts.

The form asks for:
1. **Google Slides link**, with the recorded demo video embedded, shared as "anyone with the link" (slides run from the room computer).
2. **GitHub repo link**.
3. **Sources cited**: open-source projects, tooling, models, APIs, templates used.
4. **What you built versus what you used.**

In the last ten minutes two things are due: repo pushed and form submitted. Fallback with no internet: a paper freeze sheet handed to the pod facilitator (Goodwill teams → Hector).

"Saying this is faked costs you nothing; presenting a stub as if it worked is an overclaim."

---

## 12. Ground rules

1. Build it this weekend. A project that looks pre-built gets flagged.
2. AI coding tools are fine. Not being able to explain your own system is not.
3. One partner problem per team.
4. Code freeze 4:00 PM Sunday. Nothing pushed after that counts.
5. Building closes 9:00 PM Saturday. No overnight access.
6. A small thing that works beats a big thing that does not.

Team name: registered once with the organizers; it is what judges see on the ballot — spell it the same everywhere. An equal number of teams is kept on each partner.

---

## 13. Schedule (Eastern time)

### Saturday, October 3
| Time | What | Where |
|---|---|---|
| 11:00 AM | Doors and kickoff | Room 109 |
| 11:30 AM | Reverse pitches: Beacon, Goodwill, DIU | Room 109 |
| 12:30 PM | Team formation | pick a problem; bring teammates or find them |
| 1:00 PM | Build starts | Rooms 105, 154, 160, the Cafe and open spaces |
| 1:30 PM | Lunch on your own | |
| 3:00 PM | Judge office hours open | Rooms 109A–109D, 15-minute slots |
| 6:30 PM | Dinner (provided, Cinco 5 buffet) | kitchen and vending area |
| 9:00 PM | Building closes | No overnight access; doors reopen 11:00 AM Sunday |

### Sunday, October 4
| Time | What | Where |
|---|---|---|
| 11:00 AM | Doors reopen | |
| 12:30 PM | Lunch on your own | |
| 1:00 PM | Judge office hours | Rooms 109A and 109B; remote mentors on screen |
| **4:00 PM** | **CODE FREEZE** — submissions close; everyone back to main 109 | |
| 4:18 PM | Calibration (slot length announced) | |
| 4:30–6:00 PM | Demos | Pod A Room 160, **Pod B Room 154**, Pod C Room 105 |
| 6:00 PM | Students to the lobby; judges deliberate; each partner picks its winner | |
| 6:30 PM | Dinner (provided) | students in main area; judges in 105 |
| 6:45–7:30 PM | Joe Grand, live talk + open Q&A (by video) | Room 109 |
| 7:45 PM | Awards — one track at a time (Beacon, Goodwill, DIU): winner, then two-minute demo | Room 109 |
| 8:00 PM | Close | |

### Rooms
- **109** — main room (kickoff, pitches, Joe Grand, awards).
- **109A–109D** — office hours Saturday; Sunday only 109A and 109B (109C/D become build rooms).
- **Build spaces** — Saturday: 105, 154, 160, the Cafe, main 109 area, informal conference space, lobby, gaming area. Sunday: 154, 160, 109C, 109D, the Cafe, main 109 area, open spaces (105 becomes the judges' room).

---

## 14. Mentors and office hours (15-minute slots; book via the OFFICE HOURS tab of the sign-up sheet)

### Saturday
| Mentor | Affiliation | Window | Where |
|---|---|---|---|
| Horacio Lopez *(Goodwill pod judge)* | Replit | 1:00–2:00 PM | remote |
| Matt Casanova | Nok Recommerce | 3:00–4:00 PM | 109A |
| Kyle McCullough | Cribl | 3:00–4:00 PM | remote |
| Reece Atkinson *(Goodwill pod judge)* | ClickUp | 3:00–4:00 PM | remote |
| Dustin Goodman *(Goodwill pod judge)* | ClickUp | 3:00–4:00 PM | remote |
| **Amanda Baumer** *(Goodwill partner judge)* | Goodwill Michiana | **3:00–5:00 PM** | **109B** |
| Robert Ramsey | Tire Rack | 3:00–5:00 PM | 109C |
| Nick Ashworth | DIU | 3:00–5:30 PM | remote |
| Lance Knight | Ex-Broadcom executive | 3:00–6:00 PM | remote |
| Andy Salentine | Salco Advisors | 3:30–6:30 PM | remote |
| Harshit Gupta | McKinsey & Company | 4:00–5:00 PM | 109D |
| Michael Wicks *(Goodwill pod judge)* | Notre Dame | 4:30–6:30 PM | 109A |
| Walter Scheirer | Notre Dame | 5:00–6:30 PM | 109D |
| Monish Chandrashekar | PwC | 5:00–6:00 PM | remote |

### Sunday
| Mentor | Affiliation | Window | Where |
|---|---|---|---|
| Matt Casanova | Nok Recommerce | 1:00–2:00 PM | 109A |
| Kyle McCullough | Cribl | 1:00–2:00 PM | remote |
| Reece Atkinson *(Goodwill pod judge)* | ClickUp | 1:00–2:00 PM | remote |
| Lance Knight | Ex-Broadcom executive | 1:00–3:00 PM | remote |
| JP Burford | Outcrop Solutions | 2:00–4:00 PM | 109B |
| Tim Connors *(Goodwill pod judge)* | PivotNorth | 2:00–4:00 PM | remote |
| Kevin Connors | Spray Venture Partners | 2:00–4:00 PM | remote |
| Teresa Covarrubias Gonzalez | Beacon Health System | 3:00–4:00 PM | 109A |
| Dustin Goodman *(Goodwill pod judge)* | ClickUp | 3:00–4:00 PM | remote |
| Ryan Geraghty | Google | 3:00–4:00 PM | remote |
| Nick Ashworth | DIU | 2:30–4:00 PM | remote |

**Note:** Amanda Baumer (the only Goodwill staff mentor) is listed for **Saturday 3:00–5:00 PM only**. No Goodwill staff member is listed for Sunday office hours.

---

## 15. Wider event context (non-Goodwill, for completeness)

- **Hosts:** Innovation Sprint Lab (student-run; SprintHack is "its front door") and the IDEA Center (Carolyn Madigan). Staff named: Hector Herrera, John Henry, Stefan (pod facilitators: Beacon → Stefan, Goodwill → Hector, DIU → John Henry). Coffee/dessert from student startups Addisuna Coffee and Le Dessert.
- **Format:** reverse pitching — partners pitch (11:30 Sat), teams pick and form (12:30), build, demo to that partner's judges (Sun 4:30). "2 days, 3 partners, 4 real problems."
- **Organizations supplying judges/mentors:** Beacon, Goodwill, DIU, Google, McKinsey, PwC, PivotNorth, Replit, ClickUp, Cribl, Nok Recommerce, Broadcom (ex-), ConnectALL, Notre Dame, Salco Advisors, Spray Venture Partners, Outcrop Solutions, Tire Rack.

### Other partner problems (not ours)
- **Beacon Health System** (Pod A, Room 160; Teresa Covarrubias Gonzalez, Max Maile) — credentialing automation: "Credential verification is too manual. Managers must find, verify, track, print, and file credentials across disconnected sources." One radiology manager monitors ~60 associates by hand across separate public credentialing sites, with paper files and manual expiration tracking. Constraint: no patient data leaves.
- **DIU** (Pod C, Room 105; Nick Ashworth, remote) — two problems, judged together:
  1. *AI-Enhanced Resilient Communications* — use generative AI to mask/obfuscate metadata of traffic on open commercial networks (LoRa mesh, Direct-to-Cell) via synthetic traffic generation, protocol emulation or automated cryptographic structuring; can be done in simulation.
  2. *AI-Driven RF Spectrum Analysis* — pair SDR output with LLMs/multimodal AI to characterize signals (frequency, bandwidth, modulation), summarize spectral visualizations in plain language and flag anomalies; open-source, publicly documented tools only; no SDRs in the building.

### Other pods' judges
- **Pod A (Beacon):** Teresa Covarrubias Gonzalez (partner judge), JP Burford (Outcrop Solutions), Monish Chandrashekar (PwC), Harshit Gupta (McKinsey, remote), Andy Salentine (Salco Advisors, remote), Kevin Connors (Spray Venture Partners, remote), Devotion Chikutuva (Beacon).
- **Pod C (DIU):** Nick Ashworth (partner judge, remote), Walter Scheirer (Notre Dame), Matt Casanova (Nok Recommerce), Kyle McCullough (Cribl, remote), Lance Knight (ex-Broadcom, remote), Ryan Geraghty (Google, remote).

### Special guest
Joe Grand ("Kingpin"), hardware hacker since 1982 — live talk and open Q&A by video, Sunday 6:45–7:30 PM, Room 109. (1998 US Senate testimony with L0pht; DEF CON badge designer from 2006; co-host of *Prototype This!* 2008; 2022 hardware-wallet recovery of $2M in crypto.)

### After the weekend
Innovation Sprint Lab: student-run program at Notre Dame; a partner brings a real problem and a student team ships working software in a ten-week sprint (October–December) with weekly industry mentorship. Showcase / Demo Day **Saturday, December 5**. Fall 2025 cohort: 15 students from 70+ applicants. Separate application at `innovationsprintlab.com`; the SprintHack weekend counts toward it.

### Useful links
| Link | Purpose |
|---|---|
| `innovationsprintlab.com/go/submit` | Submission form |
| `innovationsprintlab.com/go/rubric` | Rubric for students |
| `innovationsprintlab.com/go/problems` | Problem statements (sign-up sheet, PROBLEMS tab) |
| `innovationsprintlab.com/go/order` | Live demo order |
| `innovationsprintlab.com/go/board` | "Who needs a team" live board |
| `innovationsprintlab.com/go/checkin` | Check-in / status update |
| `innovationsprintlab.com/go/pod-b` | Judges' ballot for the Goodwill pod |

---

## 16. Slide index (where each fact came from)

| Slides | Section | Content |
|---|---|---|
| 1–12 | Kickoff | Title, check-in, hosts/partners, how it works, Sat/Sun schedule, rooms, ground rules, judges, judging overview, Joe Grand |
| 13 | Reverse pitches | What to listen for (problem in their words; who does the work and how long; constraints; data you get) |
| 14–17 | Beacon | Intro, overview image, video of current process, problem statement |
| **18–42** | **Goodwill** | **18 intro · 19 problem in Goodwill's words · 20 title · 21–26 Upright report steps · 27–30 Cash Monkey report steps · 31 nightly report · 32 monthly dashboard · 33–34 KPI framework · 35 COO scorecard · 36 2027 plan · 37 month-end overview · 38 nine source workflows · 39 allocation workbook · 40 target close · 41 five workstreams · 42 implementation waves + definition of done** |
| 43–45 | DIU | Intro, problem 1, problem 2 |
| 46–54 | Team formation | Forming teams, equal teams per partner, sign-up, submission requirements, Saturday mentors, build screen |
| 55–73 | Sunday | Schedule, Sunday mentors, countdown, code freeze, pods and judges, slot format, demo order, judge instructions, calibration, Joe Grand |
| 74–88 | Awards | Per-track winner and showcase, thank-yous, Innovation Sprint Lab promo, close |
| 89–95 | Appendix | Full rubric, one criterion per slide |
