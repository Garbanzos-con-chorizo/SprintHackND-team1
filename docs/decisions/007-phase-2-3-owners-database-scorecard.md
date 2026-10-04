# 007 — Phases 2 and 3: owners, a database for the nightly data, the 15-KPI scorecard

- **Date / author:** 2026-10-03, Dani
- **Status:** proposed (Victor and Orlando to accept or change)
- **Changes:** `006-web-app-scope-and-internal-api.md` on three points (database role, KPI groups, who builds what). Everything else in 006 stands.
- **Full plan:** `docs/PLAN_PHASE_2_3.md` (gap analysis, entry points, KPI definitions, tasks per person, cut order).

## Decisions
1. **Owners for phase 2.** Dani: the KPIs (`recon/kpi/`). Orlando: the frontend (`reports/`). Victor: the database and the rest of the plumbing, meaning the internal API mock and client, the nightly orchestration and the exports.
   Moves that follow: KPI math leaves `reports/kpi.py` for `recon/kpi/`; the mock internal API leaves `reports/mock_api.py` for `engine/internal_api/`; `reports/run_nightly.py` becomes Victor's.
   **Phase 3 (Business Central integration) is a separate task with no owner yet.** It is split between the three of us once phase 2 reaches its first checkpoint; the plan groups its steps into three packages for that. Until then the BC export (D2 to D8) is nobody's alone.
2. **A database holds what the nightly runs produce.** SQLite (Python standard library, one file, no new dependency): transactions, the daily pulse rows, the internal API snapshots, the run history and the KPI history, with weekly and monthly views. Decision 006 kept SQLite for app state only, and its evening update ("static first") deferred it together with the web app and Docker. **This record brings SQLite back, for the data only**, because the KPIs need a month of transactions and of internal snapshots in one place. The web app and Docker stay deferred, and the pages stay static HTML: they are generated from the KPI file, not served from the database. The CSV and JSON files remain the contract between engine and pulse. Postgres or Azure SQL stays the documented next step.
3. **The KPIs are Goodwill's own scorecard** (deck slide 35): five areas, three KPIs each: Financial, Productivity, Inventory, Sales, Category + Customer. This replaces the five groups of decision 006 and `docs/pitch/kpi_catalog.md`.
4. **Data flow:** engine -> pulse -> database -> `recon.kpi` -> one KPI file per period -> dashboard, PDF and CSV all render that same file. Contracts to write first: `kpi.md` (Dani), `store.md` and `internal-api.md` (Victor).
5. **Internal data comes from an assumed internal API** (already point 9 of decision 006; now also in `docs/ASSUMPTIONS.md` section 2b). The nightly run stores a snapshot of it, so the KPIs read only the database.
6. **Phase 2 exports:** KPI CSV, a one-page scorecard PDF printed from the HTML page with a browser already on the machine (no new dependency), and an `.eml` with the PDF attached. Generated, not sent.
7. **Phase 3 is the Business Central close** and its output is import files (General Journal, AR invoice, control totals), not a live posting, as locked in decision 006 point 7.

## Why
- The split puts each person on one kind of work and lets all three start at once against a contract and a mock.
- SQLite costs nothing to install and fits "tools they already pay for".
- Goodwill's own 15 KPIs are a better Partner Fit answer than a list we made up, and they give a fixed scope: 15, no more.

## Consequences
- Victor has the longest phase 2 list; the PDF command goes to Orlando if the first checkpoint slips.
- Phase 3 gets only the time phase 2 leaves, and nobody starts it before the split.
- 11 of the 15 KPIs depend on simulated internal data and must be badged as such.
- `docs/PHASES.md`, `docs/TASKS.md` and `docs/pitch/kpi_catalog.md` are out of date for phases 2 and 3 until their owners update them or point here.

## Response from Orlando (2026-10-03, 21:00): accept 1, 3, 5, 6; change 2 and the phase 3 deferral
- **Accept: the 15-KPI scorecard (point 3).** Goodwill's own slide 35 scorecard replaces the decision 006 groups. Condition: every KPI that depends on simulated internal data stays tagged "Simulated internal data" in the KPI file, on the page, in the CSV and in the PDF. The weekly and monthly pages become renderers of Dani's KPI file; `reports/kpi.py` loses its math once that file exists (D2.11).
- **Accept: ownership (point 1).** Victor takes the internal API mock, the nightly orchestration and the exports. Head start already on `main`: `reports/email_gen.py` (one `.eml` per active subscriber, X-Unsent, manifest), `reports/run_scheduled.py` (nightly / weekly on Mondays / monthly on the 1st, then emails), `reports/config/subscribers.csv`, and `reports/mock_api.py`. Move them to `engine/` when convenient.
- **Change: no SQLite (point 2).** With under 19 hours to the freeze, a new data layer is the riskiest item in the plan. We keep the flat files of decisions 004-006: `out/<run>/transactions.csv`, `out/pulse/<date>.json` (already the history: `run_nightly` files every night's pulse there), and the internal API snapshot as one JSON file per run (`out/internal/<date>.json`). The KPIs read a period's files directly. SQLite stays the documented next step with Postgres or Azure SQL.
- **Change: phase 3 starts now, in parallel (point 7 and section "Consequences").** The Business Central close is the partner's main pain point ("automates the rules, not just the downloads"), so it does not wait for checkpoint 1. Orlando starts the export side now (General Journal, AR invoice and control-totals CSVs with the balance check, account mapping as an editable CSV) in `reports/bc_export.py`, against a mock payload, then against `messy_month`. Matching and exceptions (D2-D5) stay open for whoever finishes phase 2 work first; the module can move when the team splits phase 3.

## Amendment from Orlando (2026-10-03, 21:30): SQLite accepted; phase 3 still not deferred
- **SQLite is accepted (point 2), replacing the "no SQLite" change above.** The nightly data store is SQLite as Dani proposed: transactions, daily pulse rows, internal API snapshots, run history and KPI history, owned by Victor (`engine/store/`). Reason: a single file database is sturdier for Goodwill IT than a folder of files, and it costs no install. The CSV and JSON files stay the contract between engine and pulse (point 2 as written); the database is loaded from them.
- **Phase 3 is still not deferred.** The Business Central export runs in parallel with the database work: `reports/bc_export.py` (General Journal, AR invoice, control totals, exceptions) already balances on a mock close and is being run on `messy_month`. The phase 3 split can still move it.
