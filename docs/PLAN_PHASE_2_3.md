# Plan: phase 2 (database, KPIs, dashboard, exports) and phase 3 (Business Central)

Written 2026-10-03 20:30 EDT by Dani's agent. **Status: proposed**, see `docs/decisions/007-phase-2-3-owners-database-scorecard.md`. It replaces the phase 2 and phase 3 rows of `docs/PHASES.md` once Victor and Orlando accept it. Sizes: **S** < 30 min, **M** 30-90 min, **L** 90+ min.

**Time left:** code freeze is Sunday 15:00, submission 16:00. That is one working morning. Everything below is ordered so that each checkpoint leaves something demo-able, and the cut order in section 9 says what goes first.

## 1. Where we want to get

```
inbox/ ──> engine run ──> out/transactions.csv ──> recon.pulse ──> out/pulse/<date>.json      (phase 1, works)
                                   │                                    │
                                   └──────────┬─────────────────────────┘
                                              v
internal API (mock) ──pull──>  DATABASE (SQLite): transactions, pulse_daily, internal_daily, runs
                                              │   views: daily, weekly, monthly
                                              v
                                recon.kpi  ──> out/kpi/<period>.json   15 KPIs, 5 areas x 3
                                              │
                    ┌─────────────────────────┼──────────────────────────┐
                    v                         v                          v
            dashboard (HTML)        scorecard PDF + email (.eml)     KPI CSV (Excel / Power BI)

phase 3:   DATABASE + bank file + mapping rules ──> close ──> general_journal_<month>.csv, ar_invoice_<month>.csv,
                                                             control_totals_<month>.csv, exceptions
```

Phase 2 is done when: one command loads a night into the database, one command computes the 15 KPIs for a day, a week or a month, the dashboard shows them, and the same numbers come out as a PDF and a CSV.
Phase 3 is done when: the messy month produces balanced Business Central files plus a list of exceptions, checked against `data/sample/messy_month/expected.json`.

### The 15 KPIs (deck slide 35, "15 KPIs create one COO operating view")
| Area | KPI 1 | KPI 2 | KPI 3 |
|---|---|---|---|
| Financial | Total e-commerce revenue | Revenue growth % | Net margin % |
| Productivity | Listings created | Revenue per labor hour | Listings per employee |
| Inventory | Days from donation to listing | Unlisted inventory backlog | Unsold inventory % |
| Sales | Average selling price | Sell-through rate | Sales per employee |
| Category + Customer | Top 10 categories by revenue | Top 10 categories by margin | Repeat buyer rate |

This replaces the five groups in decision 006 / `docs/pitch/kpi_catalog.md` (Financial; Listings & Production; Sales Effectiveness; Category Effectiveness; Customer & Marketplace). Using Goodwill's own scorecard, word for word, is the stronger Partner Fit answer. Definitions are in section 5.

## 2. Where we are (checked on `main` at 92269e4)

| Piece | Today | Gap to the target |
|---|---|---|
| Nightly pipeline | Works end to end: `engine run` -> `recon.pulse` -> `reports.pulse`, chained by `reports.run_nightly`. Recon tests: 31 pass (run today). Engine tests not run on this machine (no pytest); Victor's status says 93 pass. | None for phase 1. |
| Storage | Files only: `out/transactions.csv` is rewritten on every run, `out/pulse/<date>.json` accumulates. Decision 006 proposed SQLite for app state only. | **No database.** Nothing keeps the transactions, the internal data or the run history across nights. |
| Daily / weekly / monthly | `reports/weekly.py` and `reports/monthly.py` re-read the pulse JSON files and sum them on the fly. | Rollups should be queries on the database, shared by KPIs, dashboard and exports. |
| KPIs | `reports/kpi.py` computes about 12 numbers in the decision 006 groups. The math and the HTML are in the same file, in Orlando's lane. | Of the 15 scorecard KPIs: **3 exist** (total revenue, listings created, revenue per labor hour), **5 are partial** (growth shows n/a without a full prior month; gross margin instead of net margin; average order value instead of average selling price; sell-through is orders / listings; 7 simulated categories instead of a top 10), **7 are missing** (listings per employee, the three inventory KPIs, sales per employee, top 10 by margin, repeat buyer rate). No tests on any KPI. |
| Internal data | `reports/mock_api.py`: 4 in-process functions (labor hours, listings, cost per order, category mix), labelled "Simulated internal data". | No headcount, inventory, donation dates, cost by category. Not shaped as an API (no client interface, no HTTP). Not stored. |
| Dashboard | Static HTML: pulse page, weekly page, monthly scorecard, daily table. | Rebuild the scorecard as 5 areas x 3 KPIs from the KPI file; day / week / month switch; download links. |
| KPI CSV | `reports/monthly/<month>-kpis.csv` and `<month>.csv` exist. | Regenerate from the KPI file so page, PDF and CSV can never disagree. |
| PDF | None. The pulse has print CSS and an email-ready HTML. | One-page scorecard PDF, and an `.eml` with it attached. |
| Business Central | Nothing built. Orlando's CSV schema proposal sits in `docs/members/dani.md`; `rules.md` and `outputs.md` are not written. The engine skips payout and transfer rows; the bank file has no parser. Test data and answer key exist (`messy_month`). | All of phase 3. |
| Web app, Docker | Decision 006, proposed; no `app/` directory. | Stretch. The plan works with static pages and commands; the app, if built, calls the same functions. |

