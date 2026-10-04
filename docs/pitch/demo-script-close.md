# Demo script: the month-end close (D3.11)

Written 2026-10-04 01:45 EDT by Dani's agent, for whoever records (Orlando). Target: **about 65 seconds** inside the three-minute video (`docs/pitch/presentation_guide.md`, section 3). Three runs of **one command**, on the real pipeline: Victor's engine reads the files, Dani's rules match the money, the export writes the Business Central files. Every step below was run on `main` at 752e63f; the numbers are from those runs.

**Everything is synthetic.** The files are generated (`data/generate.py`), the account numbers are placeholders, and nothing is posted to Business Central. The page says so in its first lines; say it once out loud too.

## Before you record (5 minutes)
1. From a fresh clone: `pip install -r engine/requirements.txt`. Then rehearse once so the numbers below are the ones on your screen:
   ```
   python -m reports.close --inbox data/sample/tidy_month/inbox --month 2026-09
   python -m reports.close --inbox data/sample/messy_month/inbox --month 2026-09
   python -m reports.close --inbox data/sample/messy_month/inbox --inbox data/sample/messy_month/late --month 2026-09
   ```
   Each prints six numbered lines, Goodwill's own six steps (their slide 40), and ends `posting: NOT POSTED (import files ready)`.
2. Delete `out/close` and `out/archive` before the take, so the run history on the page starts at one run.
3. Terminal with a large font in the repo root, cleared. Browser on `reports/close/2026-09.html`, zoom 110-125%. Excel ready to open `out/close/2026-09/general_journal_2026-09.csv`.
4. The three commands in a text file to paste. Nothing typed live.

Numbers to expect (synthetic data):

| Run | Last step line | On the page |
|---|---|---|
| Tidy month | `eBay OPEN; Amazon OPEN; ShopGoodwill OPEN; 6 exceptions` | 56 journal lines in 25 documents, 1 invoice. Open balances $1,465.56, $5,410.16 and $5,429.93, each `unexplained $0.00` |
| Messy month | `eBay OPEN; Amazon INCOMPLETE; ShopGoodwill INCOMPLETE; 16 exceptions, needs review` | `payout data gap` Amazon -$743.10 (September 21-22) and ShopGoodwill -$1,875.64 (September 7); `unmatched deposit` $412.37, not posted |
| Messy month plus the late reports | `40 files from 2 inboxes`, then `eBay OPEN; Amazon OPEN; ShopGoodwill OPEN; 12 exceptions, needs review` | No data gap left. The $412.37 deposit is still held out. Run history shows the runs |

## 1. A tidy month: the baseline (about 20 s)
**Do:** `python -m reports.close --inbox data/sample/tidy_month/inbox --month 2026-09`, then refresh the page.

**Say:**
> "Month-end close. Today this is a workbook copied forward and pasted into Business Central. Here it is one command, and it prints Goodwill's own six steps: acquire, archive, enrich, apply rules, create the Business Central output, reconcile. September, every report downloaded once: the journal balances, and for each marketplace every cent it still owes is explained, payout by payout: money in transit, and the last days of the month not paid out yet."

**Point at:** the six step lines; on the page, the three `OPEN` pills and the `Unexplained $0.00` column.

## 2. The same month as it really arrives (about 30 s)
**Do:** `python -m reports.close --inbox data/sample/messy_month/inbox --month 2026-09`, then refresh.

**Say:**
> "The same month the way it really arrives: a report saved twice, an overlapping download, two rows broken in Excel, two refunds of August orders, and two reports nobody downloaded. The journal still balances. But Amazon and ShopGoodwill now read 'incomplete': Amazon paid $743.10 more than our files explain, and the page says why, no report covers September 21 and 22. ShopGoodwill, $1,875.64, September 7. And one bank deposit of $412.37 matches nothing: it is held out of the journal until someone identifies it."

**Point at:** the two `INCOMPLETE` pills; the two `payout data gap` lines with their days; the `Owner` and `What to do` columns; the `unmatched deposit` line.

**The line worth keeping if you cut everything else:**
> "A month's net can look fine while two errors cancel out. This checks every payout against the files for its own days, so nothing hides in a total."

## 3. The fix a person would make (about 15 s)
**Do:** `python -m reports.close --inbox data/sample/messy_month/inbox --inbox data/sample/messy_month/late --month 2026-09`, then refresh.

**Say:**
> "Someone finds the two reports and drops them in. Run it again: both gaps close, the deposit nobody can place is still held out, and the run history keeps all three runs with what each one found."

**Point at:** the pills back to `OPEN`; the run history table at the bottom; then open `general_journal_2026-09.csv` in Excel:
> "And this is what goes to Business Central: General Journal lines in the page's own column order, for paste or Edit in Excel. Tools Goodwill already pays for."

## If there are fifteen more seconds
Pick one, not all:
- **A rule is a line of config, not code.** In `reports/config/bc_mapping.csv` change eBay's fees account from `61210` to `61215`, run the messy month again, and show the line `eBay marketplace fees Sep 2026` in the journal with the new account. Put the file back afterwards: `git checkout reports/config/bc_mapping.csv`.
- **A second file agrees or it does not.** Add `--inbox data/sample/messy_month/cashmonkey`: the Cash Monkey month report is compared with the eBay and Amazon reports order by order, never added. eBay agrees to the order. For Amazon it finds 34 orders ($835.11) the Amazon reports do not hold: the two missing days again, seen from a different file, plus one order sold three minutes after midnight Eastern on the 1st, which is still August in Pacific time.
- **Goodwill's nine sources, honestly.** The table at the bottom of the page: three come from sample files, and each of the others says "not modeled" until a file for it reaches the run.
- **Without a person:** `python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04` runs the close on the 1st with the nightly job.

## What to say plainly (and what goes in "built versus used")
- All data is synthetic. No real Goodwill file has been read. The eBay, Amazon and bank layouts are ours; only Upright's columns come from Goodwill's slide.
- Nothing is posted. The output is import files; they have never been loaded into a Business Central. The status file of every run says `not_posted`.
- Account, customer and document numbers are placeholders, except department 180, which is on their slide 38.
- The rules are our reading. We have not seen the allocation workbook, so nothing is compared with it. Our rules are listed in `docs/contracts/close-rules.md`.
- Of Goodwill's nine month-end sources, three reach the close from sample files (Upright, eBay, Amazon) and Cash Monkey's month file as a cross-check. The others are "not modeled" unless Victor's simulated APIs for them are on `main` when you record: say the count the page shows.
- Last month's open items are not carried over: the month starts with no opening balance.
- The exception owners are role names we chose. There is no approval step.

## If something goes wrong on the take
- **The page looks stale:** the browser cached it. Reload with Ctrl+F5.
- **`... is missing: the engine writes it since close-inputs.md`:** the checkout is behind; `git pull`.
- **A run refuses with exit 1:** read the message. The usual cause is the same file name in two inboxes.
- Fallback tabs: keep `reports/close/2026-09.html` from the rehearsal open in a second window. Do not show it as if it were live.

## Questions you may get
See `docs/pitch/presentation_guide.md`, section 7. The two most likely here: "does it post?" (no: import files, and the status file says so) and "how do you know it is right?" (every document sums to zero or nothing is written; totals and all 35 payouts equal an answer key computed from the generated orders, not by our code; what we cannot check is their workbook).
