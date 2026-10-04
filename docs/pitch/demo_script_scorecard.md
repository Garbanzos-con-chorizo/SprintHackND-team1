# Demo script: the COO scorecard (L7)

**Draft for Orlando**, by Victor's agent: keep it, cut it or replace it, the presentation is yours. Updated 2026-10-04 13:50 for the pages as they are now (#76 and Dani's #79: new top bar, list pages, the (i) buttons, the pie, buttons instead of links). Every step below was run on `main` at 5673608, from an empty `out/`; the numbers are from that run.

**Where it sits in the take:** the last live segment, after the pulse and the close, **1:50 to 2:10, about 20 seconds** (`docs/pitch/deck-proposal/narration.md`, which stitches the three scripts into one take). This file is the detail for that segment. Do not repeat the close here.

**Everything is synthetic.** The sales come from generated sample files. Eleven of the fifteen KPIs also need Goodwill's internal data (labor hours, listings, cost of goods), which we have never seen: those use a mock API and carry a "Simulated internal data" badge on the tile, in the CSV and in the PDF. Say it once out loud too.

## Before you record (5 minutes)
1. From a fresh clone in a **short path** (a deep folder made Windows drop sample files): `pip install -r engine/requirements.txt -r requirements-server.txt`. Then build everything once (about 1.5 minutes):
   ```
   python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04
   ```
   It runs eight nights. On the 1st it also builds the September scorecard with its CSV and PDF, the close, and the email drafts.
2. Check the store has the whole month:
   ```
   python -m engine.store status --month 2026-09
   ```
   Expect `30 of 30 days loaded, 30 complete` and `internal API snapshot: 30 of 30 days (source mock: simulated)`.
3. `python server.py` in a second terminal (the take uses it for the close anyway). Browser on http://127.0.0.1:8000/, zoom 110-125%.
4. Excel ready to open `reports/scorecard/month-2026-09.csv`. The PDF `reports/scorecard/month-2026-09.pdf` open in another tab.
5. Nothing is typed live in this part: it is all on the page.

Numbers to expect on the September page (synthetic data):

| What | Value |
|---|---|
| Headline | Total e-commerce revenue $70,753.96, down 33.3% vs August 2026; 1 partial |
| Line under it | Synthetic sample data. 11 of 15 KPIs use simulated internal data (marked) |
| Revenue by Marketplace (the pie) | ShopGoodwill $40,502 (57%), eBay $19,981 (28%), Amazon $10,271 (15%) |
| KPIs | 15 tiles in five areas (Financial, Productivity, Inventory, Sales, Category + Customer); 14 ok, 1 marked "Partial data" (Repeat Buyer Rate 56.8%: Amazon gives no buyer id) |
| From the sales files alone | 4: revenue, revenue growth, average selling price $28.67 per unit, repeat buyer rate |
| Badged "Simulated internal data" | 11, for example Net Margin 23.0%, Revenue per Labor Hour $51.93, Listings Created 3,120 |
| Sell-through | two boxes on the tile: 61.3% of what was listed in the period, 15.3% of what was left from earlier. The overall 79.1% is in the CSV |
| CSV | 33 rows: one per KPI and one per category of the two top-10 lists; a `Simulated` column |
| PDF | one page |

**About "down 33.3%":** there is no August sample, so August comes from the provider simulators, which generate more orders a day than the September sample has. The figure shows that the comparison works. It says nothing about Goodwill. Do not present it as a trend.

## 1. The scorecard (about 12 s)
**Do:** in the top bar, **COO Scorecards**, then **September 2026** in the Months rows of the table. (Not the portal's "COO Scorecard (Monthly)" card: it shows October to date. September is under its "More", as "Previous month".)

**Say:**
> "And the monthly dashboard. These are Goodwill's own fifteen KPIs, in their five areas, from their slide 35. Every night's sales go into one small database, and this page is computed from it: nobody rebuilds a spreadsheet."

**Point at:** the Revenue by Marketplace pie at the top; the five area headings; the revenue tile.

> "Eleven of these need internal data we have not seen, labor hours, listings, cost of goods, so they run on a mock and every one says 'simulated' right on the tile."

**Point at:** a "Simulated internal data" badge; then Repeat Buyer Rate, marked "Partial data":
> "And where the data is incomplete it says so: Amazon gives no buyer id, so this one is marked partial instead of pretending."

If asked what a KPI means: its (i) button opens the definition, the August value and the note. The tile itself stays short.

## 2. The same numbers, in the tools they already use (about 8 s)
**Do:** the **KPI Table (CSV)** button at the bottom of the page, shown in Excel; then the PDF tab (or the **PDF** button).

**Say:**
> "The same numbers as a table for Excel or Power BI, and as a one-page PDF. On the first of the month that PDF goes to the COO's inbox, as a draft, with nothing for anyone to assemble."

**Point at:** the `Simulated` column in the CSV; the PDF fitting one page. The PDF prints the August values and the notes that the screen keeps behind the (i) buttons.

## If there are ten more seconds
Pick one, not both:
- **Any metric over time.** On the COO Scorecards list, the KPI Trend: choose an area (Financial, Productivity, Inventory, Sales, Category + Customer) and Days, Weeks or Months. The same fifteen KPIs for any period, from the same database.
- **Where a number comes from.** `python -m engine.store status --month 2026-09` in the terminal: thirty of thirty days loaded, per marketplace, and the internal snapshot marked simulated.

## The 15-second version
If the slot is short (the take cuts here before touching the close): show the page, say the first quote of section 1 and the sentence about the eleven simulated KPIs, and move on. Skip the CSV and the PDF.

## What to say plainly (and what goes in "built versus used")
- All data is synthetic. No real Goodwill file has been read.
- **Eleven of fifteen KPIs use simulated internal data** (a mock of Goodwill's internal systems, `engine/internal_api/`). The page, the CSV and the PDF mark each one. The four from sales files are revenue, revenue growth, average selling price and repeat buyer rate.
- The KPI definitions are our reading of slides 32 and 35, listed in `docs/contracts/kpi.md` and behind each tile's (i). Goodwill has not confirmed them.
- August is simulated, so September's growth figure is illustrative.
- The database is one SQLite file on one machine. The emails are drafts in a folder: nothing is sent.
- The PDF needs Edge, Chrome or Chromium on the machine. Without one, the command says to use Print, Save as PDF.

## If something goes wrong on the take
- **The page looks stale:** reload with Ctrl+F5.
- **No PDF button on the page:** no browser was found when the scheduled run built it. Open the page and print to PDF, and say so.
- **`store status` shows fewer than 30 days:** delete `out/` and run step 1 again.
- **The September row is missing from COO Scorecards:** the scheduled run did not reach October 1; run step 1 again.
- Fallback: keep the page from the rehearsal open in a second window. Do not show it as if it were live.

## Questions you may get
- "Are these real numbers?" No: synthetic sales, and eleven KPIs on simulated internal data, each one badged.
- "What would it take to make them real?" The nightly files they already receive, and read access to the internal figures the mock stands for. The definitions are one file to correct.
- "Why a database?" So a month is thirty nightly loads added up, re-runnable, with every number traceable to a row of a source file. It is one file, no server, and it moves to Azure SQL unchanged.