## 3. Who does what (new split)

**Phase 2**
| Person | Owns | Code lives in |
|---|---|---|
| **Dani** | The KPIs: the contract, the 15 calculations, period logic, tests. | `recon/kpi/` |
| **Orlando** | Frontend: scorecard page, period switch, print layout for the PDF, download links. | `reports/` |
| **Victor** | The database and the rest of the plumbing: store and loader, internal API (mock and client), nightly orchestration, PDF / CSV / email export. | `engine/store/`, `engine/internal_api/`, `engine/export/` |

**Phase 3 (Business Central integration) is a separate task with no owner yet.** It will be split between the three of us once phase 2 reaches checkpoint 1. Section 8 lists its steps in three work packages so the split is quick, but nobody is assigned and nobody should start it alone.

Changes against the current docs, all of which need the owners' yes:
- **KPI math moves from `reports/kpi.py` (Orlando) to `recon/kpi/` (Dani).** `reports/` keeps only rendering.
- **The mock internal API moves from `reports/mock_api.py` (Orlando) to `engine/internal_api/` (Victor).**
- **The Business Central export (D2 to D8) is no longer Dani's alone**: it becomes the shared phase 3 task, split in three later. Orlando's schema proposal and messy-month notes in `docs/members/dani.md` are its starting point.
- **`reports/run_nightly.py` becomes Victor's** (it is the pipeline runner, not a page).

**Load check.** In phase 2 Victor still has the longest list (database, internal API, exports), and Orlando still owns the demo script, slides, video and submission (O6 to O9, I4, I5). If checkpoint 1 slips, Orlando takes the PDF command (V2.9), since the print layout is his anyway. Phase 3 only gets the time phase 2 leaves, so the phase 3 split should favour whoever finishes phase 2 first.

## 4. Programs and entry points

Every step is a function with a thin command on top, so the scheduler, a web app or a person can call it.

| Command | Owner | State | What it does |
|---|---|---|---|
| `python -m engine fetch` | Victor | exists | Asks the sources for their reports (Upright stub). |
| `python -m engine run --inbox inbox --out out --date D` | Victor | exists | Parse, clean, dedupe -> `out/transactions.csv`, `source_status.json`, `warnings.json`. |
| `python -m recon.pulse --date D --in-dir out` | Dani | exists | `out/pulse/D.json`. |
| `python -m engine.store init` | Victor | new | Creates the database (`out/store/ecom.db`, path from `ECOM_DB`). |
| `python -m engine.store load --in-dir out --date D` | Victor | new | Upserts the day's transactions, pulse rows, warnings and a run record. Safe to re-run. |
| `python -m engine.store backfill --inbox DIR --from D1 --to D2` | Victor | new | Runs engine + pulse + load for each day of a range (loads September for the demo). |
| `python -m engine.store status [--month M]` | Victor | new | Days present, missing and partial per marketplace. |
| `python -m engine.internal_api pull --date D` | Victor | new | Calls the internal API (mock) and stores the day's snapshot. |
| `python -m recon.kpi --period day\|week\|month (--date D \| --week 2026-W38 \| --month 2026-09)` | Dani | new | Reads the database, writes `out/kpi/<period>.json` and `latest-<period type>.json`. |
| `python -m reports.scorecard --period ... ` | Orlando | adapt `reports.monthly`, `reports.weekly` | Renders the KPI file to HTML. No arithmetic. |
| `python -m engine.export kpi-csv\|pdf\|email --period ...` | Victor | new | KPI CSV, one-page PDF, `.eml` with the PDF attached (generated, not sent). |
| `close --month M` (module decided at the split; `TASKS.md` had it in `recon/`) | phase 3, to be split | new | Matching, exceptions, journal, the three BC CSV files. Exits non-zero and writes no journal if a document does not balance. |
| `python -m reports.run_nightly` | Victor | extend | Nightly chain: fetch -> run -> pulse -> store load -> internal pull -> kpi (day, week to date, month to date) -> render -> export. `--close-month M` adds the close. |

