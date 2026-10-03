# Status — Orlando (data, reports, story: `data/`, `reports/`, `docs/pitch/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 · **Branch:** o/phase1-data (merged to main)

## Done
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
