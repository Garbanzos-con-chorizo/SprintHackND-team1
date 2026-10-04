# Tasks by phase and person

A view of `docs/TASKS.md`, regrouped. Task IDs, owners and sizes are unchanged; `TASKS.md` stays the source of truth for descriptions. Owners: **V** = Victor (`engine/`), **D** = Dani (`recon/`, pulse calculation), **O** = Orlando (`data/`, `reports/`, `docs/pitch/`).

| Phase | Goal | Difficulty |
|---|---|---|
| **1. Nightly pulse** (done) | Each night: messy exports in, clean daily numbers out (revenue and customers by marketplace, enterprise totals) | Low |
| **2. Monthly dashboard** | Accumulate the clean days over a month and visualize the five pillars | Medium |
| **3. Month-end close** | Rules, bank reconciliation, exceptions and the Business Central journal file | High (the real problem) |
| **Cross-cutting** | Story, demo, submission, integration | |

## Phase 1: Nightly pulse
**Status, 2026-10-03: done.** The inbox goes through the engine and Dani's pulse to the page, CSV and email copy, and all 8 sample scenarios match their answer keys (24 of 24 marketplace-days). Left over: the Upright and Cash Monkey column names are still guesses, and a few definitions wait on Amanda. How it lines up with the deck is in `docs/PHASE1_ALIGNMENT.md`. Phase 2 and 3 are planned in `docs/PLAN_PHASE_2_3.md` (this file's phase 2 and 3 sections below are the original outline).

Contract first: **0.1** (`transaction.md`, Victor) and **P0** (`pulse.md`, Dani).

| Person | Tasks |
|---|---|
| **Victor** | 0.1 transaction schema (phase 1 scope), V1 scaffold, V2 parser base and source detection, **A1 acquisition** (added: `engine fetch` and an Upright API stub; reports arrive by email into the inbox, decisions 004 and 005; file drop stays the fallback), V3 parsers for **ShopGoodwill, eBay, Amazon**, V6 validation and cleaning, V9 pipeline runner (parse, clean, write output files; no rules step yet), P-V1 marketplace tagging, P-V2 customer identity, P-V3 day boundary, P-V4 source status, P-V5 dedupe |
| **Dani** | P0 pulse contract, D1 mock canonical input, P-D1 revenue calculator, P-D2 aggregation and totals, P-D3 day-over-day delta, P-D4 pulse JSON and `pulse --date` CLI, P-D5 tests |
| **Orlando** | 0.4 Amanda office hours (pulse questions 5-12 first), O1 sample exports for ShopGoodwill, Amazon, eBay (clean month), P-O1 pulse sample days, P-O2 HTML render, P-O3 summary line, P-O4 delivery, P-O5 pulse demo script, 0.5/0.6 shared setup |

Cut order inside the phase: P-O3, then P-O4, then P-D3. Never cut the missing-data state (P-V4, P-O2) or the stated definitions.

## Phase 2: Monthly dashboard
**Status, 2026-10-04: done** (plan: `docs/PLAN_PHASE_2_3.md`, decisions `007` and `008`). The original outline below this status (a thin O5 page over `out/transactions.csv`) was replaced by a larger plan: a SQLite store, Dani's KPI calculator and Goodwill's own 15-KPI scorecard. What exists, all on `main`:

| Piece | Where | Owner |
|---|---|---|
| Nightly store (SQLite), `init`, `load`, `status`, `backfill` | `engine/store/` (`docs/contracts/store.md`) | Victor |
| Mock internal API (labor, listings, cost, categories, stock), labelled simulated | `engine/internal_api/` (`internal-api.md`) | Victor |
| 15 KPIs for a day, week or month, in five areas and five pillars | `recon/kpi/` (`kpi.md`) | Dani |
| Scorecard page: pillar tags, sell-through as two boxes, partial and no-data states, simulated badges | `reports/scorecard.py` | Victor and Orlando |
| Day, week-to-date and month-to-date pages every night, weekly and monthly pages, portal with a period switch | `reports/run_nightly.py`, `weekly.py`, `monthly.py`, `hub.py` | Victor and Orlando |
| KPI table as CSV and a one-page PDF, linked from the pages and the emails | `engine/export/` | Victor |
| A thin server for the pages and a Dockerfile | `server.py`, `Dockerfile` (`008`) | Victor |

Simulated, not real: the internal data (cost, labor, listings, stock) comes from a mock; August (the month September is compared with) is simulated, so September's growth (about -33%) is an artefact of two synthetic sources (`ASSUMPTIONS.md` 2b.5). Left: the demo script for phases 2 and 3 and an updated `docs/pitch/kpi_catalog.md` (L7, `docs/members/victor.md`).

Original outline, kept for the record:

| Person | Tasks |
|---|---|
| **Victor** | none assigned in `TASKS.md`; the plan above gave him the store, the mock internal API and the exports |
| **Dani** | none assigned in `TASKS.md`; the plan gave her the KPI calculator (`recon/kpi/`) |
| **Orlando** | O5 monthly dashboard, which became the scorecard pages |

## Phase 3: Month-end close
**Status, 2026-10-04 01:45 EDT:** one command, `python -m reports.close --inbox <folder> --month 2026-09`, runs the close on a synthetic tidy month and a synthetic messy month. It writes the General Journal (56 lines in 25 documents, each balanced), an AR invoice file, control totals and an exceptions list with an owner for each, archives the run, and renders the page. Every payout is compared with the files for the days it covers, so nothing is netted: the messy month names the two missing reports and their amounts ($743.10, $1,875.64) and holds out the $412.37 deposit; dropping in the two late reports closes the gaps. **Import files, not a live posting; three of Goodwill's nine month-end sources reach the close from sample files, the rest are not modeled until their simulated sources land.** Plan, tasks and what is left: `docs/PLAN_PHASE_3.md` (decision 009). Who has done what: `docs/members/dani.md`, `docs/members/victor.md`. The task table below is the original outline.

Contracts first: **0.2** (`rules.md`, Victor) and **0.3** (`outputs.md`, Dani).

| Person | Tasks |
|---|---|
| **Victor** | 0.2 rule format, V4 parsers for Cash Monkey, Upright, Books, V5 parser for bank activity, V7 rules engine, V8 fee splitting and refund handling, V9 (add the rules step), V10 unit tests, V11 hot-reload rule edit |
| **Dani** | 0.3 outputs contract, D2 payout-to-bank matching, D3 tolerance and many-to-one, D4 exceptions queue, D5 exception resolution, D6 journal builder, D7 balance check, D8 BC journal export, D9 tests, D10 review view |
| **Orlando** | O2 messy month (duplicates, refund, missing file, unmatched deposit, malformed row), 0.4 BC questions 2-3 and 19-25 |

Do not cut: V7, D2, D6-D8. They are the proof of "automates the rules, not just the downloads".

## Cross-cutting
| Person | Tasks |
|---|---|
| **Orlando** | O6 demo script, O7 slides, O8 demo video, O9 submission, I4 dry run, I5 final record and submit |
| **All** | I1 swap mocks for real pipeline output, I2 messy month end to end, I3 feature freeze |

## Dependencies that cross phases
- Orlando's sample data (O1) unblocks Victor's parsers in every phase. Until it exists, Victor builds parsers against the contract with hand-made rows.
- Victor's phase 1 cleaning (V6, P-V5) is the same code the close depends on. Build it once.
- `V9` is touched in phases 1 and 3, so it stays one runner and grows a rules step later.
