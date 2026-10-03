# Demo script: Nightly Pulse (P-O5)

Presenter: Orlando. Target: about 90 seconds, inside the 2-3 minute demo in `docs/PROBLEM.md#demo`. Three days, one take each.

## Before you present (5 min)
1. Regenerate everything so the numbers below match:
   ```
   python data/generate.py
   python -m reports.run_nightly --scenario day_clean
   python -m reports.run_nightly --scenario day_refund
   python -m reports.run_nightly --scenario day_ebay_missing
   python -m reports.run_nightly --scenario day_duplicates
   ```
2. Open a terminal with a large font, in the repo root, and clear it.
3. Have `reports/pulse/2026-10-01.html`, `2026-10-03.html` and `2026-10-04.html` ready in browser tabs as a fallback.
4. Close everything else. Zoom the browser to 110-125% so the back row can read the numbers.

Numbers to expect (synthetic data):

| Day | Summary line |
|---|---|
| Thu Oct 1 | Revenue up 7.1% vs Wednesday; ShopGoodwill strongest (52% of revenue). |
| Sat Oct 3 | Revenue up 91.4% vs Friday on comparable marketplaces; ShopGoodwill strongest (87% of revenue); eBay file missing. |
| Sun Oct 4 | Revenue down 14.3% vs Saturday; ShopGoodwill strongest (66% of revenue); 46 duplicate rows removed. |

## 1. Clean day: the baseline (about 30 s)
**Do:** run `python -m reports.run_nightly --scenario day_clean --open --pace 0.4`.

**Say:**
> "Every morning, staff download exports from ShopGoodwill, eBay and Amazon. Today that's three files in different formats: an Excel sheet, and two CSVs with their own headers, date formats and time zones. They drop them in one folder, and this runs."
>
> *(point at the log)* "It checks which files arrived, cleans them, calculates, and publishes. Under a second."
>
> *(page opens)* "This is the nightly pulse. The first line is written for a manager who reads one sentence: revenue up 7% versus Wednesday, ShopGoodwill is the strongest channel. Below it, revenue, orders and customers for each marketplace, and the enterprise total."

**Point at:** the summary line, the green change badges, the definitions at the bottom.
> "And every number says what it means. Revenue is net of refunds, without shipping or tax; fees are shown separately. No guessing which spreadsheet rule was used."

## 2. Missing file: it doesn't lie (about 30 s)
**Do:** run `python -m reports.run_nightly --scenario day_ebay_missing --open`.

**Say:**
> "Now a real morning: someone forgot the eBay download." *(point at the log line `ebay MISSING`)* "The run catches it before anyone opens the report."
>
> *(page)* "A spreadsheet would show eBay at zero dollars and revenue looks like it fell off a cliff. Here eBay says 'No data: file not received', in red, and the banner says the total is partial."
>
> "And the comparison with Friday only uses the marketplaces we have on both days, ShopGoodwill and Amazon. A missing file never looks like a bad sales day."

**If asked about the +91%:** "That's like-for-like ShopGoodwill and Amazon; Saturday auctions close high in this sample. With real data the point is the same: we compare only what we have on both days."

## 3. Duplicates: the cleaning you don't see (about 25 s)
**Do:** run `python -m reports.run_nightly --scenario day_duplicates --open`.

**Say:**
> "Last one. eBay was downloaded twice with overlapping dates, which happens all the time, and one Amazon line was pasted twice. Added up by hand, that inflates revenue."
>
> *(point at summary)* "The system found 46 duplicate rows and counted each order once. It says so in the summary and in the data-quality note, so the person reading it knows the data was cleaned and how."
>
> "The same run also writes a CSV for Excel or Power BI and an email-ready copy, so this can land in an inbox every morning."

## Close (about 5 s)
> "Three exports in, one trustworthy page out, every night, with no formulas to maintain."

## Be honest about (say it if asked, and it's on the closing slide)
- All data is synthetic; column layouts are modeled on public eBay and Amazon reports, and ShopGoodwill's is a guess until Amanda sends a sample.
- `run_nightly` runs on demand; a real deployment would trigger it from Windows Task Scheduler.
- Files are dropped in a folder by hand; we don't log into the portals.
- Until the engine and pulse modules are merged, the log says "SIMULATED" for those steps. **Re-record after integration (I1) so the log shows the real steps.**

## If something breaks live
Switch to the pre-opened browser tabs and keep talking; the story is the same. Never debug on stage.
