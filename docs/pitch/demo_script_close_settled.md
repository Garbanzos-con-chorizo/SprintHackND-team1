# Demo script, variant: the close that ends RECONCILED (draft)

Draft by Victor's agent for Orlando (who owns `docs/pitch/`) to take, change or drop. An alternative to the three-run flow in `demo_script_close.md`, not a replacement. About **45 seconds**. One missing file, then every source reads `RECONCILED`.

**Say this out loud, once:** the month is synthetic, and it is cut to settle. `settled_month` is the same September trimmed to the activity whose payout had already reached the bank by Sep 30, so nothing is in transit. A real month end always has money in transit and ends `OPEN` (see the tidy month in the other script). Nothing is posted to Business Central. Goodwill's Controller downloads these reports by hand (decision 012); we automate everything after the download.

## Before you record
1. Server up: `python server.py`. Browser on `http://127.0.0.1:8000/close/2026-09.html`, zoom 110-125%.
2. The simulated sources, once (they stand in for the Controller's download):
   ```
   python -m engine fetch --simulate --close-month 2026-09 --inbox out/sim/2026-09 --out out/sim_fetch
   ```
3. The starting state (also the reset between takes):
   ```
   rm -rf out/close out/archive out/uploads
   python -m reports.close --month 2026-09 --inbox data/sample/settled_month/inbox --inbox data/sample/settled_month/periodic --inbox out/sim/2026-09
   ```
   Last step line to expect: `eBay RECONCILED; Amazon RECONCILED; ShopGoodwill INCOMPLETE; Goodwill Books RECONCILED; 3 exceptions, needs review`.
4. The file to add, ready in a file dialog: `data/sample/settled_month/late/paid_orders_09-07-2026_09-07-2026.xlsx`.
5. Page cached? Ctrl+F5.

## 1. The month with one report missing (about 20 s)
**Do:** reload the page. Scroll to the red box and the source table.

**Say:**
> "Month-end close, September. The Controller downloads the reports and drops them in. The close reads them, matches every payout to the bank, and tells us where we stand. eBay and Amazon: reconciled, every payout is in the bank and matches. ShopGoodwill says incomplete, and it says why: one report is missing, the ShopGoodwill orders for September 7. Not a total that looks wrong, a named file."

**Point at:** the red "To be complete, this month needs 1 more report: ShopGoodwill (Upright) report covering Sep 7"; the Upright row `Missing days`; the `INCOMPLETE` pill against three `RECONCILED`.

## 2. One file (about 15 s)
**Do:** on the Upright row choose the file, then click **Add the chosen files and run the close again**. The page reloads.

**Say:**
> "Someone finds the report and adds it. One file. The close runs again on everything, including that file."

(If the page has not changed after the reload, Ctrl+F5: the browser cached it. The command-line alternative is the same two lines as step 3 of "Before you record" plus `--inbox data/sample/settled_month/late`.)

## 3. Reconciled (about 10 s)
**Point at:** the box now green, "Complete: every report the close needs is in this run"; every pill `RECONCILED`; `Unexplained $0.00`.

**Say:**
> "Complete. Every marketplace reconciled: what the files say we sold, what the marketplaces paid out, and what reached the bank all agree to the cent. And what goes to Business Central is import files; nothing is posted."

Optional, if there are ten more seconds: open `out/close/2026-09/general_journal_2026-09.csv` in Excel ("the lines go to Business Central in its own column order").

## If asked
- **"Is every month like this?"** No. This one is cut so that nothing is in transit. A real month end has money on its way, and the close shows that as `OPEN` with every cent explained; the tidy-month run in the main script shows it.
- **"Is the data real?"** No, all of it is synthetic. Only Upright's column names come from Goodwill's slide; every other layout is ours.
- **"Does it post?"** No. The status file of every run says `not_posted`.

## Checked
Both closes were run on this branch, and `reports/tests/test_close_settled_month.py` asserts both outcomes (one `INCOMPLETE` and two `RECONCILED` marketplaces before; all `RECONCILED` after). The page wording was read off a run, not from memory, but the recording itself has not been rehearsed from this script.
