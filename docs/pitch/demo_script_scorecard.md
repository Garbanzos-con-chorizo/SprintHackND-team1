# Demo script: the COO scorecard (L7)

**Draft for Orlando**, written 2026-10-04 by Victor's agent while he was away: keep it, cut it or replace it, the presentation is yours. Target: **about 25 seconds** inside the three-minute video (`docs/pitch/presentation_guide.md`, section 3, the 1:00 slot), with a 15-second version at the end. Every step below was run on `main` at e8591c5; the numbers are from that run.

This is the middle of three scripts. Before it: the nightly pulse (`demo_script_pulse.md`). After it: the month-end close (`demo_script_close.md`, Dani's). Do not repeat the close here.

**Everything is synthetic.** The sales come from generated sample files. Eleven of the fifteen KPIs also need Goodwill's internal data (labor hours, listings, cost of goods), which we have never seen: those use a mock API and carry a "Simulated internal data" badge on the page, in the CSV and in the PDF. Say it once out loud too.

## Before you record (5 minutes)
1. From a fresh clone: `pip install -r engine/requirements.txt`. Then build everything once (about 50 seconds):
   ```
   python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04
   ```
   It runs eight nights. On the 1st it also builds the September scorecard with its CSV and PDF, the close, and the email drafts.
2. Check the store has the whole month:
   ```
   python -m engine.store status --month 2026-09
   ```
   Expect `30 of 30 days loaded, 30 complete`, and `internal API snapshot: 30 of 30 days (source mock: simulated)`.
3. Browser on `reports/index.html` (the portal), zoom 110-125%. Excel ready to open `reports/scorecard/month-2026-09.csv`. The PDF `reports/scorecard/month-2026-09.pdf` open in a second tab.
4. Nothing is typed live in this part: it is all on the page.

Numbers to expect on the September page (synthetic data):

| What | Value |
|---|---|
| Headline | Total e-commerce revenue $70,753.96, down 33.3% vs August 2026; 1 partial |
| KPIs | 15, in five areas: 14 ok, 1 partial (Repeat Buyer Rate 56.8%: Amazon gives no buyer id) |
| From the sales files alone | 4: revenue, revenue growth, average selling price $28.67, repeat buyer rate |
| Badged "Simulated internal data" | 11, for example Net Margin 23.0%, Revenue per Labor Hour $51.93, Listings Created 3,120 |
| Sell-through | 79.1%, shown as two boxes: 61.3% of what was listed in the period, 15.3% of what was left from earlier |
| CSV | 33 rows: one per KPI and one per category of the two top-10 lists |
| PDF | one page |

**About "down 33.3%":** there is no August sample, so August comes from the provider simulators, which generate more orders a day than the September sample has. The figure shows that the comparison works. It says nothing about Goodwill. Do not present it as a trend.

## 1. The scorecard (about 15 s)
**Do:** on the portal, click "COO scorecard (monthly)", September 2026.

**Say:**
> "The monthly dashboard. These are Goodwill's own fifteen KPIs, in their five areas, from their slide 35. Every night's sales go into one small database, and this page is computed from it: nobody rebuilds a spreadsheet."

**Point at:** the five area headings; the revenue tile; the pillar tag on a tile.

> "Four of these come straight from the sales files. The other eleven need internal data we have not seen, labor hours, listings, cost of goods, so they run on a mock and every one of them says 'simulated' right on the tile."

**Point at:** a "Simulated internal data" badge; then Repeat Buyer Rate:
> "And where the data is incomplete it says so: Amazon gives no buyer id, so this one is marked partial instead of pretending."

## 2. The same numbers, in the tools they already use (about 10 s)
**Do:** click "KPI table (CSV)" and show it in Excel; switch to the PDF tab.

**Say:**
> "The same numbers as a table for Excel or Power BI, and as a one-page PDF. On the first of the month that PDF goes to the COO's inbox, as a draft, with nothing for anyone to assemble."

**Point at:** the `Simulated` column in the CSV; the PDF fitting one page.

## If there are ten more seconds
Pick one, not both:
- **Day, week, month.** On the portal card, the period switch: "Day · Week to date · Month to date". The same fifteen KPIs for any period, from the same database.
- **Where a number comes from.** `python -m engine.store status --month 2026-09` in the terminal: thirty of thirty days loaded, per marketplace, and the internal snapshot marked simulated.

## The 15-second version
If the slot is short (the guide says to cut here before touching the close): show the page, say the first quote of section 1 and the sentence about the eleven simulated KPIs, and move on. Skip the CSV and the PDF.

## What to say plainly (and what goes in "built versus used")
- All data is synthetic. No real Goodwill file has been read.
- **Eleven of fifteen KPIs use simulated internal data** (a mock of Goodwill's internal systems, `engine/internal_api/`). The page, the CSV and the PDF mark each one. The four from sales files are revenue, revenue growth, average selling price and repeat buyer rate.
- The KPI definitions are our reading of slides 32 and 35, listed in `docs/contracts/kpi.md` and on the page. Goodwill has not confirmed them.
- August is simulated, so September's growth figure is illustrative.
- The database is one SQLite file on one machine. The emails are drafts in a folder: nothing is sent.
- The PDF needs Edge, Chrome or Chromium on the machine. Without one, the command says to use Print, Save as PDF.

## If something goes wrong on the take
- **The page looks stale:** reload with Ctrl+F5.
- **No PDF link on the page:** no browser was found when the scheduled run built it. Open the page and print to PDF, and say so.
- **`store status` shows fewer than 30 days:** delete `out/` and run step 1 again.
- Fallback: keep the page from the rehearsal open in a second window. Do not show it as if it were live.

## Questions you may get
- "Are these real numbers?" No: synthetic sales, and eleven KPIs on simulated internal data, each one badged.
- "What would it take to make them real?" The nightly files they already receive, and read access to the internal figures the mock stands for. The definitions are one file to correct.
- "Why a database?" So a month is thirty nightly loads added up, re-runnable, with every number traceable to a row of a source file. It is one file, no server, and it moves to Azure SQL unchanged.
