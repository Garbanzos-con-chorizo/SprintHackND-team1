# Status — Orlando (data, reports, story: `data/`, `reports/`, `docs/pitch/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 · **Branch:** o/phase1-data (merged to main)

## Done
- Real reconciliation (B1-B2): `python -m reports.reconcile --inbox data/sample/messy_month/inbox --month 2026-09` runs the engine, reads bank credits (classified by `Bank_Text` in `bc_mapping.csv`), eBay Payout and Amazon Transfer rows, matches deposits to payouts (5-day window, many-to-one), detects in-transit payouts, missing reports (file names), prior-month refunds and engine warnings, and writes the close payload. Matches the answer key on all 23 deposits, the 4 multi-payout ones and the unmatched $412.37. Stopgap: shipping/handling per source from the answer key until the engine outputs them (asked Victor).
- Messy-month close: `python -m reports.mock_recon --scenario messy_month` (payload from the answer key, stand-in for D2-D5) then `python -m reports.bc_export --payload out/close/2026-09/close_payload_2026-09.json`: 56 journal lines in 25 documents, all 0.00; ShopGoodwill, eBay and Amazon OPEN with every cent explained (unexplained 0.00); 15 exceptions with source, amount and effect.
- Phase 3 export started (decision 007 response): `python -m reports.bc_export [--payload close.json]` writes `out/close/<month>/` General Journal, AR invoice, control totals and exceptions CSVs from a close payload (`docs/contracts/close-payload.md`); account rules in `reports/config/bc_mapping.csv`. Refuses unbalanced documents, re-checks the written files. Mock September close: 30 lines / 12 documents all 0.00, three sources RECONCILED. Tests: `python -m pytest reports/tests` (7).
- Delivery: `reports/config/subscribers.csv` (sample roles, example.org), `python -m reports.email_gen` writes one `.eml` per active subscriber to `out/outbox/<run date>/` (opens in Outlook as unsent; no SMTP), `python -m reports.run_scheduled --from D1 --to D2` simulates the nightly job (pulse nightly, weekly on Mondays, monthly on the 1st, then emails). `run_nightly` files each pulse in `out/pulse/`.
- UI sweep: white background, 2px corners, greys tinted from the brand black, SIMULATED badge in black; no emojis or placeholder text.
- Demo on the real pipeline: `run_nightly` runs engine + recon.pulse by default (`--simulated` = stage fallback), each scenario in `out/<scenario>/`. Demo script uses Goodwill's formats (`gw_*`): real output matches the answer keys.
- Weekly dashboard (`reports/weekly.py`) and Monthly COO scorecard (`reports/monthly.py` -> `<month>-scorecard.html`, `-kpis.csv`): same five KPI groups from `reports/kpi.py`; internal data from `reports/mock_api.py`, badged "Simulated internal data".
- O2 messy month: `data/sample/messy_month/` (September: missing and duplicate files, overlapping download, malformed rows, prior-month refunds, payouts, bank file with a many-to-one deposit, an unmatched deposit and in-transit payouts) with a `close` answer key. Engine matches its eBay and Amazon month revenue exactly. Proposed BC CSV schemas (General Journal, AR invoice) in Dani's requests.
- Goodwill-format samples: `data/sample/gw_*` with Upright `paid_orders_*.xlsx` (Pacific, one row per order) and Cash Monkey `orders2023-*.xlsx` (UTC, one line per unit), answer keys, `run_nightly` recognizes them. Request for parsers + per-source timezone is in `docs/members/victor.md`.
- Integrated with main: renderer, mock and CSV follow Dani's `docs/contracts/pulse.md` v1 (renders both `pulse.sample*.json`). `run_nightly --real` runs `engine run` + `recon.pulse`; Victor's parsers read all sample inboxes and match `expected.json` to the cent for day_clean (SG, eBay, Amazon).
- O1 (first pass) + P-O1: synthetic exports for ShopGoodwill (.xlsx), eBay, Amazon in `data/sample/<scenario>/inbox/`, five scenarios (clean month, clean day, refund day, eBay missing, duplicates), each with an `expected.json` answer key. Format notes in `data/README.md`.
- P-O4: print CSS, `<date>.email.html` (inline-styled tables for Outlook), `python -m reports.run_nightly --scenario <day_*>` (logged end-to-end run; engine and pulse simulated until merged). P-O5: `docs/pitch/demo_script_pulse.md`.
- P-O3 summary line + Goodwill palette on the pulse page; pulse also writes `reports/pulse/<date>.csv` (shared layout with the monthly CSV, `reports/schema.py`).
- P-O2 (against a proposed schema): `python -m reports.pulse --date YYYY-MM-DD` renders `out/pulse/<date>.json` to `reports/pulse/<date>.html` + `index.html`. Four marketplace rows, enterprise total, day-over-day delta (like-for-like), "No data" for missing/stale sources, data-quality and definitions footnotes. Stdlib only.
- Proposed pulse JSON for Dani: `docs/pitch/gemini/pulse_proposal.md`. Mock builder `python -m reports.mock_pulse --scenario <day_*>` makes that JSON from a sample answer key.
- Phase 2 plumbing (O5, proof of concept): `python -m reports.monthly --month YYYY-MM` rolls daily pulse files into `reports/monthly/<month>.csv` (Excel/Power BI) and `.json`; `reports/monthly/index.html` loads the JSON with fetch() and renders a daily table, month totals and a chart placeholder. Serve with `python -m http.server 8000 -d reports/monthly`.
- Accepted decision 002 (engine in Python); my code is Python too.