If the web app of decision 006 is built, its routes are wrappers over the same functions: `GET /api/kpis?period=`, `GET /export/kpis.csv`, `GET /export/scorecard.pdf`, `GET /export/bc/<file>.csv`, `POST /api/run`.

## 5. KPI definitions (Dani; these go into `docs/contracts/kpi.md`)

Period = a day, an ISO week (Monday to Sunday) or a calendar month, Eastern time. Revenue is the pulse definition: sales minus refunds, excluding shipping and tax, fees shown separately. **Source:** `files` = from the marketplace exports; `internal` = from the internal API (simulated today, badged on screen); `mixed` = both.

| # | KPI | Formula | Needs | Source | Today |
|---|---|---|---|---|---|
| 1 | Total e-commerce revenue | Sum of revenue over marketplaces with data | pulse_daily | files | exists |
| 2 | Revenue growth % | (revenue - prior period revenue) / prior period revenue. Slide 33 says year over year; we show prior period until 13 months are stored, and label which | two full periods | files | partial |
| 3 | Net margin % | (revenue - marketplace fees - cost of goods - shipping cost - labor cost) / revenue | fees; costs and labor cost | mixed | partial |
| 4 | Listings created | Count of new listings in the period | listings | internal | exists |
| 5 | Revenue per labor hour | revenue / e-commerce labor hours | labor hours | mixed | exists |
| 6 | Listings per employee | listings created / e-commerce employees (average headcount in the period) | listings, headcount | internal | missing |
| 7 | Days from donation to listing | Median of (list date - donation date) for items listed in the period | inventory items | internal | missing |
| 8 | Unlisted inventory backlog | Items sent to e-commerce and not yet listed, at period end | inventory snapshot | internal | missing |
| 9 | Unsold inventory % | Active listings older than 30 days / active listings, at period end (threshold is config) | inventory snapshot | internal | missing |
| 10 | Average selling price | revenue / units sold. Until the transaction file has `units`: revenue / orders, labelled "per order" | `units` column | files | partial |
| 11 | Sell-through rate | units sold / units listed, in the period | units; listings | mixed | partial |
| 12 | Sales per employee | revenue / e-commerce employees | headcount | mixed | missing |
| 13 | Top 10 categories by revenue | Revenue by category, ranked, with share | category of each sale | mixed | partial |
| 14 | Top 10 categories by margin | (category revenue - category cost of goods), ranked, with margin % | costs by category | mixed | missing |
| 15 | Repeat buyer rate | Buyers with 2 or more orders in the period / buyers, only for rows with a buyer id; shows which marketplaces are covered | transactions.customer_id | files | missing |

Rules every KPI follows (same spirit as the pulse contract):
- **No data is never 0.** Each KPI has `status`: `ok`, `partial` (some days or marketplaces missing; value shown with the coverage) or `no_data` (value `null`, with the reason).
- Each KPI carries its `source`, its `definition` as text, the `prior` value and the `delta`, so the page prints them without deciding anything.
- KPI 15 can only cover ShopGoodwill today: the Upright report has `Channel Buyer` (kept hashed in `customer_id`), Cash Monkey has no buyer column.
- Open definitions for Goodwill: the unsold threshold (9), whether margin includes labor (3, 14), growth year over year or month over month (2). Each is one constant in `recon/kpi/`.

