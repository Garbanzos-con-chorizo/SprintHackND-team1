# 006 — Web app, hosting, scope cuts and the internal API assumption

- **Date / author:** 2026-10-03, Orlando (from the team's lunch sync, "Notes on 03-10-26.pdf"; the PDF is not in the repo yet, add it under `docs/` if you have it)
- **Status:** **accepted with amendments** by Victor (2026-10-04); Dani's acceptance is not recorded yet. What is still true and what was overtaken is in the **Resolution** at the end.
- **Complements:** `005-api-email-delivery-and-run-schedule.md` (Victor): 005 covers how reports come **in** (API, emailed Excel) and when the run happens (once a day, just after midnight Eastern). This record covers the app around it and the pulse email going **out**.

## Decisions from the sync
1. **One web app** wraps what exists: pulse, monthly dashboard, close outputs, a data input page, an email page. Served by an ASGI server (Uvicorn), self-hosted.
2. **Dockerized**, so it can later run on AWS (ECS/App Runner) or Azure (Container Apps) without changes.
3. **No authentication.** Out of scope for the hackathon.
4. **No vendor management.** Adding or removing data providers is left to Goodwill IT; providers are config, not a UI.
5. **Data input page** shaped like the future API: the page posts to the same endpoint an API client would.
6. **Email generator and scheduler** for the nightly pulse.
7. **Business Central integration = CSV files** (General Journal lines, AR invoice lines), pasted or imported with "Edit in Excel". Locked.
8. **KPIs** in five groups: Financial; Listings & Production; Sales Effectiveness; Category Effectiveness; Customer & Marketplace. Catalog: `docs/pitch/kpi_catalog.md`.
9. **Internal API assumption:** any company data we don't have (cost of goods, labor hours, listings, inventory, categories, the BC chart of accounts) is assumed to come from a **hypothetical Goodwill internal API**. We build a mock of it with synthetic data.

## How we keep these honest (the rubric penalizes overclaiming)
- **Every number fed by the mock internal API is labelled** on screen ("simulated internal data") and in the submission's built-versus-used text. The mock lives in one place (`data/internal_api/`), returns JSON shaped like a real API, and its responses say `"source": "mock"`.
- **No auth means local only.** The container binds to localhost by default; the demo says "authentication is out of scope; in production it sits behind Goodwill's Microsoft 365 sign-in". We do not deploy it publicly.
- **Email:** we generate the email (HTML + `.eml` file) and show it; we do not send real mail without an SMTP account Goodwill provides. **Scheduler:** the run time from decision 005 (just after midnight Eastern) as a setting, plus the `run_nightly` job; in the container a simple in-process timer, in production Windows Task Scheduler or a cloud scheduler. Both stated as such.
- **Data input page:** uploads land in the same inbox the engine reads; the endpoint is the API contract. Real API clients (Upright, Cash Monkey, email) are not built.

## Database: evaluation
| Option | For | Against | Verdict |
|---|---|---|---|
| **Files only** (today: `inbox/`, `out/*.csv`, `out/pulse/*.json`) | Already works end to end; nothing to install; easy to audit; every lane's contract is files | No query layer; run history and schedules need somewhere to live | **Keep as the source of truth for the demo** |
| **SQLite** (Python standard library) | Zero install, one file, fits in the container; good for run history, schedules, uploaded-file log, KPI history | Single writer; not for many concurrent users | **Add only for app state** (runs, schedules, uploads) |
| **PostgreSQL** (Docker / AWS RDS / Azure Database) | Production-grade, what AWS/Azure would host | A second container, migrations, credentials: hours we don't have before Sunday 4 PM | **Next step after the hackathon**; SQL kept portable so it moves over |

Recommendation: files stay the contract between lanes; SQLite holds only app state; Postgres is the documented path to AWS/Azure.

## Architecture (target for Sunday)
```
browser ──> FastAPI app (Uvicorn, in Docker, localhost:8000)
              ├─ /               nightly pulse (reports/pulse.py output)
              ├─ /monthly        monthly dashboard + KPIs (reports/monthly)
              ├─ /close          BC General Journal + AR invoice CSV downloads, exceptions (recon/)
              ├─ /input          data input page  ─┐
              ├─ POST /api/ingest  <───────────────┘ same endpoint a future API client calls -> inbox/
              ├─ POST /api/run     runs engine -> recon.pulse -> reports (run_nightly)
              ├─ /email          generated pulse email (+ .eml download), schedule setting
              └─ /api/internal/* mock Goodwill internal API (COGS, labor, listings, inventory)
```
New dependencies (need this decision accepted, rule 10): `fastapi`, `uvicorn`, `python-multipart` (uploads). Templates stay standard library. Docker: one `Dockerfile` + `docker-compose.yml` at the root (shared files: claim in `docs/CLAIMS.md`).

## Proposed split
| Who | Tasks |
|---|---|
| **Victor** (`engine/`) | Finish what the app depends on first: Upright + Cash Monkey parsers with per-source timezone, P-V4 source status, V5 bank parser. Then `POST /api/ingest` behaviour (validate and file uploads into `inbox/`), reusing `victor/ingest-framework`. |
| **Dani** (`recon/`) | BC CSV export (D6-D8, schema proposal in her requests), reconciliation and exceptions on `messy_month` (D2-D4), KPI calculations for Financial and Sales Effectiveness (reuses the pulse calculator), `/close` data. |
| **Orlando** (`app/`, `data/`, `reports/`, `docs/pitch/`) | FastAPI app shell and pages, Dockerfile + compose, data input page, email generator + schedule setting, mock internal API with synthetic data, KPI catalog and the remaining KPI groups' display, demo script, slides, video, submission. |

New top-level directory: `app/` (Orlando). Root `Dockerfile`, `docker-compose.yml`, `requirements` for the app: claimed by Orlando.

## Cut order if Sunday gets tight (Working Evidence and Partner Fit carry the score; UI polish scores zero)
1. Scheduler UI (keep `run_nightly` + "would run nightly at 00:15 ET")
2. Category and Listings KPIs (keep Financial and Customer & Marketplace)
3. SQLite (files only)
4. Docker (run with `uvicorn` directly; Dockerfile stays as the deployment path)

Never cut: the pulse on the real engine output, the messy month through reconciliation, the balanced BC CSV files, the disclosures.

## Update (2026-10-03, evening): static first
The team chose to ship the suite as **static HTML generated by Python**, no web server, for the hackathon:
- Portal: `reports/index.html`, built by `python -m reports.hub` and rebuilt at the end of `run_nightly`, `reports.weekly` and `reports.monthly`. It links to the latest nightly pulse, weekly dashboard and monthly COO scorecard, with their CSVs and archives, and shows each one's headline.
- Every page opens from disk (`file://`) and can be emailed, printed or put on a SharePoint/OneDrive folder Goodwill already pays for.
- The FastAPI/Uvicorn app, Docker and SQLite above are **deferred**: they become the path to AWS/Azure after the hackathon, serving these same files. The data input page and email scheduler are not built; uploads go to the inbox folder and `run_nightly` stands in for the scheduler (decision 005).
- One exception remains: `reports/monthly/index.html` (daily table) loads its data with `fetch()`, which browsers block on `file://`. It says so and shows the one-line command to serve it. The monthly **scorecard** is static and is what the portal links to.

## Resolution (2026-10-04, Victor): where this stands today
**Accepted with amendments.** The body above stays as the record of what the sync proposed. Where it differs from what exists, **this section is the current truth**, and the later decisions win: `007` (owners, SQLite, the 15-KPI scorecard) and `008` (a thin server, Docker). Everything marked "today" below was run or checked on 2026-10-04 on `main`. Dani: please add your own acceptance line under this section.

| # | What 006 proposed | Today | Verdict |
|---|---|---|---|
| 1 | One web app: pulse, dashboard, close, a data-input page, an email page | **Not an app.** Generated static pages, plus a thin server that only serves them. The portal (`reports/index.html`) links the nightly pulse, the weekly dashboard, the monthly scorecard and the close page. There is no input page and no email page | Superseded by "static first" and 008 |
| 2 | Dockerized | The image `goodwill-reports` builds its own pages from the synthetic samples. A container from it is running and healthy; all 16 links on the portal return 200 | **Done** (008) |
| 3 | No authentication | The server listens on localhost only, and the file with people's email addresses is refused (404) | **Stands** |
| 4 | No vendor management | Providers are classes in `engine/scrapers/`, set up by environment variables, not a screen | **Stands** |
| 5 | A data-input page that posts to the API endpoint | **Not built.** A report gets into `inbox/` by hand, by an email rule, or (for the demo) from `engine fetch --simulate` | Deferred |
| 6 | An email generator and a scheduler | **Built as stand-ins.** `reports.email_gen` writes `.eml` drafts (they open as unsent mail) addressed to sample `example.org` subscribers; nothing is sent. `reports.run_scheduled` and `run_nightly` run once when called (the nightly pulse, the weekly dashboard on Mondays, the monthly on the 1st); in production Windows Task Scheduler or cron would call them | Built, **simulated** |
| 7 | Business Central integration = CSV files | **Done.** A General Journal (56 lines in 25 documents, each summing to 0.00), an AR invoice file, control totals and an exceptions list, from a synthetic messy month. Import files, not a live posting | **Done** |
| 8 | KPIs in five groups (`docs/pitch/kpi_catalog.md`) | **Replaced** by Goodwill's own 15-KPI scorecard from the deck's slide 35, five areas of three (`docs/contracts/kpi.md`). On the sample month, 13 are complete, 1 partial and 1 has no data. The catalog is out of date | Superseded by 007 |
| 9 | A hypothetical Goodwill internal API, mocked with synthetic data and labelled | **Done**, moved from `data/internal_api/` to `engine/internal_api/` (007). Every page that uses it says "Simulated internal data" | **Done** |

**Other parts of 006**
- **Database:** 006 said files, with SQLite only for app state. 007 agreed SQLite for the nightly store, and it is built (`engine/store/`). Postgres remains the path after the hackathon.
- **The architecture diagram** (`/input`, `POST /api/ingest`, `POST /api/run`, `/email`, `/api/internal/*`) was **not built**. The server's only routes are the static files and `/healthz`. The `app/` folder was never created.
- **Dependencies:** `fastapi` and `uvicorn` were accepted in 008 (`requirements-server.txt`); `python-multipart` is not needed.
- **The split of tasks** is replaced by 007.
- **The cut order, as it turned out:** the scheduler screen and the data-input page were cut; SQLite and Docker were kept; the category and listings KPIs were kept and show as simulated.

### What this means for the presentation
**Show, with the command that proves it:**
1. **The nightly pulse on three nights** (clean, a report missing, a report saved twice): `python -m reports.run_nightly --scenario gw_day_clean`, then `gw_day_cashmonkey_missing`, then `gw_day_duplicates`.
2. **The month's 15-KPI scorecard:** `python -m engine.store backfill ...`, `python -m recon.kpi --month 2026-09`, `python -m reports.monthly --month 2026-09`.
3. **The month-end close:** `python -m reports.reconcile`, `reports.bc_export`, `reports.close_report`; show the exceptions list, not only the balanced journal.
4. **The portal in a browser:** `python server.py`, or the Docker image.
5. **An email draft** opening in Outlook as unsent mail.

**Say out loud that these are simulated or assumed:** all the data is synthetic; the providers' APIs are assumed and their clients are stubs; the internal data (cost, labor, listings, inventory) comes from a mock; email is drafted, never sent; the scheduler is a stand-in; the Business Central files are import files, not a live posting; there is no login.

**Do not claim:** a web app with an upload page or API endpoints (the diagram above was not built); a real scheduler; a live Business Central integration; anything deployed or hosted anywhere; authentication; real Goodwill data.

Judging guide: `docs/pitch/engine_pitch.md`. The same facts for a first-time reader: `README.md`.