## In progress
- 0.4 Amanda office hours (3-5 PM): real sample exports first, then pulse questions 5-12, then MUST 1-4.

## Blocked / needs from others
- Victor: Upright and Cash Monkey parsers and per-source timezone (request in his file); P-V4 (per-source status). Until then `run_nightly --real` shows every source as missing, so the demo uses the default simulated mode.
- Victor (contract question, `transaction.md`): Amazon's report has **one row per item**, so a 2-item order gives two `Order` rows with the same order id. `txn_id = amazon:<order>:sale` makes them collide and dedupe would drop real revenue. Suggest either summing item rows per order before dedupe, or adding the sku/line to `txn_id`. A real duplicate (identical line pasted twice) is in `day_duplicates`.
- Victor: refunds in the sample count on the day they are **issued** (`business_date` of a refund = refund date, not original order date). Please confirm in the contract.

## Next
1. Office hours; record answers in a new `docs/decisions/` file
2. Adjust sample column names to any real exports
3. I1: switch the demo to `run_nightly --real` once P-V4 lands
4. Re-run the demo script after I1

## How to run / test my part
```
pip install -r engine/requirements.txt
python data/generate.py
```
Pulse page from mock data:
```
python -m reports.mock_pulse --scenario day_ebay_missing
python -m reports.pulse --date 2026-10-03     # open reports/pulse/2026-10-03.html
```
Engine against a scenario: `python -m engine run --inbox data/sample/day_refund/inbox --date 2026-10-02`, then compare with `data/sample/day_refund/expected.json`.

## Requests to me (append only: `- [from X, time] request`)
- [from Dani, 2026-10-03 20:40] **Phases 2 and 3 plan: please accept or change `docs/decisions/007-phase-2-3-owners-database-scorecard.md`; the detail is in `docs/PLAN_PHASE_2_3.md`.** It proposes that you own the frontend: the scorecard page as Goodwill's own 5 areas x 3 KPIs (slide 35, replacing the five groups in `kpi_catalog.md`), the day / week / month switch, the one-page print layout the PDF is made from, and download links. Phase 3 (Business Central) is a separate task, not assigned to anyone: we split it in three once phase 2 reaches its first checkpoint. Two things leave `reports/` if you agree: the KPI math in `reports/kpi.py` moves to `recon/kpi/` (mine; your page renders `out/kpi/<period>.json` and does no arithmetic), and `reports/mock_api.py` plus `run_nightly.py` go to Victor. I will publish `docs/contracts/kpi.md` and a sample KPI file first so you can build the page against it; tell me what the page needs that is missing. The demo script, slides, video and submission stay with you, so say if the frontend list is too long.
- [from Victor, 2026-10-03 22:15] **Thanks for the SQLite amendment: decision 007 is agreed by all three** (my response is in 007). Your head start stays in `reports/` (`email_gen.py`, `run_scheduled.py`, `run_nightly.py`, `mock_api.py`). I'll extend those files where they are, and `mock_api.py` becomes a re-export of `engine/internal_api/` so your pages keep working. For the slides: `docs/contracts/store.md` has a section "For the pitch" (rubric points, four short demo moments, what not to claim). For the PDF (V2.9) I need your one-page print layout (O2.4). Your old "Blocked" items on me (Upright and Cash Monkey parsers, per-source timezone, P-V4) are done on `main`: all 8 sample scenarios match through the pulse.