KPI file shape (sketch, to be fixed in the contract):
```json
{ "schema_version": 1, "period": {"type": "month", "start": "2026-09-01", "end": "2026-09-30", "label": "September 2026"},
  "coverage": {"days_expected": 30, "days_with_data": 30},
  "kpis": [
    {"id": "fin.revenue", "area": "Financial", "name": "Total e-commerce revenue", "value": 6850986, "unit": "cents",
     "prior": null, "delta": {"pct": null, "reason": "no_prior_period"}, "source": "files", "status": "ok",
     "definition": "Sales minus refunds, excluding shipping and tax."},
    {"id": "cat.top_revenue", "area": "Category + Customer", "name": "Top 10 categories by revenue", "unit": "cents",
     "rows": [{"label": "Books & Media", "value": 1234500, "share": 0.18}], "source": "mixed", "status": "ok"}
  ] }
```

## 6. Database (Victor; goes into `docs/contracts/store.md`)

**SQLite**, Python standard library, one file, no new dependency, nothing for Goodwill to buy or install. SQL kept plain so it moves to Azure SQL or Postgres later. The CSV and JSON files stay the contract between engine and pulse; the database is where they accumulate.

| Table | One row per | Key | Filled by |
|---|---|---|---|
| `transactions` | sale or refund (the columns of `transaction.md`) | `txn_id` | `store load` |
| `pulse_daily` | business date and marketplace: status, gross, refunds, revenue, fees, orders, customers, basis | `(business_date, marketplace)` | `store load` |
| `internal_daily` | business date, metric, dimension: value, `source` (`mock` or `api`) | `(business_date, metric, dimension)` | `internal_api pull` |
| `runs` | pipeline run: time, business date, files read, warning counts, result | `run_id` | `store load` |
| `kpi_values` | period and KPI: value, status, source, computed at (history for trends) | `(period_type, period_start, kpi_id, dimension)` | `recon.kpi` through a store function |
| views `v_weekly`, `v_monthly` | week or month and marketplace: sums and days with data | | defined in the schema |

Dani reads the database only through the tables and views named in the contract, never through Victor's Python. The schema file (`engine/store/schema.sql`) is enough for her to build a test database before the loader exists.

Contract changes this needs in `transaction.md` (Victor, small PR, non-breaking): a `units` column (Cash Monkey is one line per unit; Upright has an item count). Phase 3 adds `payout` rows and `shipping_cents`.

## 7. Assumptions (also added to `docs/ASSUMPTIONS.md`, section 2b)
- **All Goodwill internal data comes from an internal API**: inventory, listings, donation dates, labor hours and headcount, cost of goods, product categories, the BC chart of accounts. We have not seen such an API. We build a mock with synthetic values; every response says `"source": "mock"` and every number built on it is badged "Simulated internal data".
- The internal API reports the current state only, so the nightly run stores a snapshot. That is why backlog and headcount have history.
- "Imported automatically into Business Central" means **a file Business Central accepts** (General Journal lines and AR invoice lines as CSV, for "Edit in Excel" or a configuration package). No live posting: we have no sandbox (assumption 1.2, decision 006 point 7). Say "BC-ready import file" in the demo; a posting API call is a next step, not a claim.
- The PDF and the email are generated, not sent (no mail account), as in decision 006.

## 8. Tasks, step by step

### First, tonight or first thing Sunday (contracts; they unblock everyone)
| ID | Task | Owner | Size | Needs |
|---|---|---|---|---|
| C1 | Accept or change decision 007 (owners, SQLite, the 15 KPIs) | All | S | |
| C2 | `docs/contracts/kpi.md` + `examples/kpi.sample.month.json` (all 15, one `no_data`, one `partial`) | Dani | M | C1 |
| C3 | `docs/contracts/store.md` + `engine/store/schema.sql` | Victor | M | C1 |
| C4 | `docs/contracts/internal-api.md`: endpoints and fields for labor, headcount, listings, inventory, costs, categories | Victor | S | C1; Dani lists the fields the 15 KPIs need |
| C5 | Read C2 and say what the page needs that is missing | Orlando | S | C2 |

