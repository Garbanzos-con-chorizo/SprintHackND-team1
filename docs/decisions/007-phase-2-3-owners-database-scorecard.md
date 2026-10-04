# 007 — Phases 2 and 3: owners, a database for the nightly data, the 15-KPI scorecard

- **Date / author:** 2026-10-03, Dani
- **Status:** proposed (Victor and Orlando to accept or change)
- **Changes:** `006-web-app-scope-and-internal-api.md` on three points (database role, KPI groups, who builds what). Everything else in 006 stands.
- **Full plan:** `docs/PLAN_PHASE_2_3.md` (gap analysis, entry points, KPI definitions, tasks per person, cut order).

## Decisions
1. **Owners for phase 2.** Dani: the KPIs (`recon/kpi/`). Orlando: the frontend (`reports/`). Victor: the database and the rest of the plumbing, meaning the internal API mock and client, the nightly orchestration and the exports.
   Moves that follow: KPI math leaves `reports/kpi.py` for `recon/kpi/`; the mock internal API leaves `reports/mock_api.py` for `engine/internal_api/`; `reports/run_nightly.py` becomes Victor's.
   **Phase 3 (Business Central integration) is a separate task with no owner yet.** It is split between the three of us once phase 2 reaches its first checkpoint; the plan groups its steps into three packages for that. Until then the BC export (D2 to D8) is nobody's alone.
2. **A database holds what the nightly runs produce.** SQLite (Python standard library, one file, no new dependency): transactions, the daily pulse rows, the internal API snapshots, the run history and the KPI history, with weekly and monthly views. Decision 006 kept SQLite for app state only; this widens it, because the KPIs need a month of transactions and of internal snapshots in one place. The CSV and JSON files remain the contract between engine and pulse. Postgres or Azure SQL stays the documented next step.
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
