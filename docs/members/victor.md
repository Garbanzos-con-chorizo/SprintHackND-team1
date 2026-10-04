# Status — Victor (core engine `engine/`; phase 2: store, internal API, exports, nightly run)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 23:30 · **Branch:** victor/store-loader

## Phase 2 (now): decision 007, plan in `docs/PLAN_PHASE_2_3.md`
**Decision 007:** agreed by all three, SQLite included (Orlando's amendment at 21:30, my response appended). Tripwire: if September isn't in the store by 10:00 Sunday, the KPIs read the files instead.

### Done
- **V2.1 + V2.2** (branch `victor/store-loader`): `engine/store/` with `connect`/`init` (path: `--db`, else `ECOM_DB`, else `out/store/ecom.db`) and `load_day`. Command: `python -m engine.store init`, `python -m engine.store load --in-dir out --date D`. 15 tests in `engine/tests/test_store.py`: re-run changes nothing, dropped rows disappear, moved rows move, other dates untouched, failures (missing or wrong pulse, bad CSV, failure halfway through the writes) leave the previous load and log a `failed` run, plus one September day through the real engine + pulse + load against `expected.json`.
- **Checked by hand:** all of September from `clean_month`, run with the real commands (engine run -> recon.pulse -> store load, one day at a time): **month revenue in `v_monthly` = 7,075,396 cents = the answer key, to the cent**; 30 of 30 days ok for ShopGoodwill, eBay and Amazon; `other` has NULL, not 0; 2,425 transactions; about 1.4 s a day (41 s for the month), mostly the engine reading the month spreadsheet.
- Contracts (merged, #16):
  - **C3** `docs/contracts/store.md` + `engine/store/schema.sql`: tables `transactions`, `pulse_daily`, `internal_daily`, `runs`, `warnings`, `kpi_values`; views `v_daily`, `v_weekly` (ISO weeks, Monday start), `v_monthly`. Checked in memory: the schema runs twice without error, and the views give NULL (not 0) for days with no data. **Dani: enough to build your test database now** (snippet in `store.md`, "Rules for readers").
  - **C4** `docs/contracts/internal-api.md`: 4 endpoints and the 10 metrics Dani's `kpi.md` asks for (names unchanged), 14 categories; category sales scaled to the pulse revenue.
  - Pitch notes for the store (rubric points, demo moments, what not to claim): `docs/contracts/store.md`, "For the pitch".

### Next, in order (sizes S < 30 min, M 30-90 min)
| ID | Task | Size | Target |
|---|---|---|---|
| V2.3 | `store status` (views already in the schema) | S | 08:30 |
| V2.4 | `store backfill`: September from `clean_month` (one month file per marketplace, so engine runs once per date on the same inbox); month revenue = `expected.json` | M | **10:00 tripwire** |
| V2.5 | `engine/internal_api/`: client + mock per `internal-api.md`; `reports/mock_api.py` re-exports it until Orlando switches | M | 10:45 |
| V2.6 | `internal_api pull`, included in backfill | S | 11:00 checkpoint 1 |
| V2.11 | `run_nightly`: add store load, internal pull, kpi | S | after CP1 |
| V2.8 | `export kpi-csv` from the KPI file (against Dani's sample file) | S | |
| V2.9 | `export pdf`: headless Edge prints Orlando's scorecard page (needs O2.4); goes to Orlando if late | M | |
| V2.10 | Attach the PDF to Orlando's `email_gen.py` `.eml` (already writes drafts) | S | |
| V2.7 | `units` in parsers + `transaction.md` (the `units` column already exists in the store, NULL for now) | S-M | if time |
| V2.12 | August sample for growth | M | cut first |
Then phase 3, with Orlando's `reports/bc_export.py` already on `main`.

### Blocked / needs from others
- None on Dani: `kpi.md` + sample KPI files are on `main` (#15); V2.8 codes against them.
- Orlando: print layout (O2.4), for V2.9. And read my SQLite response in 007.

## Done (phase 1)
- Phase split of all tasks: `docs/PHASES.md`
- Phase 1 transaction contract (draft): `docs/contracts/transaction.md`, mock `docs/contracts/examples/transactions.sample.csv`
- Handoff map: `docs/HANDOFFS.md` (PR #4)
- `out/.gitignore` so generated output is not committed (no root file touched)

- V1 scaffold in `engine/` (branch `victor/v1-scaffold`): `python -m engine run` writes valid empty `transactions.csv`, `source_status.json` (all sources `missing`) and `warnings.json`; 2 tests pass. No parsers yet.

- Acquisition: `python -m engine fetch` runs scrapers and logs to `out/fetch_log.json`. After the Oct 3 meeting (Amanda: assume an Upright API that emails Excel) the browser backend was removed; Upright is an API stub; reports arrive by email into the inbox. Decisions 003 (superseded in part), 004 (Orlando: Amanda's answers) and 005 (mine: API, email delivery, run schedule).
- Cleanup branch `victor/api-email-cleanup`: removed `engine/scrapers/browser.py`, `requirements-browser.txt` and the Playwright test; wrote decision 005 (API + email, run schedule options) and updated `docs/ASSUMPTIONS.md`. 81 tests pass.
- P-V4 (branch `victor/p-v4-source-status`): `source_status.json` is now real, keyed by marketplace (`ok` / `stale` / `missing`), built from the files read and the rows for the day (`engine/status.py`). Verified end to end: `python -m engine.tools.make_sample --scenario messy_day --check --pulse` runs the engine and Dani's `recon.pulse` and compares the pulse to the answer key. 91 tests pass.
- `victor/parser-aliases`: ran Orlando's real-format samples (Upright + Cash Monkey .xlsx) through the engine and Dani's pulse; found and fixed Upright `Payment Date` alias, Pacific timezone for Upright timestamps, customers = orders for Upright, and Cash Monkey `Market Fees` alias. All 8 sample scenarios now match their answer keys through the pulse (24 of 24 marketplace-days); `run_nightly --real` works on Python 3.12. 93 tests pass.
- Out of scope by decision: brick and mortar, an Excel-to-CSV converter (the engine reads .xlsx directly), a 'late' state.

- V3 parsers (branch `victor/v3-parsers`, stacked on the scraper skeleton): ShopGoodwill, eBay, Amazon on a shared `OrderReportParser`; money/date cleaning in `engine/clean.py`; 56 tests pass. Checked against Orlando's synthetic samples (`data/sample/*`): 64 of 66 marketplace-days off at first, now all match except the overlapping eBay re-download, which needs P-V5. Column names are still not from real Goodwill files, and ShopGoodwill's layout is a guess on both sides. Not yet done: cross-file dedupe (P-V5), source status (P-V4), day cutoff config (P-V3 beyond timezone).

- P-V5 cross-file dedupe (`engine/dedupe.py`): keeps the first copy, logs the rest, flags conflicting amounts. All 5 of Orlando's scenarios now match their answer keys (0 of 66 marketplace-days off).
- `docs/contracts/source-formats.md`: what the deck actually shows about the real files. **Finding: the nightly ShopGoodwill file is probably Upright's Paid Orders report and eBay/Amazon probably come from one Cash Monkey Orders CSV, not the seller-portal reports our samples imitate.** Orlando should read it before changing `data/generate.py`.

- Pluggable ingestion (branch `victor/ingest-framework`): `engine/ingest/` with `DataIngestAdapter.fetch_and_normalize()`, `EmailAttachmentAdapter` (CSV/TSV/TXT/XLSX from the inbox folder, which is also where manual exports and ERP file drops land), `MockScraperAdapter` (synthetic fixture, no network), and `ingest()` which merges adapters and dedupes. `python -m engine run` now goes through it. 8 new tests, 70 in total.

- Sample generator + checker (branch `victor/sample-generator`): `python -m engine.tools.make_sample --scenario clean_day|messy_day --check` writes synthetic Upright and Cash Monkey files shaped like the deck shows, an answer key computed from the generated orders, then runs the pipeline and compares. Added parsers `engine/sources/upright.py` and `cashmonkey.py` (columns partly guessed). Both scenarios match; 82 tests pass.
- `docs/ASSUMPTIONS.md`: every assumption, why, and confidence (for the pitch).

### Assumptions (stated on purpose, change any of them and tell Victor)
1. **Lane and paths:** the request named `src/ingest/` and `tests/test_ingest.py`. Our lane is `engine/` and new top-level dirs need a decision record, so it lives in `engine/ingest/` and `engine/tests/test_ingest.py`. Branch is `victor/ingest-framework` (team convention) not `feature/ingest-framework`.
2. **Reuse, not rewrite:** reading and cleaning reuse the existing source parsers (ShopGoodwill, eBay, Amazon). "Normalized format" means the canonical transaction CSV in `docs/contracts/transaction.md`.
3. **Email is a folder:** we do not connect to a mailbox. Someone saves the attachment (or the ERP's export) into `inbox/`. Reading an actual email account is not built.
4. **ERP drop = a file drop:** an ERP export is only supported if it is CSV/XLSX and a parser exists for its columns. No ERP API.
5. **Extensions:** `.csv .tsv .txt .xlsx`. Legacy `.xls` and `.xlsm` are reported as a warning, not read. Only the first sheet of a workbook is read.
6. **Sources are the three we have parsers for**, whose column names come from the team's synthetic samples, not real Goodwill files (see `docs/contracts/source-formats.md`: the real nightly sources are probably Upright and Cash Monkey, which have no parser yet).
7. **Scraper is a stub:** `MockScraperAdapter` is handed the records a scraper would have extracted (a JSON fixture or a list of dicts keyed by the source's column names). No login, no network, no paging, no retries. The real scrapers in `engine/scrapers/` are separate and still skeletons.
8. **Duplicates across adapters:** the same transaction from two adapters counts once; the first adapter's copy wins and the other is logged.

## Phase 1 leftovers
Phase 1 runs end to end (all 8 sample scenarios match their answer keys through the pulse). The old in-progress, blocked and next lists are replaced by the phase 2 section above. Open from phase 1: real column names for Upright and Cash Monkey when real files arrive; the portal discovery step in decision 003.

## How to run / test my part
Store (phase 2), from the repo root, after `engine run` and `recon.pulse` for the date:
```
python -m engine.store init
python -m engine.store load --in-dir out --date 2026-09-14
```
From the repo root, Python 3.11+:
```
pip install -r engine/requirements.txt
python -m engine run [--inbox inbox] [--out out] [--date YYYY-MM-DD]
python -m pytest engine -q
```
(These commands are not yet in `CLAUDE.md`, to avoid touching a shared file; add them when someone claims it.)

## Requests to me (append only: `- [from X, time] request`)
- [from Orlando, 2026-10-03 18:00] **Upright and Cash Monkey parsers + per-source timezone for naive timestamps.** Sample files are in `data/sample/gw_day_clean`, `gw_day_cashmonkey_missing`, `gw_day_duplicates` (`.xlsx`, as emailed per decision 004), each with `expected.json`. Today `engine run` rejects both files ("no source recognizes this file"). Asks: (1) parser for Upright `paid_orders_*.xlsx`: one row per order, `Payment Date` naive **Pacific**, revenue = `Subtotal`, buyer = `Channel Buyer`; (2) parser for Cash Monkey `orders2023-*.xlsx`: one line per unit (sum rows per `Order ID`, as the Amazon parser does), `Order Date` naive **UTC**, `Channel` `eBay` / `Amazon-MF` -> marketplace, gross = `Item Price`, fee = `Market Fees`; (3) a timezone setting per source, used by `parse_business_date` for naive values only (zone-tagged values already convert correctly). Impact if (3) is missing: on `gw_day_clean` 17 Cash Monkey rows land on the wrong day, on `gw_day_duplicates` 27. Cash Monkey column names are guesses (the deck never shows the CSV); Upright's are from the slide 26 screenshot. Answer keys count customers by order for all three, matching the staff practice in `source-formats.md`.
- [from Dani, 2026-10-03 20:40] **Phases 2 and 3 plan: please accept or change `docs/decisions/007-phase-2-3-owners-database-scorecard.md`; the detail is in `docs/PLAN_PHASE_2_3.md`.** It proposes that in phase 2 you own the database (SQLite, `engine/store/`), the internal API mock and client (`engine/internal_api/`, moved from `reports/mock_api.py`), the exports (KPI CSV, PDF, `.eml`) and `run_nightly`. Phase 3 (Business Central) is a separate task, not assigned to anyone: we split it in three once phase 2 reaches its first checkpoint. First asks, so I am not blocked: (1) `docs/contracts/store.md` + `engine/store/schema.sql` (tables in section 6 of the plan), enough for me to build a test database; (2) `docs/contracts/internal-api.md`, I will list the fields the 15 KPIs need; (3) a `units` column in `transactions.csv`. Your phase 2 list is the longest: the PDF command can go to Orlando if it gets tight.
- [from Orlando, 2026-10-03 21:00] **Decision 007: ownership accepted, so these are yours now** (my response is appended to 007). Working and on `main`: `reports/email_gen.py` (reads `reports/config/subscribers.csv`, writes one `.eml` per active subscriber per report to `out/outbox/<run date>/` with `X-Unsent: 1` so Outlook opens it as a draft, plus `manifest.csv`; bad rows are listed, not fatal), `reports/run_scheduled.py` (`--date D` or `--from/--to`: nightly pulse every night, weekly when D+1 is Monday, monthly when D+1 is the 1st, then emails), `reports/run_nightly.py` (now real by default, isolated `out/<scenario>/`, files each pulse in `out/pulse/<date>.json`), `reports/mock_api.py`. Move them to `engine/` whenever you like; `reports/hub.py` only needs the pages to land in `reports/pulse|weekly|monthly`. Note: we are **not** taking SQLite (see 007 response): keep the flat files, with the internal API snapshot as `out/internal/<date>.json`.
- [from Orlando, 2026-10-03 21:30] **SQLite: we're on board after all** (amendment appended to decision 007). The nightly store is yours as Dani planned (`engine/store/`): load `transactions.csv`, the pulse rows, the internal API snapshot, run history and KPI history after each run; keep the CSV/JSON files as the engine -> pulse contract. Useful inputs already on `main`: the pulse history in `out/pulse/<date>.json` (filed by `run_nightly`), and `data/sample/clean_month` + `messy_month` for a month of data. Phase 3 is **not** deferred: the BC export (`reports/bc_export.py`) keeps going in parallel; when the store exists, the close payload can be read from it (`docs/contracts/close-payload.md`).
