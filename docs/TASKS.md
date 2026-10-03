# Tasks: Goodwill Michiana Reporting

Split across three people by lane. Sizes: **S** < 30 min, **M** 30-90 min, **L** 90+ min. "Needs" lists the tasks or contracts a task depends on; code against the contract and a mock, not the teammate's work in progress. See `docs/roadmap.md` for the reasoning.

| Person | Lane | Owns |
|--------|------|------|
| **Victor** | Core engine | `engine/`: canonical schema, parsers, rules engine, pipeline runner |
| **Dani** | Reconciliation and accounting output | `recon/`: bank matching, exceptions queue, Business Central journal export |
| **Orlando** | Data, reports and story | `data/`, `reports/`, `docs/pitch/`: sample data, nightly pulse, dashboard, Amanda liaison, demo and submission |

> Proposed assignment. Swap lanes freely, but then update the lanes table in `CLAUDE.md` through a claim in `docs/CLAIMS.md`.

## Phase 0: Kickoff (first hour, all three, in parallel)
| ID | Task | Owner | Size | Needs |
|----|------|-------|------|-------|
| 0.1 | Draft the **canonical transaction schema** contract in `docs/contracts/transaction.md`: id, source, date, type (sale, fee, refund, payout, bank), marketplace, gross, fee, net, customer id, memo, raw ref | Victor | M | none |
| 0.2 | Draft the **rule format** contract in `docs/contracts/rules.md`: match conditions, GL debit/credit lines, fee splits, priority | Victor | M | 0.1 |
| 0.3 | Draft the **exceptions and journal output** contract in `docs/contracts/outputs.md`: exception record shape, BC journal line columns | Dani | M | 0.1 |
| 0.4 | Go to Amanda's office hours (3-5 PM, room 109B) with the question list from the roadmap; write answers into `docs/decisions/001-partner-answers.md` | Orlando | M | none |
| 0.5 | Fill in the lanes table in `CLAUDE.md`, create `docs/members/<name>.md` status files, set run/test commands | All | S | none |
| 0.6 | All three agree the contracts (read, comment, lock) | All | S | 0.1-0.3 |

## Victor: core engine
| ID | Task | Size | Needs |
|----|------|------|-------|
| V1 | Project scaffold in `engine/` (language, test runner, run command) and add the commands to `CLAUDE.md` | S | 0.5 |
| V2 | Parser base interface plus source auto-detection from filename or header | M | 0.1 |
| V3 | Parsers for the marketplace exports: ShopGoodwill, eBay, Amazon | L | V2, O1 |
| V4 | Parsers for Cash Monkey, Upright, Books exports | L | V2, O1 |
| V5 | Parser for bank activity | M | V2, O1 |
| V6 | Validation and cleaning: dedupe, bad dates, missing columns, with a warning list instead of crashing | M | V3 |
| V7 | Rules engine: load YAML/JSON rules, match transactions by priority, emit GL lines | L | 0.2 |
| V8 | Fee-splitting and refund handling in the rules (eBay and Amazon fees, refunds reversing sales) | M | V7 |
| V9 | Pipeline runner (CLI): read `inbox/`, parse, clean, apply rules, write the canonical output file that the other lanes consume | M | V3, V7 |
| V10 | Unit tests for parsers and rules, including the messy dataset | M | V6, V8, O2 |
| V11 | Rule edit demo support: make rules hot-reloadable and print a clear before/after diff | S | V7 |

## Dani: reconciliation and accounting output
| ID | Task | Size | Needs |
|----|------|------|-------|
| D1 | Scaffold `recon/` and a mock canonical input file so work isn't blocked on Victor | S | 0.1 |
| D2 | Matching logic: marketplace payouts to bank deposits by amount and date window | L | D1 |
| D3 | Tolerance and many-to-one matching (one deposit covering several payouts, timing differences) | M | D2 |
| D4 | Exceptions queue: unmatched items, duplicates, unclassified transactions, each with a reason and suggested action | M | D2, 0.3 |
| D5 | Exception resolution: mark resolved with a note, re-run the match, keep an audit trail | M | D4 |
| D6 | Journal builder: GL lines from the rules output, grouped into balanced debit/credit entries per day or per source | L | 0.2, 0.3 |
| D7 | Balance check: refuse to export unbalanced journals, report the difference | S | D6 |
| D8 | Business Central journal import file export (CSV/Excel in the format confirmed with Amanda) | M | D6, 0.4 |
| D9 | Tests for matching and journal balancing, including the unmatched-deposit case | M | D3, D7 |
| D10 | Exceptions and journal review view (simple table UI or HTML report) for the demo | M | D5, D8 |

## Orlando: data, reports and story
| ID | Task | Size | Needs |
|----|------|------|-------|
| O1 | Build realistic **synthetic sample exports** for every source in a clean month (match any real samples from Amanda) | L | 0.4 |
| O2 | Build a **messy month**: duplicates, a refund, a missing file, an unmatched bank deposit, a malformed row | M | O1 |
| O3 | Nightly pulse report: revenue and customer count by marketplace (ShopGoodwill, Amazon, eBay, other) plus enterprise totals | L | 0.1, mock data |
| O4 | Nightly pulse delivery: HTML page and email-ready or PDF output | M | O3 |
| O5 | Monthly dashboard (thin): growth, profitability, productivity, inventory, customer engagement; show only metrics we have data for | L | O3 |
| O6 | Write the demo script and click-path; update the Demo section of `docs/PROBLEM.md` | M | 0.6 |
| O7 | Slides: open with Debie's words, 30-second pitch, what is real versus simulated | M | O6 |
| O8 | Record the demo video (clean month and messy month, one take each) | L | Phase 2 |
| O9 | Write the submission: built versus used, sources cited, repo link, Slides link shared "anyone with the link" | M | O7 |

## Phase 2: Integration (all three, after the build tasks)
| ID | Task | Owner | Size | Needs |
|----|------|-------|------|-------|
| I1 | Swap mocks for the real pipeline output: run Victor's engine into Dani's recon and Orlando's reports end to end on the clean month | All | M | V9, D8, O3 |
| I2 | Run the messy month end to end; fix what breaks | All | M | I1, O2 |
| I3 | **Feature freeze** (one hour before the demo); bug fixes only | All | S | I2 |
| I4 | Dry run of the full demo against the script; time it | Orlando | S | I3 |
| I5 | Final record, submit by **4:00 PM Sunday**, then confirm the link works logged out | Orlando | S | O8, O9 |

## Critical path
`0.1 -> 0.2 -> V7 -> V9 -> I1`, and in parallel `0.1 -> O1 -> V3/V4/V5`. Victor's engine unblocks everyone at integration, and Orlando's sample data unblocks Victor's parsers, so **O1 and the contracts go first**. Until then Victor writes parsers against the contract and Dani works from her mock.

## Cut order if time runs short
1. O5 monthly dashboard (cut to a single page, or drop)
2. O4 email/PDF delivery
3. V11 hot reload (show the rule edit with a restart instead)
4. D10 review UI (show the exceptions as a plain report)

Do not cut: the rules engine (V7), reconciliation (D2), the balanced BC journal (D6-D8), and the clean-plus-messy demo (O1-O2, O8). They're the proof of "automates the rules, not just the downloads".
