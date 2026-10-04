# Demo script 3 of 3: Month-end close to Business Central

Presenter: Orlando. About 60 to 70 seconds. Done in the browser: you add one report with the file picker, nothing is typed.

## Before you record
1. Messy September must be the state of the page: `python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04`, then `python server.py`. The page should read "eBay OPEN, Amazon INCOMPLETE, ShopGoodwill INCOMPLETE".
2. Clear any earlier uploads with the page's **Remove the added files and generate again** button (or `python -m reports.close_upload --month 2026-09 --clear`), so the demo starts from missing.
3. Put the file to drop where you can find it fast, e.g. the Desktop. Copy it from `data/sample/messy_month/late/`:
   - `amazon_daterange_2026-09-21_2026-09-22.csv` (Amazon, Sep 21 and 22)
   - `paid_orders_09-07-2026_09-07-2026.xlsx` (ShopGoodwill, Sep 7)
4. Excel not needed. Decide the one-file story: dropping **only the Amazon file** turns Amazon from missing to done and leaves ShopGoodwill as the remaining exception. Dropping both clears everything. Pick one before recording.

## 1. Open the month (about 20 s)
**Do:** top bar, **Month-End Close**, then open **September 2026**.

> "Last step: the month-end close. Today this is a workbook copied forward and pasted into Business Central. The page checks every marketplace's payouts against the reports for those days, and shows where it stands."

**Point at:** the status pills (`Amazon INCOMPLETE`), the **Missing days** next to the source (Sep 21 and 22), and the exception line "payout data gap" with its owner and what to do.

> "It does not guess. It tells you exactly which report is missing and for which days."

## 2. Add the missing file (about 25 s)
**Do:** in step 1 (Month-end files), under the Amazon row, choose the downloaded file. Click **Generate the month-end close**. Wait for the page to refresh.

> "The Controller downloads the missing report and drops it here. One click, and the close runs again."

**Point at:** Amazon moving from `INCOMPLETE` to done, the payout data gap line gone, the run history at the bottom gaining a run.

> "Missing becomes reconciled. A person only touched the exception."

## 3. Send it on (about 15 s)
**Do:** scroll to **Export Files for Business Central** and click **General Journal (CSV)**. Mention **AR Invoice (CSV)** beside it.

> "And this goes into Business Central: the general journal and the invoice, in Business Central's own column order, for upload or paste. Nothing is posted by us."

## Say plainly if asked
- Synthetic data. Nothing is posted; the files have never been loaded into a real Business Central.
- The Controller downloads these reports by hand today (decision 012). We automate everything after the download.
- The status word for a healthy marketplace on the page is `OPEN` (money still in transit), not "reconciled".

## Does not exist on this page (check before you say it)
- There is **no "email PDF" button on the close page**. It offers CSV downloads only. The email copy and PDF live on the pulse and scorecard pages. If you want "send as email, PDF or journal", either say it for those pages or ask for the button to be built.
