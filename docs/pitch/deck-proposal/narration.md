# The take: slides, demo and narration (proposal for Orlando)

Written 2026-10-04 by Victor's agent, at Victor's request. **A proposal: `docs/pitch/` is Orlando's.** It revises his deck (`origin/o/skills-sdd`, `docs/pitch/deck/content.json`) and stitches the three demo scripts (`demo_script_pulse.md`, `demo_script_close.md`, `demo_script_scorecard.md`) into one take of about three minutes, most important things first. Team name as registered: **Chorizo Power**.

Files in this folder:
- `content.json`: the seven slides, in Orlando's format. Build: `python docs/pitch/scripts/build_deck.py docs/pitch/deck-proposal/content.json --out <dir> --html docs/pitch/deck-proposal/deck.html` (his tool, on his branch). 0 errors, 0 warnings.
- `deck.html`: that build, one offline file. Arrow keys or space to move, F for full screen. Built with one fix to his `export_html.py` (see "For Orlando" below); without it every slide shows the last one.
- this file: what to run, what to say, what to point at, and the numbers to expect.

**Every number below is synthetic** and comes from runs on `main` at 8f71775 (2026-10-04 12:45 to 12:52 EDT). Read them again from the 13:00 dry run before you say them.

## Before you record (10 minutes)
1. Fresh clone into a **short path** (a deep folder made Windows drop sample files). Then:
   ```
   pip install -r engine/requirements.txt -r requirements-server.txt
   python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04
   ```
   About a minute. It builds the pulse pages, the September scorecard (page, CSV, one-page PDF), the simulated month-end sources in `out/close_sources/2026-09/inbox`, the close and the portal. Do not delete `out/` afterwards.
2. In a second terminal: `python server.py`. Leave it running, off screen.
3. Browser (zoom 110-125%), tabs in this order:
   1. `docs/pitch/deck-proposal/deck.html`, full screen (F)
   2. http://127.0.0.1:8000/close/2026-09.html
   3. http://127.0.0.1:8000/close/index.html
   4. http://127.0.0.1:8000/ (the portal, for the scorecard)
4. Choose the two files in `data/sample/messy_month/late/` once in the panel's file dialog and cancel, so the dialog opens in that folder during the take. Check `out/uploads/2026-09/` is empty (`python -m reports.close_upload --month 2026-09 --clear` if not).
5. Terminal: font 18 pt or more, repo root, cleared. The commands below in a text file to paste; nothing typed live.
6. Excel closed; notifications off; everything else closed.

The three close commands (paste them as they are):
```
python -m reports.close --month 2026-09 --inbox data/sample/tidy_month/inbox --inbox data/sample/tidy_month/periodic --inbox out/close_sources/2026-09/inbox
python -m reports.close --month 2026-09 --inbox data/sample/messy_month/inbox --inbox data/sample/messy_month/periodic --inbox out/close_sources/2026-09/inbox
```
The third run is the panel in the browser, not a command.

## The take (one recording, no cuts)

| Time | On screen | Say |
|---|---|---|
| 0:00 | Slide 1, Goodwill's three sentences | "This is Goodwill's problem in their words: three reports, built by hand from six or more systems." |
| 0:15 | Slide 2 | "We automated all three. The data is synthetic, and we'll show exactly what is real." |
| 0:25 | Slide 3, then switch to the terminal | "Here it is running, in one take: a clean input, then a messy one." |

**Nightly pulse (0:30 to 0:55)**
- **Do:** `python -m reports.run_nightly --scenario gw_day_clean --open --pace 0.4`
- **Say:** "Every night two reports arrive: Upright for ShopGoodwill, Cash Monkey for eBay and Amazon. It parses them, puts every order on the right Eastern day and publishes. Revenue up 7.1% versus Wednesday, ShopGoodwill strongest."
- **Do:** `python -m reports.run_nightly --scenario gw_day_cashmonkey_missing --open`
- **Say:** "Now the night the Cash Monkey email never came. A spreadsheet would show eBay and Amazon at zero. This says no data, and the total says it is partial."
- **Point at:** `ebay MISSING`, `amazon MISSING` in the log; "Amazon and eBay: no data for this day" on the page.

**Month-end close (0:55 to 1:50)**
- **Do:** the first close command (tidy month); then the close tab, Ctrl+F5.
- **Say:** "Month-end. Today it's a workbook pasted into Business Central. Here it's one command running Goodwill's own six steps. Every report in: the journal balances, and every cent each marketplace still owes is explained."
- **Point at:** the six step lines; `OPEN` on eBay, Amazon, ShopGoodwill; `Unexplained $0.00`.
- **Do:** the second close command (messy month); Ctrl+F5.
- **Say:** "The same month as it really arrives: duplicates, broken rows, and two reports nobody downloaded. Amazon paid $743.10 more than our files explain, and the page says why: no report covers September 21 and 22. ShopGoodwill, $1,875.64, September 7. And a $412.37 deposit matches nothing, so it is held out of the journal with an owner."
- **Point at:** the two `INCOMPLETE` pills; the two `payout data gap` lines; the `Owner` column; the `unmatched deposit` line.
- **Do:** the Month-end Close list tab. In the panel, choose the two files in `messy_month/late/`, then "Add files and run the close again" (about 5 seconds).
- **Say:** "Someone finds the two reports and adds them here. The close runs again: both gaps close, and the deposit nobody can place is still held out."
- **Point at:** all `OPEN`; 13 exceptions.
- **Do:** open the General Journal CSV from the close page in Excel.
- **Say:** "This is what goes to Business Central: General Journal lines in its own column order. Nothing is posted."