### Phase 2: Victor (database, internal API, exports)
| ID | Task | Size | Needs |
|---|---|---|---|
| V2.1 | `engine/store/`: connection helper, `init` from `schema.sql`, database path setting | S | C3 |
| V2.2 | `store load`: upsert transactions, pulse rows, warnings, run record; re-running a day changes nothing | M | V2.1 |
| V2.3 | Views `v_weekly`, `v_monthly`; `store status` | S | V2.1 |
| V2.4 | `store backfill`; load September (`clean_month`) and October 1-4; check month revenue against `expected.json` | M | V2.2 |
| V2.5 | `engine/internal_api/`: client interface and mock (move `reports/mock_api.py`, add headcount, inventory snapshot, donation-to-listing days, costs by category, 12 or more categories) | M | C4 |
| V2.6 | `internal_api pull`: store the day's snapshot in `internal_daily` | S | V2.5, V2.1 |
| V2.7 | `units` in the parsers and in `transaction.md` | S-M | C3 |
| V2.8 | `export kpi-csv`: long format from the KPI file (period, area, KPI, value, unit, source, status) | S | C2 |
| V2.9 | `export pdf`: print Orlando's scorecard page to PDF with headless Edge or Chrome (already on every Windows machine, no new dependency); if neither is found, say so and point to "Print, Save as PDF" | M | O2.4 |
| V2.10 | `export email`: `.eml` with the PDF attached, to and subject from settings (standard library) | S | V2.9 |
| V2.11 | Extend `run_nightly` with the new steps | S | V2.2, V2.6, D2.9 |
| V2.12 | A second sample month (August) so growth has a prior period; Orlando wrote `data/generate.py`, so agree with him | M | cut first |

### Phase 2: Dani (KPIs)
| ID | Task | Size | Needs |
|---|---|---|---|
| D2.1 | Scaffold `recon/kpi/`: KPI registry (id, area, name, unit, definition, function), CLI skeleton | S | C2 |
| D2.2 | Periods: day, ISO week, month; prior period; days expected against days with data; the partial rule | S | |
| D2.3 | Read access to the store per `store.md`; a fixture database built from `schema.sql` with hand-made rows | M | C3 |
| D2.4 | Financial: revenue, growth, net margin | M | D2.2, D2.3 |
| D2.5 | Productivity: listings created, revenue per labor hour, listings per employee | S | D2.3 |
| D2.6 | Inventory: donation to listing, backlog, unsold % | M | D2.3 |
| D2.7 | Sales: average selling price (with the per-order fallback), sell-through, sales per employee | S-M | D2.3 |
| D2.8 | Category + Customer: the two top 10 lists, repeat buyer rate with coverage | M | D2.3 |
| D2.9 | `python -m recon.kpi`: write the KPI file and `kpi_values`; exit 0 whenever a file is written | S | D2.4-D2.8 |
| D2.10 | Tests: every KPI against hand-computed values; `no_data` and `partial` cases; September total revenue equals `clean_month/expected.json` to the cent | M | D2.9, V2.4 |
| D2.11 | With Orlando: delete the math from `reports/kpi.py` once the page reads the KPI file | S | O2.5 |

### Phase 2: Orlando (frontend)
| ID | Task | Size | Needs |
|---|---|---|---|
| O2.1 | Scorecard page from the sample KPI file: 5 areas x 3 tiles, value, change against the prior period, source badge, "no data" and "partial" states, definitions | L | C2 |
| O2.2 | The two top 10 tables | S | O2.1 |
| O2.3 | Day / week / month switch and a period picker (static pages linked together, or query parameters if the app exists) | M | O2.1 |
| O2.4 | Print layout: one page, landscape, readable in grayscale, simulated badges kept | M | O2.1 |
| O2.5 | Point `reports.monthly` and `reports.weekly` at the KPI file; remove their own sums | M | D2.9 |
| O2.6 | Download links: KPI CSV, PDF, and in phase 3 the BC files | S | V2.8, V2.9 |
| O2.7 | Revenue trend over the month (daily bars from the monthly view) | M | cut early |
| O2.8 | Demo script for phases 2 and 3; check every simulated number is badged | S | |

