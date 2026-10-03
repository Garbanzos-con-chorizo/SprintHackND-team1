# Demo script: Nightly Pulse (P-O5)

Presenter: Orlando. Target: about 90 seconds, inside the 2-3 minute demo in `docs/PROBLEM.md#demo`. Three nights, one take each, **on the real pipeline**: Victor's engine parses the files, Dani's pulse calculates, our renderer publishes. Nothing is precomputed.

The inboxes hold Goodwill's two nightly reports in their real tools' layouts: **Upright "Paid orders"** (ShopGoodwill; Pacific time, one row per order) and **Cash Monkey "Orders Report"** (eBay and Amazon; UTC, one line per unit), as `.xlsx` like the emailed attachments.

## Before you present (5 min)
1. Regenerate and rehearse once, so the numbers below match:
   ```
   python data/generate.py
   python -m reports.run_nightly --scenario gw_day_clean
   python -m reports.run_nightly --scenario gw_day_cashmonkey_missing
   python -m reports.run_nightly --scenario gw_day_duplicates
   ```
   Each run uses its own folder (`out/<scenario>/`), so the order doesn't matter and no run borrows another's "prior day".
2. Open a terminal with a large font, in the repo root, and clear it.
3. Have `reports/pulse/2026-10-01.html`, `2026-10-03.html` and `2026-10-04.html` open in browser tabs as a fallback.
4. Close everything else. Zoom the browser to 110-125%.

Numbers to expect (synthetic data):

| Night | Summary line |
|---|---|
| Thu Oct 1 | Revenue up 7.1% vs Wednesday; ShopGoodwill strongest (52% of revenue). |
| Sat Oct 3 | Revenue up 89.3% vs Friday on comparable marketplaces; Amazon file missing; eBay file missing. |
| Sun Oct 4 | Revenue down 14.3% vs Saturday; ShopGoodwill strongest (66% of revenue); 149 duplicate rows removed. |

## 1. Clean night: the baseline (about 30 s)
**Do:** `python -m reports.run_nightly --scenario gw_day_clean --open --pace 0.4`

**Say:**
> "Every night Goodwill gets two reports by email: Upright for ShopGoodwill, Cash Monkey for eBay and Amazon. Amanda told us to assume an API sends them; this folder is where they land. Two tools, two time zones: Upright in Pacific, Cash Monkey in UTC."
>
> *(point at the log)* "E-commerce closes at 9 PM Pacific, midnight Eastern, so this runs after midnight. It checks what arrived, parses both files, puts every order on the right Eastern day, calculates, and publishes. Under a second, on the real engine."
>
> *(page opens)* "This is the nightly pulse. One sentence for the manager: revenue up 7% versus Wednesday, ShopGoodwill strongest. Below it, revenue, orders and customers per marketplace, and the e-commerce total."

**Point at:** the summary line, the change badges, the definitions at the bottom.
> "Every number says what it means: revenue is net of refunds, without shipping or tax; fees are separate; customers are counted the way your staff count them today, one per order."

## 2. Missing report: it doesn't lie (about 30 s)
**Do:** `python -m reports.run_nightly --scenario gw_day_cashmonkey_missing --open`

**Say:**
> "Now a bad night: the Cash Monkey email never came." *(point at `ebay MISSING`, `amazon MISSING` in the log)* "The run sees it before anyone opens the report."
>
> *(page)* "A spreadsheet would show eBay and Amazon at zero and revenue falling off a cliff. Here they say 'No data: file not received', in red, and the banner says the total is partial."
>
> "The comparison with Friday uses only what we have on both days, ShopGoodwill. A missing report never looks like a bad sales day."

**If asked about the +89%:** "That's ShopGoodwill alone, Friday to Saturday; auctions close high on Saturday in this sample. The point holds with real data: we compare like with like."

## 3. Duplicates: the cleaning you don't see (about 25 s)
**Do:** `python -m reports.run_nightly --scenario gw_day_duplicates --open`

**Say:**
> "Last one. Someone saved the Upright report twice; you can see the '(4)' in the file name, exactly like the screenshot in Goodwill's own walkthrough. Added up by hand, ShopGoodwill doubles."
>
> *(point at the summary)* "The engine found 149 duplicate rows and counted each order once, and it tells you so. Cash Monkey lists one line per unit, so a two-item order has two lines; those are not duplicates, and it keeps them."
>
> "The same run writes a CSV for Excel and an email-ready copy, so this lands in an inbox every morning."

## Close (about 5 s)
> "Two reports in, one trustworthy page out, every night, with no formulas to maintain."

## Be honest about (say it if asked; it's on the closing slide)
- **All data is synthetic.** Upright's columns come from the screenshot in Goodwill's walkthrough (three truncated headers guessed); Cash Monkey's columns are guesses, because the walkthrough never shows the file. A real file of each replaces the guesses with a column rename.
- **Ingestion stands in for the API** Amanda said we can assume (decisions 004, 005): reports are dropped in the inbox folder. The Upright API request is a stub until the API is documented.
- **`run_nightly` runs on demand.** In production Windows Task Scheduler or cron calls it just after midnight Eastern (decision 005).
- **Fallback:** `--simulated` builds the pulse from the answer key if the live run fails on stage; the log then says SIMULATED. Don't use it for the recording.

## If something breaks live
Switch to the pre-opened browser tabs and keep talking; the story is the same. Never debug on stage.
