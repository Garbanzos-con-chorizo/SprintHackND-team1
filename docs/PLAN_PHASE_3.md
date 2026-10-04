# Plan: phase 3, the month-end close to Business Central

Written 2026-10-04 00:15 EDT by Dani's agent. **Status: proposed** (`docs/decisions/009-phase-3-split-dani-victor.md`). It replaces section 8 ("Phase 3") of `docs/PLAN_PHASE_2_3.md`, which was written before any close code existed. Sizes: **S** < 30 min, **M** 30-90 min, **L** 90+ min. **All clock times are Eastern.**

Checked against `main` at 4d8d8d9 by running the commands and reading the code, not from status files. What Goodwill asked for was read from the deck itself (slides 37 to 42, from the page's DOM), not from memory.

**Time left:** submission and code freeze are Sunday 16:00. The recording has to exist before that, so phase 3 stops taking features at **13:00**. With a start at 08:00 that is **five build hours per person**. Phase 3 is split between **Dani** (rules, matching, calculation, samples with their answer keys, the close command and page) and **Victor** (the engine's side: what the parsers hand over, the scheduler, the store). Orlando built the first version and is away; section 3 says who holds which of his files meanwhile.

## 0. Where `main` is today

Run on a fresh virtual environment (Python 3.13.16, `engine/requirements.txt`), Sunday 00:10:

| Command | What it printed |
|---|---|
| `python -m pytest engine recon reports -q` | `353 passed, 1 skipped` in 69 s (347 an hour earlier; Victor's L1 to L5 landed in between) |
| `python -m reports.reconcile --inbox data/sample/messy_month/inbox --month 2026-09` | `23 deposits classified (19 matched to payouts), 31 payouts read, 14 exceptions` |
| `python -m reports.bc_export --payload out/close/2026-09/close_payload_2026-09.json` | `journal: 56 lines in 25 documents, every document sums to 0.00`; `invoices: 1 document(s), 3 lines`; eBay `OPEN`, ShopGoodwill `OPEN`, Amazon `UNEXPLAINED` with `unexplained -226.78` |
| `python -m reports.close_report --month 2026-09` | `wrote reports/close/2026-09.html` |
| `python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04` | exit 0 (40 s the first time, 21 s once the store exists); on the night of Sep 30 it prints `close: 2026-09 from data/sample/messy_month/inbox` and `close page: reports/close/2026-09.html` |

That matches what we believed. Six things do not, or were not known:

1. **The $226.78 is two real things netted.** Amazon's open balance is $4,667.06 and the payout in transit is $4,893.84, so the close is $226.78 *over*-explained. The answer key has both halves: $516.32 of September 29-30 activity not paid out yet (`unpaid_activity_cents`), minus $743.10 that the settlement paid for September 21-22, the two days nobody downloaded (`data_gap_cents` on `AMZN-0928`). 516.32 - 743.10 = -226.78.
2. **ShopGoodwill has the same defect, hidden.** It reads `OPEN, unexplained 0.00`, with $3,554.29 "not yet paid out". The truth in the answer key is $5,429.93 not yet paid out minus $1,875.64 that payout `SGW-0913` paid for September 7, the missing Upright report. The net happens to fall under the ceiling the rule accepts (`Settles_Within_Days`), so today's close explains ShopGoodwill with the wrong reason. This is the more serious of the two: nothing on the page shows it.
3. **The close does not run on a clean month.** `data/sample/clean_month` has no bank file and no `close` answer key. Run on it, the same commands give `0 deposits classified`, 34 exceptions, Amazon `UNEXPLAINED` by $7,680.32 and ShopGoodwill by $57,490.89. The judges' top level asks for a clean and a messy example; for phase 3 we only have the messy one.
4. **The engine's rows carry the Eastern day and no time.** Amazon and ShopGoodwill pay by Pacific days. Rebuilding payout windows from `business_date` reproduces 32 of the answer key's 36 payouts; the other four (`AMZN-0928`, `SGW-0913`, `SGW-0920`, `SGW-0927`) are off by $12.99 to $72.00, orders placed between midnight and 3 AM Eastern. Fixing findings 1 and 2 exactly needs the order's time from the parsers.
5. **The bank file and the payout rows are read in `reports/reconcile.py`, not by the engine.** The engine skips `Payout` and `Transfer` rows and reports the bank file as `unparseable` ("no source recognizes this file"), which `reconcile` then filters out. Bank debits are dropped (`reports/reconcile.py:66`).
6. **The close page does not say what is simulated.** Nothing on `reports/close/2026-09.html` or in the four CSV files says the data is synthetic or that the account numbers are placeholders. By rule 14 of `CLAUDE.md` that is an overclaim waiting to be found.

Also changed in the last hour: **Victor has finished L1 to L5** (PRs #48 to #50). L6, L7 and L8 are left, so he has more room for phase 3 than "L1 to L8" suggested.

**Deck against `docs/goodwill-project-context.md`, sections 6 and 7:** the same, item for item, on slides 37 to 42. The deck has two things the transcription leaves out, neither of substance: a kicker line on each slide (for example "GOODWILL MICHIANA · TARGET CLOSE") and a one-sentence speaker note that restates the title. The transcription numbers slide 38's rows 1 to 9; the slide does not. One phrase is easy to read past in both: slide 41 says "**the attachment** clarifies the required scope". Goodwill has a document we have never seen (question 4).

## 1. Gap table: what the deck asks for against `main`

**done** = runs on the sample and matches its answer key · **partly** · **missing** · **out of reach** = cannot be built honestly this weekend, whatever the time.

### Slide 38: the nine source workflows
| Source, month-end input (the slide's words) | Today | What shows it | In this plan |
|---|---|---|---|
| **Cash Monkey**: orders, full month | partly | The engine reads the layout for the nightly run (`engine/sources/cashmonkey.py`; `run_scheduled` runs `gw_day_clean` through it). No month file in the close sample (`expected.json`, `close.not_modeled`), and no rule for how it sits beside the eBay and Amazon reports without counting sales twice | not built; question 8 |
| **Upright**: paid order items, full month | partly | `messy_month/inbox` has 30 daily "Paid orders" files, one row per order, read by `engine/sources/upright.py`; ShopGoodwill sales 39,118.00 = the answer key. The slide names the item-level report for the whole month, which we have never seen | no change |
| **Jewelry**: Jewelry Report, "Co-Pivot populates Supplier" | missing | nothing in the repo reads or simulates it | out of reach: we know neither the report nor what Supplier feeds; question 7 |
| **OSM / PB / EasyPost**: shipping amounts (1st Source acct 0101, GL 10009) | missing | `reports/reconcile.py:66` skips every bank debit; the sample bank file has two, payroll and a service charge | D3.5, first on the cut list |
| **FedEx**: charges and refunds (BC GL 40356, Dept 180, V00122, net BNKDEPOSIT refunds) | missing | only Dept 180 is used, as the department on every line (`reports/config/bc_mapping.csv`) | D3.5 with V3.5, first on the cut list |
| **ShopGoodwill**: periodic marketplace reports (Period 1, Period 3) | missing | `close.not_modeled`. Its 4 deposits are tied to the source but to no payout (the 4 of 23 that are not "matched to payouts") | D3.1 rebuilds its payout windows from the cycle; the report itself is out of reach, question 5 |
| **Goodwill Books**: prior-month payment statement | missing | `close.not_modeled`. Cash Monkey's Goodwillbooks channel becomes marketplace `other`, which has no row in `bc_mapping.csv`; `reconcile.build` loops over the mapping only (`reports/reconcile.py:157`), so such rows would be left out with no exception. Read in the code, not run: the month sample has no `other` rows | D3.2 makes it an exception; the statement is out of reach |
| **eBay**: listing sales report | done, on a synthetic layout | 5 files, one an overlapping re-download; sales 20,052.32, refunds 94.97, fees 3,103.73 in the journal = the answer key; 29 payouts read, 18 deposits matched, 4 of them covering several payouts | |
| **Amazon**: payments summary | done, on a synthetic layout, with the gap | 2 files, September 21-22 never downloaded; revenue 9,434.51 = the answer key; **$226.78 unexplained** | D3.1 |
| Bank activity (slides 37 and 41, not one of the nine) | partly | 24 credits read, 23 classified by `Bank_Text`, 1 held out ($412.37, `unmatched_deposit`); debits ignored; parsed outside the engine | V3.2 |

### Slide 40: the target close in six steps, and its control principle
| Step (the slide's three items) | Today | What shows it | In this plan |
|---|---|---|---|
| **01 Acquire**: portal reports; email attachments; bank and BC lookups | partly | Files arrive in an inbox folder. `python -m engine fetch --simulate` writes simulated provider emails for the nightly run; the month inbox is a sample folder. The bank file is read. No BC lookup | V3.2; BC lookup only with V3.5 |
| **02 Archive**: consistent year / month; source file naming; run history | partly | Outputs land in `out/close/2026-09/`. Inputs are not copied, and nothing records that a close ran (the store's `runs` table knows `load`, `pull`, `kpi`) | D3.7, V3.4 |
| **03 Enrich**: supplier assignment; source labels; period metadata | partly | Every row carries `marketplace`, `source_file`, `source_row`; the payload carries the month and posting date. No supplier | supplier out of reach |
| **04 Apply rules**: monthly date range; shipping and refunds; period-specific reports | partly | Month filter on `business_date`; shipping and handling charged to buyers go to their own accounts; refunds post, and the 2 refunds of August orders are flagged. Shipping *cost* and period-specific reports: nothing | D3.1; D3.5 if time |
| **05 Create BC output**: General Journal lines; AR invoice entry; control totals | done on the sample | 56 lines in 25 documents, each 0.00; 1 invoice, 3 lines; `control_totals_2026-09.csv`. An unbalanced document is refused and nothing is written (`reports/tests/test_bc_export.py`). Account numbers are placeholders | labels: D3.8 |
| **06 Post + reconcile**: import/API status; source-to-BC totals; owned exceptions | partly | Revenue in = revenue posted for all three sources (`Difference 0.00`). 14 exceptions, none with an owner. No import or API status | D3.3, D3.7; posting itself is out of reach (no sandbox, `ASSUMPTIONS.md` 1.2) |
| **Control principle**: balanced, traceable payloads; missing reports, failed rules and posting errors stay visible | partly | Balanced: yes. Traceable: descriptions carry payout ids, exceptions carry file and row. Missing reports: 2 `missing_report` lines. But two amounts are netted out of sight (findings 1 and 2), and a marketplace without a mapping row would vanish (slide 38, Goodwill Books) | D3.1, D3.2 |

### Slide 41: the five workstreams
| Workstream (deliverable) | Today | What shows it | In this plan |
|---|---|---|---|
| **1 Source intake** (reliable monthly source package) | partly | 3 of the 6 named sources reach the close (Upright, eBay, Amazon); Cash Monkey nightly only; ShopGoodwill periodic and Books not at all. Acquisition is a folder | the page lists all nine with their state (D3.8, V3.3) |
| **2 Shipping + enrichment** (complete expense and enrichment dataset) | partly | Bank credits only. No FedEx filters or refund netting, no Jewelry supplier | D3.5 if time; Jewelry out of reach |
| **3 Rules + mapping** (approved transformation and BC mapping) | partly | `reports/config/bc_mapping.csv`: one row per source, journal or invoice path, accounts, department, bank text. The rules themselves are only in docstrings and `docs/contracts/close-payload.md`. We have never seen the workbook, its orange fields or its formulas | D3.10 writes our rules down; the workbook's are out of reach, question 4 |
| **4 Business Central outputs** (tested journal and invoice interfaces) | partly | Both payloads are built and checked twice (before writing, and by reading the files back). Never imported into a Business Central | import and posting response out of reach; D3.7 records "not posted" |
| **5 Close controls + support** (auditable month-end operating model) | partly | Source totals against posted totals: yes. Workbook-equivalent totals: no workbook. Exceptions defined; no approvals, archive or owners | D3.3, D3.7; approvals not built |

### Slide 42: the definition of done
| Point | Today | What shows it | In this plan |
|---|---|---|---|
| Every required source is captured | partly | 3 of 9, plus the bank's credits | stays partial; the page says which six are not modeled |
| Period and shipping rules are reproduced | partly | Month range, shipping charged, refunds. Not the carrier cost rules, not ShopGoodwill's periods | D3.5 if time, else said plainly |
| Journal lines reconcile | partly | Every document sums to 0.00 and revenue in = posted. **Amazon is $226.78 off**, and we cannot compare with the workbook | D3.1 |
| AR invoice output reconciles | partly | ShopGoodwill invoice: 3 lines, 39,118.00 of sales = revenue in. Its open balance is explained with the wrong reason (finding 2) | D3.1 |
| Posting status and exceptions are retained | partly | `exceptions_2026-09.csv` is kept with the month's files and overwritten by the next run. No posting status, no history of runs | D3.7, V3.4 |

Slide 42's four waves, for orientation: we are in wave 3 ("reproduce + validate") on synthetic files. Wave 1 (baseline the real workbook) never happened for us, and wave 4 (cut over) is Goodwill's.

## 2. What "phase 3 done" means on Sunday

**In the recording, one take, the same command three times:**

1. **A tidy month.** `python -m reports.close --inbox data/sample/tidy_month/inbox --month 2026-09`: every report downloaded once. The page shows three sources `OPEN` with every cent explained (payouts in transit, activity not paid out yet), nothing to review, and the four Business Central files.
2. **The same month as it really arrives.** The same command on `messy_month`: a report never downloaded on two sources, a re-download, an overlapping range, two broken rows, two refunds of August orders, a deposit nobody can place. The journal still balances. Amazon and ShopGoodwill read `INCOMPLETE` and the page names the days and the amounts ($743.10, $1,875.64); the $412.37 deposit is held out; nothing is netted out of sight.
3. **The fix a person would make** (if D3.9 survives the cuts): drop the two late reports into the inbox, run again, and the two gaps close.

And without a person: `python -m reports.run_scheduled` runs the same close on the 1st.

**It is done when all of these hold on `main`:**
- Both months run from one command each, exit 0, and every journal document sums to 0.00.
- On both months every source reads `unexplained 0.00`, and every figure equals an answer key that was computed from the generated orders, not by the code under test.
- Each run leaves an archive of its inputs and outputs and a status file that says `not_posted`.
- The page and the files say: synthetic data, placeholder account numbers, import files, not posted. The page lists Goodwill's nine sources and marks the ones we do not model.
- `python -m pytest engine recon reports -q` passes.

**What we will say plainly is not built:**
- **Nothing is posted to Business Central.** The output is import files in the column order of the General Journal and Sales Invoice pages. They have never been loaded into a Business Central, so "import/API status" and "posting response" do not exist.
- **Six of the nine sources are not in the close**: the Cash Monkey month file, Jewelry (supplier), OSM / PB / EasyPost, FedEx, the ShopGoodwill periodic reports, the Goodwill Books statement. (Four if D3.5 lands.)
- **The rules are our reading, not the workbook's.** We have not seen the E-Commerce Allocation workbook, its orange fields or its formulas, so nothing is compared with it.
- **Account, customer and document numbers are placeholders**, except Dept 180, which is on slide 38.
- **The file layouts are imitations.** The eBay, Amazon and bank files are synthetic and shaped by us; only Upright's columns come from a slide.
- **No carry-forward.** August payouts that settle in early September are not modeled, so the month starts with no opening balance.
- **No approvals.** Exceptions get an owner from a config file with role names we made up; nobody signs anything off.
- **No portal automation for the month files.** They are dropped in a folder.

## 3. The work, in two parts

```
month inbox ──> ENGINE (Victor) ──> transactions.csv (+ occurred_at)        ┐
  (files)                           payouts.csv, bank.csv                   ├ contract: close-inputs.md
                                    source_coverage.json, warnings.json     ┘
                                         │
                                         v
              CLOSE RULES (Dani)  reports.reconcile ──> close payload ──> reports.bc_export
                                  payout windows, matching, exceptions    journal, invoice, control totals
                                         │
                                         v
              reports.close (Dani)  one command: archive, status file, page ── contract: close-outputs.md
                                         │
                                         v
              RUNNER AND STORE (Victor)  run_scheduled on the 1st, run history, portal card, email
```

The two parts meet at two contracts and nowhere else. Until Victor's files exist, `reports/reconcile.py` keeps its own readers for the bank file and the payout rows (they work today), so Dani does not wait. Until Dani's command exists, `run_scheduled` keeps calling the three commands it calls today, so Victor does not wait.

### Who holds which file while Orlando is away
Nothing is moved or renamed (it would cost time and break imports for no gain before the freeze). Ownership below is temporary: it ends when Orlando says so or at the freeze, whichever comes first, and is recorded in decision 009 and as rows in `docs/CLAIMS.md`.

| Files | Normally | For phase 3 | Why |
|---|---|---|---|
| `reports/reconcile.py`, `reports/bc_export.py`, `reports/mock_recon.py`, `reports/config/bc_mapping.csv`, `reports/tests/test_reconcile.py`, `reports/tests/test_bc_export.py` | Orlando | **Dani** | matching, rules and their tests |
| `reports/close_report.py`; new `reports/close.py`, `reports/config/close_*.csv`, `reports/tests/test_close*.py` | Orlando | **Dani** | the command and the page render Dani's payload |
| `data/generate.py`, `data/sample/messy_month/`, new `data/sample/tidy_month/`, `data/README.md` | Orlando | **Dani** | samples and answer keys are written by someone other than the parser's author, so the key stays independent |
| `docs/contracts/close-payload.md`; new `close-outputs.md`, `close-rules.md` | Orlando / new | **Dani** | |
| `docs/pitch/demo_script_close.md` (new) | Orlando | **Dani** | Victor's L7 links it instead of writing a second one |
| `engine/` including `engine/tests/test_close_reads_engine_columns.py`; `docs/contracts/transaction.md`, `store.md`; new `close-inputs.md` | Victor | Victor | unchanged |
| `reports/run_scheduled.py`, `run_nightly.py`, `email_gen.py` (decision 007); `reports/hub.py`, `scorecard.py`, `weekly.py` (007, last amendment) | Victor for now | Victor | unchanged |
| Slides, video, submission; the rest of `reports/` and `docs/pitch/` | Orlando | Orlando | see the decision in section 7 |

Two rules that keep us apart: **Dani does not touch `reports/run_scheduled.py` or `reports/hub.py`; Victor does not touch `data/generate.py` or `reports/reconcile.py`.** His August sample already comes from his own simulators, so nothing of his needs the generator. `reconcile.build` keeps its signature, because Victor's test calls it.

### Dani: rules, samples, the command and the page
Two tracks that share no file, so two agents can run them side by side, each in its own worktree. Every "done when" is run from the repo root.

**Track A: the rules** (`reports/reconcile.py`, `reports/bc_export.py`, the mapping)

| ID | Task | Files | Size | Needs | Done when |
|---|---|---|---|---|---|
| D3.1 | **Payout windows: explain every payout, not the month's net.** For each source, rebuild the window of activity each payout covers from its cycle (two new mapping columns, `Payout_Cutoff` and `Payout_Timezone`: eBay `daily`, Eastern; Amazon `previous_day`, Pacific; ShopGoodwill `weekly:SUN`, Pacific, taken from the deposit because there is no payout report). Compare what the files hold for the window with what was paid. Equal: nothing to say. Paid more than the files hold, and the window has days no report covers: `payout_data_gap`, naming the days; the source reads `INCOMPLETE`. Different with no missing day: `payout_mismatch`, and the source stays `UNEXPLAINED`. Activity after the last cutoff: `not_yet_paid_out` with its exact amount and days. This replaces the "fits the last N days" ceiling. | `reports/reconcile.py`, `reports/bc_export.py` (the status), `reports/config/bc_mapping.csv`, `reports/tests/test_reconcile.py`, `test_bc_export.py` | L | C3.2. Exact Pacific windows need `occurred_at` (V3.1): until it is on `main`, test on hand-made rows that have it; on real files the rule falls back to `business_date` and prints that it did | `python -m reports.reconcile --inbox data/sample/messy_month/inbox --month 2026-09` then `python -m reports.bc_export --payload out/close/2026-09/close_payload_2026-09.json` prints `unexplained 0.00` on all three lines, `INCOMPLETE` for Amazon and ShopGoodwill, `OPEN` for eBay; `exceptions_2026-09.csv` has `payout_data_gap,Amazon,-743.10`, `not_yet_paid_out,Amazon,516.32`, `payout_data_gap,ShopGoodwill,-1875.64`, `not_yet_paid_out,ShopGoodwill,5429.93`; a test finds every window equal to `close.payouts[]` in the answer key (`net_in_files_cents`, `data_gap_cents`) |
| D3.2 | **Nothing dropped in silence.** A marketplace with rows but no mapping row goes into the payload, so the export lists it as `unmapped_source`, not posted. The payload field `mock` (it reads "reconciled from the raw inbox" on a real run) is renamed `origin`. | `reports/reconcile.py`, `reports/bc_export.py`, tests | S | | a test with one `other` row gets an `unmapped_source` exception with effect `not_posted`; `grep -c '"mock"' out/close/2026-09/close_payload_2026-09.json` prints 0 |
| D3.3 | **Owned exceptions.** A small config, exception kind to owner (a role; placeholder names) and what to do about it. The exceptions file gains two columns at the end. | new `reports/config/close_exceptions.csv`, `reports/bc_export.py`, test | S | | the first line of `out/close/2026-09/exceptions_2026-09.csv` reads `Kind,Source,Amount,Effect,Detail,Owner,Action` and no row has an empty owner |
| D3.4 | **Read the engine's bank and payout files** and delete the two readers in `reconcile`. | `reports/reconcile.py` | S | V3.2 on `main` | `grep -c "def read_bank\|def read_payouts" reports/reconcile.py` prints 0 and D3.1's output is unchanged |
| D3.5 | **Shipping cost, the two rules slide 38 spells out.** Carrier payments (OSM, PB, EasyPost) from the bank's debits, account 0101 = GL 10009. FedEx from a Business Central ledger export filtered to GL 40356, Dept 180, vendor V00122, with the BNKDEPOSIT refunds netted. Output: net shipping cost per carrier beside the shipping charged to buyers, as control totals; a journal document only for the bank-paid carriers, on a placeholder expense account. Needs new synthetic rows in both samples. | `data/generate.py`, `reports/reconcile.py`, `bc_export.py`, mapping, tests | L | D3.1, V3.2, V3.5 | `control_totals_2026-09.csv` has one line per carrier and FedEx's net equals charges minus refunds in the answer key. **First on the cut list: it starts only if checkpoint 1 is fully green at 11:00** |

**Track B: samples, the command, the page** (`data/generate.py`, `reports/close.py`, `reports/close_report.py`, docs)

| ID | Task | Files | Size | Needs | Done when |
|---|---|---|---|---|---|
| D3.6 | **A tidy month for the close.** The same September orders as `messy_month`, every report downloaded once, in the same formats, with the bank file and a `close` answer key. Its own random stream, so every existing sample stays byte for byte the same. Named `tidy_month` because `clean_month` is taken (older formats, no bank file) and because `run_scheduled.month_inbox` takes the first sample in name order: a name after `messy_month` keeps the scheduled close on the messy month without touching Victor's file. | `data/generate.py`, `data/sample/tidy_month/`, `data/README.md`, new `reports/tests/test_close_tidy_month.py` | M | | `python data/generate.py`, then `git status --short data/sample` lists only `data/sample/tidy_month/`; `reports.reconcile` and `reports.bc_export` on it print three `OPEN` lines with `unexplained 0.00`, and its exceptions are only `in_transit` and `not_yet_paid_out`; a test pins `run_scheduled.month_inbox("2026-09")` to `messy_month` |
| D3.7 | **One command, an archive, a status file.** `python -m reports.close --inbox DIR --month M [--out] [--archive] [--dest]` runs reconcile, export and page, then copies the inputs and outputs to `<archive>/Accounting/Month End/<year>/<month>/Journal Entries/E-Commerce JEs/<run id>/` (slide 39's own path; default root `out/archive`) with a `manifest.json` (file, bytes, SHA-256, rows read, rows rejected), writes `close_status_<month>.json` and appends a line to `runs.csv`. Tests write to a temporary folder, never to the real `out/`. | new `reports/close.py`, `reports/tests/test_close.py` | M | C3.3 | the command prints one line per step of slide 40 (`ACQUIRE` to `RECONCILE`) and ends `posting: NOT POSTED (import files ready)`; the archive folder holds the inbox files, the four CSVs, the payload and the manifest; a second run adds a second line to `out/close/2026-09/runs.csv`; exit 0 |
| D3.8 | **The page says what it is.** A banner: synthetic sample data, placeholder account numbers except Dept 180, import files, not posted. An `INCOMPLETE` pill. The posting status and the run history from D3.7. A table of Goodwill's nine sources (slide 38's own wording from a config file) with our state for each: captured, days missing, or not modeled. | `reports/close_report.py`, new `reports/config/close_sources.csv`, test | M | D3.7; days missing come from V3.3 when it lands, from `reconcile`'s file-name check until then | `python -m reports.close_report --month 2026-09` writes a page whose text contains "Synthetic sample data", "placeholder" and "Not posted", and nine source rows, six of them "not modeled" |
| D3.9 | **Late files, then a re-run.** The generator also writes the two reports nobody downloaded (Upright September 7, Amazon September 21-22) into `data/sample/messy_month/late/`, and the key says what the close reads once they arrive (`close_after_late`). | `data/generate.py`, test, the demo script | S-M | D3.1, D3.6 | copy the inbox and `late/` into one folder and run D3.7's command on it: Amazon and ShopGoodwill print `OPEN`, no `payout_data_gap` is left, and `runs.csv` shows both runs |
| D3.10 | **Our rules, written down** (slide 41, workstream 3): one line per rule the close applies, where it is configured, and whether it comes from the deck or is our assumption. | new `docs/contracts/close-rules.md` | S | D3.1 | every exception kind and every column of `bc_mapping.csv` appears in it; the rows marked "assumed" equal the new close rows in `docs/ASSUMPTIONS.md` |
| D3.11 | **Demo script for the close, and its disclosures**: the three runs of section 2, one rule edited in `bc_mapping.csv` with the journal changing, and the "not built" list as the lines for "built versus used". | new `docs/pitch/demo_script_close.md` | S | D3.7 | a person who did not write it runs it top to bottom from a fresh clone and sees what it says |
| D3.12 | Status: `docs/members/dani.md`, the phase 3 rows of `docs/PHASES.md`, the close assumptions in `docs/ASSUMPTIONS.md` (shared files: claim them first) | docs | S | | they describe what is on `main` |

### Victor: what the engine hands over, the runner, the store
In this order. V3.1 comes first because it is the only task Dani's numbers depend on.

| ID | Task | Files | Size | Needs | Done when |
|---|---|---|---|---|---|
| V3.1 | **`occurred_at` on every transaction** (`transaction.md` v0.5, appended, so nothing breaks): the moment of the sale or refund as ISO 8601 with its offset; empty when the export gives only a date (eBay) or only a file name. Several lines of one order: the first line's time. The store ignores the column. | `engine/sources/`, `engine/contract.py`, `docs/contracts/transaction.md`, test | M | | `python -m engine run --inbox data/sample/messy_month/inbox --out out/tmp --date 2026-09-30` writes a header ending `units,occurred_at`; a test sums gross + shipping + handling - fee over the rows whose `occurred_at`, read in Pacific time, falls in each window and gets the answer key's `net_in_files_cents`: Amazon Sep 1-14 = 405,400 and Sep 15-28 = 415,074; ShopGoodwill Sep 1-6 = 1,088,878, Sep 7-13 = 1,344,329, Sep 14-20 = 1,329,924, Sep 21-27 = 1,370,702 |
| L6 | The weekly page from the KPI file (his list) | | M | | his list |
| V3.2 | **The engine writes `payouts.csv` and `bank.csv`** instead of skipping payout rows and rejecting the bank file. Payouts de-duplicated across overlapping downloads. Bank rows signed, credits positive, debits included. | `engine/sources/`, `engine/writer.py`, new `docs/contracts/close-inputs.md`, tests | M | C3.1 | the same `engine run` writes `out/tmp/payouts.csv` with 31 rows (29 eBay, 2 Amazon) and `out/tmp/bank.csv` with 26 rows (24 credits, 2 debits), and `warnings.json` has no `unparseable` entry for `bank_activity_2026-09.csv` |
| V3.3 | **`source_coverage.json`**: per marketplace, the files read, the days each file says it covers, and the days of the month no file covers. Replaces the file-name check in `reconcile`. | `engine/status.py` or beside it, contract, test | S-M | C3.1 | on `messy_month` it lists `2026-09-21` and `2026-09-22` missing for Amazon, `2026-09-07` for ShopGoodwill, none for eBay |
| V3.4 | **The scheduler calls the one command, and the store remembers the run**: `run_scheduled` runs `python -m reports.close` on the 1st in place of the three commands; a `runs` row with `command = 'close'` (`store.md`); the portal card links the status file. | `reports/run_scheduled.py`, `reports/hub.py`, `engine/store/`, `docs/contracts/store.md` | S | D3.7 on `main`; until then nothing changes | `python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04` exits 0 and prints `close page: reports/close/2026-09.html`; `python -m engine.store status` shows a close run |
| L8, L7 | His list. For L7 the close part is D3.11: link it | | S, S-M | D3.11 | his list |
| V3.5 | **A Business Central ledger export for the FedEx rule**: parse a G/L entries file into `ledger.csv`. Only if D3.5 goes ahead. | `engine/sources/`, contract | S | checkpoint 1 | cut with D3.5 |
| V3.6 | **A close email**: a `Close` report type in `subscribers.csv`, an `.eml` to accounting with the page and the four CSVs attached, generated, not sent. | `reports/email_gen.py`, `reports/config/subscribers.csv` | S-M | D3.7 | `out/outbox/<run date>/` has one close email per active subscriber. Cut early |

## 4. Contracts first

Written between 08:00 and 08:45, before any code. The shapes below are the drafts: the owner copies them into the file and changes what he or she must.

| ID | Contract | Owner | Consumers | Change |
|---|---|---|---|---|
| C3.1 | `docs/contracts/close-inputs.md` (**new**) | **Victor** | Dani (`reports.reconcile`) | what the engine writes for the close |
| | `docs/contracts/transaction.md` v0.5 | Victor | everyone | `occurred_at` appended (with V3.1) |
| C3.2 | `docs/contracts/close-payload.md` v0.4 | **Dani** (was Orlando) | `reports.bc_export` | payout windows, two exception kinds, `INCOMPLETE`, `origin`, owner |
| C3.3 | `docs/contracts/close-outputs.md` (**new**) | **Dani** | Victor (`run_scheduled`, `hub`, `email_gen`) | the command, exit codes, the files, the status file |
| | `docs/contracts/store.md` v0.5 | Victor | | `runs.command` gains `close` (with V3.4) |
| C3.4 | Decision 009 accepted or changed; claim rows in `docs/CLAIMS.md` | both | | Victor adds a response and his rows |

**C3.1, close inputs.** After `python -m engine run --inbox <month inbox> --out <dir> --date <month end>`, `<dir>` holds:

| File | Columns |
|---|---|
| `transactions.csv` | as v0.4, plus `occurred_at` |
| `payouts.csv` | `payout_id` (`<marketplace>:<paid date>`), `marketplace`, `paid_date`, `amount_cents` (positive = paid to Goodwill), `source_file`, `source_row` |
| `bank.csv` | `bank_txn_id` (`<file>:<row>`), `posting_date`, `description`, `amount_cents` (credit positive, debit negative), `balance_cents` (empty if the export has none), `source_file`, `source_row` |
| `source_coverage.json` | `{"month": "2026-09", "marketplaces": {"amazon": {"files": [{"name": "...", "from": "2026-09-01", "to": "2026-09-20", "rows": 0}], "days_missing": ["2026-09-21", "2026-09-22"]}}}` |

A file the engine cannot read stays a warning, never silent.

**C3.2, close payload v0.4.** Additions only: each entry of `payouts` gains `activity_from`, `activity_to`, `files_net_cents`, `gap_cents`. New exception kinds: `payout_data_gap` (effect `open_balance`, amount negative, as v0.2 already allows for "a payout for activity missing from our files") and `payout_mismatch` (effect `info`; it is what leaves a source `UNEXPLAINED`). New control status `INCOMPLETE`: nothing unexplained, but at least one `payout_data_gap`. Order of precedence: `MISMATCH`, `UNEXPLAINED`, `INCOMPLETE`, `OPEN`, `RECONCILED`. `mock` becomes `origin`. Exceptions may carry `owner` and `action`.

**C3.3, close outputs.** `python -m reports.close --inbox DIR --month YYYY-MM`. Exit 0: files written, whatever the statuses. Exit 1: a document does not balance, nothing written. Exit 2: the files failed the read-back check. In `out/close/<month>/`: the four CSVs, the payload, `runs.csv`, and
```json
{ "month": "2026-09", "run_id": "2026-10-01T00-15-07", "inbox": "data/sample/messy_month/inbox",
  "sources": {"amazon": {"status": "INCOMPLETE", "open_cents": 466706, "unexplained_cents": 0}},
  "journal": {"lines": 56, "documents": 25, "balanced": true}, "invoices": {"documents": 1, "lines": 3},
  "exceptions": {"total": 16, "by_kind": {"payout_data_gap": 2}}, "needs_review": true,
  "posting": {"status": "not_posted", "reason": "no Business Central connection: import files only",
              "checks": ["every document sums to 0.00", "files read back and re-checked"]} }
```
The page is `reports/close/<month>.html`, as today. (The counts in the example are illustrative.)

## 5. Order of work, checkpoints, cuts

The clock assumes both start at 08:00. Anything done tonight is a head start; the checkpoints do not move.

| Time | Dani, track A | Dani, track B | Victor |
|---|---|---|---|
| 08:00 | contracts C3.2, C3.3; claim rows | | C3.1; response to decision 009; claim rows |
| 08:45 | D3.1 | D3.6 | V3.1, then L6 |
| 10:00 | D3.1 | D3.7 | V3.2 |
| **11:00** | **Checkpoint 1** | | |
| 11:00 | D3.2, D3.3 | D3.7, then D3.8 | V3.3 |
| 12:00 | D3.4 (once V3.2 is in); D3.5 only if checkpoint 1 was fully green | D3.9 | V3.4, L8 |
| 12:30 | | D3.10, D3.11 | L7 (links D3.11) |
| **13:00** | **Checkpoint 2: phase 3 takes no more features** | | |
| 13:00 | dry run of the demo script from a fresh clone | | |
| 13:30 | record; a second take if needed until 14:30 | | |
| 14:30 | slides, "built versus used", sources cited; first submission by 15:00 | | |
| 15:00 | feature freeze for everything (`CLAUDE.md`): bug fixes only, one integrator merges | | |
| 15:45 | last push, final submission | | |
| 16:00 | freeze | | |

**Checkpoint 1, 11:00. Every cent on both months.** On `main`: V3.1, D3.1, D3.6. Check: the two commands of D3.1 on `messy_month` print `unexplained 0.00` three times with Amazon and ShopGoodwill `INCOMPLETE`; the same two commands on `tidy_month` print three `OPEN`.
- **Tripwire:** if V3.1 is not on `main` at 11:00, Dani opens that PR herself (decision 009 allows it in advance; it is a change in `engine/sources/` and Victor reviews it). Without the column, payouts that are in fact exact show false differences ($12.99 and $72.00 on two ShopGoodwill payouts of the messy month, and the two real gaps come out $23.26 and $35.99 wrong). The same happens on the tidy month, and the clean example stops being clean.
- If D3.1 is not done: everything else of track A waits behind it, and D3.5 is cut on the spot.

**Checkpoint 2, 13:00. One command, both months, from nothing.** On `main`: D3.7, D3.8, and whatever else made it. Check, from a fresh clone with `out/` empty: `python -m pytest engine recon reports -q` passes; `python -m reports.close` on `tidy_month` and then on `messy_month` exits 0 both times and the page shows the banner and the nine sources; `python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04` exits 0. What is not on `main` now goes on the "not built" list, in the script and on the slide.

**Cut order** (first to go first):
1. D3.5 with V3.5, the shipping cost rules. Six sources stay "not modeled" and we say so.
2. V3.6, the close email.
3. D3.9, the late files and the re-run. The demo keeps two runs.
4. D3.3, owners on exceptions.
5. V3.3, the coverage file. `reconcile` keeps reading file names.
6. V3.2 with D3.4. `reconcile` keeps its own readers for the bank file and the payout rows.
7. The store's `runs` row in V3.4. `runs.csv` in the close folder stays.
8. D3.10 shrinks to a table inside `close-payload.md`.

**Never cut:**
- Every journal document sums to 0.00, or nothing is written.
- No amount netted out of sight: the $226.78 and ShopGoodwill's $1,875.64 are split per payout, or the source reads `UNEXPLAINED`. We never widen a tolerance to make a number go away.
- The close runs on a tidy and a messy month, one command each, in one take.
- The labels: synthetic data, placeholder accounts, import files not posted, and which of the nine sources are not modeled.
- Answer keys computed from the generated orders, never by the code they check.
- `main` green.

## 6. Open questions for Goodwill, and what we do until they answer

Amanda was listed for Saturday only, so these may stay open. Each default is one place in the code or the config.

| # | Question | Default we use |
|---|---|---|
| 1 | How do entries get into Business Central today: pasted into the General Journal grid, Edit in Excel, a configuration package, an API? Cloud or on-premises? | CSV in the column order of the General Journal and Sales Invoice pages, for paste or Edit in Excel. Nothing posts |
| 2 | The real chart of accounts, customer numbers and dimensions for e-commerce | Placeholders in `bc_mapping.csv`, one row per source, except Dept 180 from slide 38 |
| 3 | Which sources post by journal and which through the AR invoice? Slide 39 has journal entry tabs "for each report" and one Invoices tab | ShopGoodwill by invoice, eBay and Amazon by journal: one column, `Path` |
| 4 | Can we see last month's E-Commerce Allocation workbook (tabs, orange fields, formulas) and "the attachment" slide 41 mentions? | Our rules as listed in `close-rules.md`; no comparison with the workbook |
| 5 | ShopGoodwill "Period 1 periodic only; Period 3 all reports": what are the periods, and what does each report feed? | Not modeled. ShopGoodwill sales come from Upright; its payouts are assumed weekly, Monday to Sunday, Pacific |
| 6 | What entry does the workbook make from the FedEx lookup (GL 40356, Dept 180, V00122, net of BNKDEPOSIT refunds) and from the bank lookup for OSM / PB / EasyPost (acct 0101, GL 10009)? An allocation across departments? | If D3.5 is built: net cost per carrier as a control total, and a journal only for bank-paid carriers on a placeholder account. Otherwise not modeled |
| 7 | The Jewelry Report and "Co-Pivot populates Supplier": what is Supplier used for in the close? | Not modeled |
| 8 | Cash Monkey's full-month orders beside the eBay and Amazon portal reports: which one drives which journal line? | eBay and Amazon totals come from their own reports; the Cash Monkey month file is not read at close, to avoid counting sales twice |
| 9 | The Goodwill Books statement is "prior-month": does it post a month late? | Not modeled; rows for that channel become an exception, not posted |
| 10 | A payout larger than our files explain (a report was not downloaded): hold the source back, or post what we have and flag it? | Post and flag `INCOMPLETE`, naming the days |
| 11 | Is a refund of a prior-month order posted in the month it is issued? Is money paid out but not yet in the bank left as a receivable at month end? | Yes to both, each flagged or listed |
| 12 | Matching deposits to payouts: to the cent? How many days can a payout take? | To the cent, no tolerance; up to 5 days before the deposit; one deposit may cover several payouts of one source |
| 13 | Who owns each kind of exception, and who approves the journal before it posts? | Role names in `close_exceptions.csv` (placeholders); no approval step |
| 14 | Where does the archive live ("Accounting / Month End / year / month / Journal Entries / E-Commerce JEs")? | The same folder names under `out/archive`; the root is a setting |
| 15 | Posting date and document numbering | Last day of the month; `ECOM-<yymm>-<source>`, `BNK-<mmdd>-<source>`, `SI-ECOM-<yymm>-<source>` |

## 7. Risks, and one decision that is open

- **One column carries the exactness.** D3.1 is exact only with `occurred_at`. It is first on Victor's list and has a tripwire at 11:00.
- **Nobody is confirmed to record and submit.** The slides, video and submission are Orlando's and he is away. The recording window (13:30 to 14:30) is fixed by the freeze. **Default until Dani decides otherwise:** if Orlando has not confirmed by 11:00, Dani records the close, Victor records phases 1 and 2 with his L7 script, and Dani assembles the slides and submits. Dani is also the one integrator from 15:00.
- **The rules are ours.** "Automates the rules" is true of the rules we could infer and put in config. The workbook's own rules are unseen. The page banner, the nine-source table and the "not built" list are what keep this from being an overclaim; they are on the never-cut list for that reason.
- **Three agents in `reports/`.** Dani's two tracks and Victor all edit that folder. The file table in section 3 has no overlap; anyone who needs a file outside their row asks first.
- **The generator must not disturb the other samples.** D3.6 and D3.9 add to `data/generate.py`; a changed byte in an existing sample breaks phase 1 and 2 tests. Each task's "done when" checks `git status data/sample`.
- **Five hours is five hours.** Dani's two tracks add up to about seven hours of work for two agents; D3.5 does not fit unless checkpoint 1 is early, and the plan says so in advance rather than at 12:55.