### Phase 3: Business Central integration (separate task, **owners not assigned**)
To be split in three when phase 2 reaches checkpoint 1. The steps are grouped into three packages of similar size that meet only at contracts, so each can go to one person. Who takes which is decided then.

| ID | Task | Size | Needs |
|---|---|---|---|
| P3.0 | **Shared, first:** `docs/contracts/outputs.md` from Orlando's proposal (the three CSV layouts, sign rule, exception record), and the split itself | S | checkpoint 1 |
| | **Package A: inputs and rules** | | |
| A1 | Keep payout and transfer rows in the engine output (new `payout` type) | M | P3.0 |
| A2 | Parse `bank_activity_*.csv` | M | |
| A3 | `docs/contracts/rules.md` + the mapping file: source -> accounts, department, journal or invoice path. Config, not code. Account numbers are placeholders except FedEx 40356 / Dept 180 from the deck | M | P3.0 |
| | **Package B: reconciliation** | | |
| B1 | Match payouts to bank deposits: amount and date window, many-to-one, in transit | L | A1, A2 (rows from `expected.json` as a mock until then) |
| B2 | Exceptions: missing file, unmatched deposit, prior-month refund, unbalanced document; each with a reason | M | B1 |
| B3 | Tests for matching and exceptions against `messy_month/expected.json` -> `close` | M | B2 |
| | **Package C: Business Central output** | | |
| C1 | Journal builder: one balanced document per source per month and one per deposit | L | A3 |
| C2 | Balance check: refuse to write a document that does not sum to 0.00 | S | C1 |
| C3 | Write `general_journal_<month>.csv`, `ar_invoice_<month>.csv`, `control_totals_<month>.csv`; tests on the month totals | M | C2 |
| C4 | Close page: exceptions, journal preview, control totals, download links | M | C3, B2 |
| C5 | Written, not built: how the file gets into BC (Edit in Excel, configuration package, or the journal lines API) for the "next steps" slide | S | |

## 9. Order of work, checkpoints, cuts

```
C1 -> C2, C3, C4 (parallel) -> build against mocks:
        Victor  V2.1 -> V2.2 -> V2.4 -> V2.5 -> V2.6
        Dani    D2.1 -> D2.2 -> D2.3 -> D2.4 .. D2.8 (on the fixture database)
        Orlando O2.1 -> O2.2 -> O2.4 (on the sample KPI file)
   -> CHECKPOINT 1: September in the database -> recon.kpi -> scorecard page shows real numbers
   -> split phase 3 in three (P3.0); exports (V2.8-V2.10, O2.6) and tests (D2.10) finish alongside packages A, B, C
   -> CHECKPOINT 2: messy month -> BC files balanced; decide cuts
   -> record the demo, freeze at 15:00
```
Suggested clock for Sunday: contracts done by 08:30, checkpoint 1 at 11:00, checkpoint 2 at 13:30, recording from 14:00.

**Cut order** (first to go first): V2.12 August sample; O2.7 trend chart; V2.10 email file; O2.3 week view (keep day and month); V2.7 units (keep "per order"); AR invoice file (keep the General Journal); V2.9 PDF command (print from the browser instead).

**Never cut:** the database load with a re-run that changes nothing; the 15 KPIs with honest `no_data` and simulated labels; total revenue matching the answer key; a balanced General Journal file from the messy month with its exceptions; the disclosures.

## 10. Risks
- **Most of the scorecard is simulated.** Only 4 of the 15 KPIs come purely from the files (1, 2, 10, 15). The other 11 depend, fully or in part, on the mock internal API. The demo must say so; the value we show is the plumbing and the definitions, not Goodwill's numbers.
- **The database is on everyone's path.** The fixture database and the sample KPI file exist so Dani and Orlando never wait on Victor's loader.
- **Phase 3 has no owner until checkpoint 1.** If checkpoint 1 slips past 11:00, phase 3 shrinks to package C on the month totals (a balanced General Journal without bank matching) before anything else is cut from it.
- **Two KPI lists in the repo** until decision 007 is accepted and `kpi_catalog.md` is updated by Orlando.
- **Growth needs two periods.** Without August it reads "no prior period", which is correct and should stay that way rather than be faked.
