# Demo script 1 of 3: Overview and the nightly pulse

Presenter: Orlando. About 60 to 70 seconds. Everything is clicked on the served pages (`python server.py`, http://127.0.0.1:8000/), nothing is typed. All data is synthetic; say so once.

## Before you record
1. `python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04`, then `python server.py`.
2. Browser on the **Overview** page, zoom 110 to 125%. Ctrl+F5 so it is fresh.
3. Know the two days you will open: **Sun Oct 4** (a good day) and **Sat Oct 3** (Amazon and eBay missing).

## 1. The Overview (about 20 s)
**Show:** the page as it opens. Point at **Revenue by Night, last 8 nights**: one bar per night, split by marketplace.

> "This is the overview Goodwill's team opens each morning. Every bar is a night's revenue, split by ShopGoodwill, eBay and Amazon. And every bar is a link: click it and you are in that night's report."

**Do:** scroll down slowly and name the four widgets as you pass them:
- **Daily Report**, the Nightly Pulse, with its one-sentence summary.
- **Weekly Dashboard**, the week's 15 KPIs.
- **COO Scorecard (Monthly)**, the month's 15 KPIs.
- **Month-End Close**, the Business Central export.

> "Four reports, one page, all built from the same nightly data. Nobody rebuilds a spreadsheet."

## 2. A good day (about 15 s)
**Do:** scroll back up and click the **Sun Oct 4** bar.

> "A normal night. One sentence for the manager: revenue down 14% versus Saturday, ShopGoodwill strongest. Below it, revenue, orders and customers per marketplace. It even tells you it removed 149 duplicate rows, because someone saved the report twice."

**Point at:** the summary line and the change badges. Then **All Days** to go back, or the browser back button.

## 3. The day with missing data (about 25 s)
**Do:** click the **Sat Oct 3** bar (its axis label reads "No data: Amazon, eBay").

> "Now a bad night: the Amazon and eBay reports never arrived. A spreadsheet would show zero and look like a crash in sales. Here the marketplaces say 'No data: file not received' in red, the total is marked partial, and the comparison uses only what we have on both days."

> "That gets fixed by hand: someone downloads the missing report and drops it in. Which is the point. People only do work for the exceptions, not as a general rule like before. We will do exactly that on the month-end close page."

## Say plainly if asked
- Synthetic data. The reports are dropped in an inbox folder, standing in for the delivery Goodwill described.
- Revenue is net of refunds, without shipping or tax; customers are counted one per order, as staff do today.
