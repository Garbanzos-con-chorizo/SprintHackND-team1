# 011 — Website feedback round: charts, an Excel download, fewer words on the pages

- **Date / author:** 2026-10-04 12:50 EDT, Dani
- **Status:** proposed (Victor and Orlando: say no to any point and it is reverted; nothing else depends on it)
- **Changes:** `009-phase-3-split-dani-victor.md`, point 4, for this round only (Dani edits `reports/hub.py`); `008-static-server-for-docker.md` on one point (the server also serves `.xlsx`).

## Context
We got feedback on the site on Sunday. Liked: the bars on the overview that open the daily report, and the search on Daily Reports. Asked for: titles in title case; a button on the daily report to download the whole day in Excel; overview cards further apart and easier to tell apart; a pie chart for the week on the overview and on each scorecard, and a chart on the COO Scorecards page where you choose the metric and see it over days, weeks or months; fewer words on every page, with the explanations at the bottom or behind an asterisk; search by MM/DD/YYYY; clearer buttons for the close's export files.

The pages are in files held by Victor (`hub.py`, `scorecard.py`, `run_nightly.py`) and Orlando (`pulse.py`, `monthly/index.html`), and 009 says Dani does not edit `hub.py`. The feedback could not be done without them, and the freeze is at 16:00.

## Decision
1. **Dani does the whole round in one PR** (`d/website-feedback`), with a claim row and a note to each owner. The fence of 009 on `reports/run_scheduled.py` stands: that file is not touched.
2. **What changes on the pages:**
   - Titles and headings in title case ("Nightly Pulse", "COO Scorecard", "Month-End Close").
   - Daily report: a "Download Full Day (Excel)" button. `reports/day_workbook.py` writes `reports/pulse/<date>.xlsx`: Summary, By Marketplace, Data Quality, Definitions, and, from the engine's folder for the night, Transactions and Flagged Rows. No new dependency: `openpyxl` is already in `engine/requirements.txt`. Without it no file is written and the page shows no button.
   - Overview: the cards are further apart, each under a colored band with its name (red, with "Missing Data", when its latest page flags a gap); one short headline, a button to open the report and two for its main files; the rest under "More".
   - Charts (`reports/charts.py`, plain SVG, no script): a pie of the latest week's revenue by marketplace on the overview; a pie of the period's revenue by marketplace on every scorecard; on the COO Scorecards list, a KPI trend where you choose the area (Financial, Productivity, Inventory, Sales, Category + Customer) and days, weeks or months, and see each of the area's KPIs over the scorecards on file.
   - Fewer words: the explanations moved into a "Notes and Definitions" dropdown at the bottom of each page; an asterisk beside a label or figure shows the reason on hover and opens the dropdown. Example: "counted by order" is now an asterisk after the customer count.
   - Daily Reports search finds `10/03/2026`, `10/3/2026` and `10/03/26`.
   - Month-End Close: the export files are buttons, in a block under the summary on the month's page and in the list. The page still says "Posting status: Not posted" and no button says "Post" or "Send".
3. **The scorecard page still does no arithmetic.** The pie needs revenue by marketplace, so the KPI file carries it: `inputs.by_marketplace` on KPI 1 (`docs/contracts/kpi.md` v0.7, additive). The KPI trend only draws values the KPI files state.
4. **What is simulated is still said on every page**: the "Synthetic sample data" label stays in the top bar and the footer, the "Simulated internal data" badges stay on the KPIs, and the longer explanation is the first thing in each notes dropdown. The workbook says it on every sheet.
5. **The server serves `.xlsx`** (one suffix added to `SERVED`, with its content type).

## Consequences
- Orlando's port of `o/ui-map` (Victor's page of 12:40) and this round touch the same files: whichever lands second rebases on the other. This one is small in each file except `hub.card` and the bottom of `scorecard.py`.
- The scorecard PDF is unchanged: the pie, the buttons and the notes dropdown are screen only.
- Not done: the "Who receives this" block Victor asked for at 11:50 (his task 2), and the emails keep their wording.
- KPI files written before v0.7 have no `by_marketplace`: their scorecard shows no pie until the KPIs are computed again (the nightly run does).

## Response from Victor
**Yes** (Victor, 2026-10-04 13:25): the edits to `reports/hub.py`, `reports/scorecard.py` and `reports/run_nightly.py` are fine as merged in #79, including `hub.py` behind 009's fence. Nothing to take out.