**COO scorecard (1:50 to 2:10)**
- **Do:** the portal tab, COO Scorecards, September 2026.
- **Say:** "And the monthly dashboard: Goodwill's own fifteen KPIs in their five areas, computed from the nightly data. Eleven need internal data we haven't seen, so each one says 'simulated' on the tile. The change against August is against a simulated August, so it's illustrative."
- **Point at:** a "Simulated internal data" badge; Repeat Buyer Rate marked partial.

**Back to the slides (2:10 to 3:00)**

| Time | On screen | Say |
|---|---|---|
| 2:10 | Slide 4 | "It checks its own work. Totals match an answer key computed apart from the program; a journal that doesn't balance is never written; a missing report is never zero." |
| 2:22 | Slide 5 | "It uses tools they already pay for: Excel, Outlook, Business Central's import format. Nothing new to buy." |
| 2:32 | Slide 6 | "What we simulated: all the data, the provider APIs and the mailbox, and the internal data behind eleven of the fifteen KPIs. Not done: posting, their real accounts, and their workbook's rules." |
| 2:48 | Slide 7 | "Send us one real month of files and your allocation workbook. We'll run your close and compare it with yours, line by line." |

## If the slot is shorter: cut in this order
1. The Excel step in the close (about 5 s).
2. The scorecard down to one sentence and the badge (saves about 10 s).
3. Slide 4 (12 s).
Never cut slide 1, the messy close or slide 6.

## Numbers to expect (synthetic; check them at the dry run)

| Where | Expected | From |
|---|---|---|
| Pulse, Thu Oct 1 | "Revenue up 7.1% vs Wednesday; ShopGoodwill strongest (52% of revenue)", $2,385.52 | `run_nightly --scenario gw_day_clean` |
| Pulse, Sat Oct 3 | Amazon and eBay "no data for this day"; total partial | `run_nightly --scenario gw_day_cashmonkey_missing` |
| Close, tidy month | `eBay OPEN; Amazon OPEN; ShopGoodwill OPEN; Goodwill Books RECONCILED; 7 exceptions`; 65 journal lines in 28 documents | the first close command |
| Close, messy month | `Amazon INCOMPLETE; ShopGoodwill INCOMPLETE; 17 exceptions, needs review`; gaps Amazon −$743.10 (Sep 21-22), ShopGoodwill −$1,875.64 (Sep 7); unmatched deposit $412.37 | the second close command |
| Close, late reports added | all `OPEN`, `13 exceptions, needs review`, about 5 s | the panel (`reports.close_upload --add`, same code) |
| Scorecard, September | $70,753.96, down 33.3% vs a simulated August; 15 KPIs, 11 badged simulated, 1 partial | `run_scheduled` |
| Tests | 480 passed | `python -m pytest engine recon reports -q` |

The single-inbox commands in `CLAUDE.md` give different counts (6, 16, 12) because they leave out the periodic report and the simulated sources. Use the commands above.

## What must be said, and goes in the form
- All data is synthetic. No real Goodwill file has been read.
- The provider APIs are assumed and simulated. Files land in an inbox folder (there is no mailbox), a command stands in for the scheduler, and the emails are unsent drafts.
- Goodwill's nine month-end sources: in this take, four come from sample files we generated (Upright, eBay, Amazon, ShopGoodwill's periodic report) and four from simulated APIs (the Jewelry report, the carriers' bank feed, FedEx's ledger entries, the Goodwill Books statement). Cash Monkey's month file is "not in this inbox"; adding `--inbox data/sample/messy_month/cashmonkey` makes it five and four. The close page labels each one.
- 11 of the 15 KPIs use a simulated internal API and are badged. September's change compares with a simulated August, so it is illustrative.
- The close writes import files that have never been loaded into Business Central. Account, customer and document numbers are placeholders, except Dept 180 and the codes on their slide 38. The rules are our reading: we have not seen their allocation workbook.

## For Orlando
1. **Bug in `docs/pitch/tools/export_html.py`:** each `<section>` has an inline `display:flex`, which beats the stylesheet's `section{display:none}`, so the offline `deck.html` shows the last slide on every page (your `deck.html` on `o/skills-sdd` too; open it and press the right arrow). Fix: `display:none!important` and `section.on{display:flex!important}`. `deck.html` here was built with that change.
2. **Text size:** `deckgen.py` sets the quotes at 30 px, tables at 28 px, labels and the footer at 24-28 px. Our rule is body text at 32 px or more. This deck uses no table; slide 1's quotes are the only body text under 32 px.
3. **Getting the deck to `main`:** `o/skills-sdd` cannot merge (decision 011's renames, a second decision 010). This folder is new files only, so it can merge on its own.
4. What changed from your v2: slide 2 names the three reports; the "gaps" slide is gone (the messy close shows it live); a new slide 5 for their limit, "tools they already pay for"; slide 6 has three columns (built, simulated, not done); slide 7 adds the workbook and next steps; speaker notes carry the times.
