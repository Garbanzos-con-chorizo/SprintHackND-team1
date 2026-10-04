# Goodwill Michiana reporting automation

**From manual reporting to management visibility.** (Goodwill's own words for the problem.)

Goodwill Industries of Michiana builds its e-commerce reports by hand: someone opens Upright and Cash Monkey every night, clicks through ten steps, counts rows in Excel and types the numbers into a spreadsheet. At month end the work grows to nine sources, a rules workbook and manual Business Central entries. We built the pipeline that does this from the reports Goodwill already receives, and it **tells you when it is missing data instead of showing $0**.

Built at **SprintHack@ND, October 3-4 2026**, by three people with AI coding agents (Claude Code). The partner brief is the "Reporting" track; the problem in full is in [`docs/PROBLEM.md`](docs/PROBLEM.md).

> **Everything in this repo runs on synthetic data.** We have never seen a real Goodwill file or API. Nothing here is presented as real unless it says so; [what is real and what is simulated](#what-is-real-and-what-is-simulated) is below, and [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) lists every assumption, why we made it and how sure we are.

## What works today
| Part of the brief | Status | Try it |
|---|---|---|
| **Nightly pulse:** revenue and customers by marketplace (ShopGoodwill, Amazon, eBay, Other), then the e-commerce total | **Done**, runs end to end | [Nightly pulse](#1-the-nightly-pulse) |
| **Monthly dashboard:** the 15-KPI scorecard (growth, profitability, productivity, inventory, engagement) | **Runs** on a synthetic month, kept in a SQLite store night by night, with a **one-page PDF** and a **CSV for Excel / Power BI** attached to the monthly email draft. Some KPIs need company data we don't have and use a **mock internal API**, labelled "Simulated internal data" | [A month](#2-a-month-and-its-scorecard) |
| **Month-end close to Business Central:** bank deposits matched to marketplace payouts, an exceptions list, a balanced journal file | **Runs** on a synthetic messy month and writes Business Central **import files** (CSV), not a live posting. It reads only the engine's files and the bank file, never an answer key | [Month-end close](#3-month-end-close-to-business-central) |

## Quick start
Needs **Python 3.12 or newer**; the repo pins **3.13** (`.python-version`, and the Docker image). The engine alone also runs on 3.11, but the report pages and the PDF export need 3.12.
```bash
pip install -r engine/requirements.txt          # openpyxl, tzdata, pytest  (or: uv venv; uv pip install -r engine/requirements.txt)
python -m pytest engine recon reports -q        # every test, all three lanes
```
Everything below writes to `out/`, `inbox/` and `reports/` (generated, git-ignored).

### 1. The nightly pulse
```bash
python -m reports.run_nightly --scenario gw_day_clean            # a normal night
python -m reports.run_nightly --scenario gw_day_cashmonkey_missing   # a report never arrived
python -m reports.run_nightly --scenario gw_day_duplicates       # the same report saved twice
```
Each run checks the inbox, parses the reports, calculates, loads the night into the store (with the day's simulated internal data), updates the KPIs for the day, the week and the month to date, and writes a page (`reports/pulse/<date>.html`), an Excel-ready CSV and an email-ready copy. If the store or KPI step fails, the page is still written and the run says so. Add `--open` to open the page. `reports/index.html` links the pages. The scenarios are synthetic nights in `data/sample/`, each with an answer key the output is checked against.

The same thing, step by step:
```bash
python -m engine fetch --simulate --date 2026-10-02     # simulated provider emails land in inbox/
python -m engine run --date 2026-10-02                  # inbox/ -> out/ (clean rows, source status, warnings)
python -m recon.pulse --date 2026-10-02                 # out/ -> out/pulse/2026-10-02.json
```

### 2. A month and its scorecard
```bash
python -m engine.store backfill --inbox data/sample/clean_month/inbox --from 2026-09-01 --to 2026-09-30
python -m recon.kpi --month 2026-09                     # the 15 KPIs -> out/kpi/month-2026-09.json
python -m reports.monthly --month 2026-09               # the scorecard page -> reports/scorecard/month-2026-09.html
python -m engine.export kpi-csv --kpi-file out/kpi/month-2026-09.json   # the same KPIs as one CSV for Excel / Power BI
python -m engine.export pdf --kpi-file out/kpi/month-2026-09.json       # the page as a one-page PDF
python -m engine.store status                           # which days are in the store, per marketplace
```
About 15 seconds. On the sample month, 13 KPIs are complete, 1 is partial and 1 has no data, and the page says which. Revenue matches the sample's answer key to the cent ($70,753.96). The page, the CSV and the PDF render the same KPI file, so they can't disagree. Both land next to the page in `reports/scorecard/`. (`--period month` instead of `--kpi-file` takes the newest month computed, which after a nightly run is the current month to date.) The PDF is printed by a browser already on the machine (Edge, Chrome or Chromium; `PDF_BROWSER` points to another one); without one, open the page and use Print, Save as PDF, as it's laid out for one landscape page. `python -m reports.run_scheduled --from 2026-09-30 --to 2026-10-04` plays five nights as the scheduler would, including the month end: scorecard, CSV, PDF, close and the email drafts in `out/outbox/`.

### 3. Month-end close to Business Central
```bash
python -m reports.reconcile --inbox data/sample/messy_month/inbox --month 2026-09
python -m reports.bc_export --payload out/close/2026-09/close_payload_2026-09.json
python -m reports.close_report --month 2026-09
```
The messy September has missing and duplicated files, malformed rows, refunds from the prior month, payouts, and a bank file with one deposit covering several payouts and one deposit that matches nothing. The output (`out/close/2026-09/`) is a General Journal (56 lines, every document sums to 0.00), an AR invoice file, control totals and an **exceptions list**. Not everything reconciles, on purpose: the page shows what is open, what is explained and what is still unexplained.

### 4. See the pages in a browser
```bash
pip install -r requirements-server.txt          # fastapi, uvicorn (only for this step)
python server.py                                # then open http://127.0.0.1:8000/
```
A thin server that only serves `reports/`; it computes nothing, has no login and listens on localhost. Only pages, data files, CSVs and PDFs are served, never the code or `reports/config/`. Or as one image: `docker build -t goodwill-reports .` then `docker run --rm -p 127.0.0.1:8000:8000 goodwill-reports` (about 40 s to build; the image builds its pages from the synthetic samples and has no browser, so it has no PDF; see [`docs/decisions/008-static-server-for-docker.md`](docs/decisions/008-static-server-for-docker.md)).

## How it works
```
provider API (assumed, simulated)  ->  emailed .xlsx  ->  inbox/        <- or a person drops a file here
                                                              |
                                                     engine: parse, clean, de-duplicate
                                                              |
        out/transactions.csv    out/source_status.json    out/warnings.json
                                                              |
        recon.pulse -> daily pulse -> page, CSV, email          engine.store (SQLite) -> recon.kpi -> scorecard
                                                              |
                          month-end: bank + payouts -> reconcile -> exceptions + Business Central CSVs
```
Files are the contract between the three parts (`docs/contracts/`), so each part can be tested and replaced alone.

**The messy cases it handles:** a report that never arrived, a report saved twice, overlapping downloads, refunds (counted on the day issued), malformed rows and dates, a blank line, another sales channel mixed into a file, timestamps in Pacific (Upright) or UTC (Cash Monkey) that must land on the right Eastern day, and one line per unit.

## What is real and what is simulated
| | Real, built this weekend | Simulated or assumed |
|---|---|---|
| **Input** | Readers for CSV and Excel; source detection; parsers; cleaning of money, dates and timezones; de-duplication across files; per-marketplace status | **All data is synthetic.** Upright's columns come from a screenshot in Goodwill's walkthrough; Cash Monkey's columns are guesses |
| **Providers** | The adapter structure; one class per provider | **The APIs.** Amanda (Goodwill) told us to assume an Upright API that emails the report; we have never seen it. The clients are stubs, and `--simulate` writes synthetic reports, marked `simulated` in the log |
| **Scheduling and email** | The nightly job and the email files (`.eml` drafts) | **No scheduler and no mailbox.** `run_nightly` runs once when called; no mail is sent |
| **KPIs** | The 15-KPI calculation, the store, the scorecard | **Company data (cost of goods, labor, listings, inventory) comes from a mock internal API**, badged on every page that uses it |
| **Month-end sources** | Readers for each source; a file picker per source on the close page | **The Controller downloads these reports by hand** (Debie, Goodwill's CEO, on Sunday: decision 012). Goodwill has no API for them. Four of them (FedEx ledger, carriers' bank feed, Goodwill Books, Jewelry) come from our simulators, which stand in for that download and for a possible later step. The data is synthetic |
| **Close** | Matching deposits to payouts, exceptions, balanced journal files | **Business Central is not connected.** The output is import files (CSV). Goodwill confirmed Business Central is cloud and accepts CSV uploads; today the Controller does a recurring entry (decision 012). The API requests of `engine.export bc-api` are a dry run: nobody has said Goodwill can use that route |
| **Checking** | Tests for every lane; answer keys computed **independently of the engine** | |

## Known gaps
- **No real file has been read.** The first thing to do with a real file is replace a few column names. Different teammates guessed different names for a few columns; the parsers accept both spellings as a hedge, not as proof.
- **Two open questions could change the numbers:** whether Cash Monkey's report covers only the Goodwill Books operation, and how staff count customers for it (rows or orders). See [`docs/PHASE1_ALIGNMENT.md`](docs/PHASE1_ALIGNMENT.md).
- **Brick and mortar is out of scope.** The total is the e-commerce total.
- **No login.** The server is for local use only (localhost, no authentication); in production it would sit behind Goodwill's own sign-in.
- **The run time is an assumption.** The nightly run is set just after midnight Eastern, when e-commerce reports finalize; the slides suggest staff pull the previous day's data the next day, around 1:20 PM.

## Where things are
| Folder | What | Owner |
|---|---|---|
| [`engine/`](engine/README.md) | Parsers, cleaning, the SQLite store, the internal-API mock, the provider simulators, the KPI exports (CSV, PDF) | Victor |
| [`recon/`](recon/README.md) | The pulse calculation and the 15 KPIs | Dani |
| `reports/` | The pages, CSV and email layouts, reconciliation, the Business Central export, the nightly run | Orlando |
| `data/` | Synthetic sample inboxes, each with an answer key | Orlando |
| `docs/` | Problem, plan, contracts, decisions, assumptions, pitch material | all |
| `server.py`, `Dockerfile` | A thin server for the pages, and the image that bundles them | Victor |

## Documentation
- [`docs/PROBLEM.md`](docs/PROBLEM.md): the brief, the rubric, the demo plan.
- [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md): what we assumed, why, and how sure we are.
- [`docs/PHASE1_ALIGNMENT.md`](docs/PHASE1_ALIGNMENT.md): the nightly pulse checked against Goodwill's own slides.
- [`docs/PLAN_PHASE_2_3.md`](docs/PLAN_PHASE_2_3.md) and [`docs/PHASES.md`](docs/PHASES.md): the plan and task status.
- [`docs/contracts/`](docs/contracts/): the file formats between the parts (transactions, pulse, KPIs, store, close).
- [`docs/decisions/`](docs/decisions/): every decision, one file each.
- [`docs/pitch/`](docs/pitch/): the demo script and the judging guide.
- [`CLAUDE.md`](CLAUDE.md): how the team and its AI agents work together.

## Sources and tools
Python and its standard library (including SQLite); [`openpyxl`](https://openpyxl.readthedocs.io) to read Excel; `tzdata` for timezones on Windows; `pytest` for tests; [FastAPI](https://fastapi.tiangolo.com) and Uvicorn for the optional page server only; the machine's own Edge or Chrome (headless) to print the PDF; Docker for the optional image. Built with AI coding agents (Claude Code); we wrote the design and can explain every part.
