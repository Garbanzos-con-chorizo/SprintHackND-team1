# Tasks by phase and person

A view of `docs/TASKS.md`, regrouped. Task IDs, owners and sizes are unchanged; `TASKS.md` stays the source of truth for descriptions. Owners: **V** = Victor (`engine/`), **D** = Dani (`recon/`, pulse calculation), **O** = Orlando (`data/`, `reports/`, `docs/pitch/`).

| Phase | Goal | Difficulty |
|---|---|---|
| **1. Nightly pulse** | Each night: messy exports in, clean daily numbers out (revenue and customers by marketplace, enterprise totals) | Low |
| **2. Monthly dashboard** | Accumulate the clean days over a month and visualize the five pillars | Medium |
| **3. Month-end close** | Rules, bank reconciliation, exceptions and the Business Central journal file | High (the real problem) |
| **Cross-cutting** | Story, demo, submission, integration | |

## Phase 1: Nightly pulse
Contract first: **0.1** (`transaction.md`, Victor) and **P0** (`pulse.md`, Dani).

| Person | Tasks |
|---|---|
| **Victor** | 0.1 transaction schema (phase 1 scope), V1 scaffold, V2 parser base and source detection, **A1 portal acquisition** (added: `engine fetch` plus one scraper per portal, HTTP or browser, per decision 003; file drop stays the fallback), V3 parsers for **ShopGoodwill, eBay, Amazon**, V6 validation and cleaning, V9 pipeline runner (parse, clean, write output files; no rules step yet), P-V1 marketplace tagging, P-V2 customer identity, P-V3 day boundary, P-V4 source status, P-V5 dedupe |
| **Dani** | P0 pulse contract, D1 mock canonical input, P-D1 revenue calculator, P-D2 aggregation and totals, P-D3 day-over-day delta, P-D4 pulse JSON and `pulse --date` CLI, P-D5 tests |
| **Orlando** | 0.4 Amanda office hours (pulse questions 5-12 first), O1 sample exports for ShopGoodwill, Amazon, eBay (clean month), P-O1 pulse sample days, P-O2 HTML render, P-O3 summary line, P-O4 delivery, P-O5 pulse demo script, 0.5/0.6 shared setup |

Cut order inside the phase: P-O3, then P-O4, then P-D3. Never cut the missing-data state (P-V4, P-O2) or the stated definitions.

## Phase 2: Monthly dashboard
Starts after the phase 1 output files are stable. The dashboard reads the same `out/transactions.csv`, now covering the whole month.

| Person | Tasks |
|---|---|
| **Victor** | none assigned in `TASKS.md`. **Gap:** nothing yet for monthly accumulation (month filter, month-over-month window, optional COGS/labor/inventory loaders). Needs the answers to questions 13-16 in `OFFICE_HOURS.md`. Propose before building. |
| **Dani** | none assigned. **Gap:** monthly metric calculations (growth, profitability, productivity, inventory, engagement) have no owner. Proposed: Dani, reusing P-D1 and P-D2. |
| **Orlando** | O5 monthly dashboard (thin; show only metrics we have data for) |

Cut order: O5 is the first thing cut from the whole project.

## Phase 3: Month-end close
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
