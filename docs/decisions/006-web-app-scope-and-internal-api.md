# 006 — Web app, hosting, scope cuts and the internal API assumption

- **Date / author:** 2026-10-03, Orlando (from the team's lunch sync, "Notes on 03-10-26.pdf"; the PDF is not in the repo yet, add it under `docs/` if you have it)
- **Status:** proposed (Victor and Dani to accept or change)
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
