# Handoffs: who gives what to whom (phase 1, nightly pulse)

```
Victor (engine/)  ->  Dani (recon/ pulse calc)  ->  Orlando (reports/)  ->  reader / dashboard
 clean data files      pulse JSON files             rendered reports
```
Each arrow is a folder of files with a contract. Code against the contract and a mock, not the teammate's work in progress. Paths are relative to the repo root and are written by the producer, read-only for the consumer.

## 1. Victor gives Dani
Contract: `docs/contracts/transaction.md` (Victor owns). Mock: `docs/contracts/examples/transactions.sample.csv`.

| File | What it is | Dani uses it for |
|---|---|---|
| `out/transactions.csv` | Clean sale and refund rows: marketplace, business date, order id, customer id and basis, gross and fee in cents. Deduped, bad rows removed. | Revenue, orders, customer counts (P-D1, P-D2) |
| `out/source_status.json` | Per source for the pulse day: `ok`, `missing` or `stale`, with files and row counts. | Showing "no data" instead of $0, excluding missing sources from totals (P-D2) |
| `out/warnings.json` | Duplicates dropped, bad dates, bad amounts, rejected files. | Optional data-quality count carried into the pulse JSON |

Victor also provides `python -m engine run`, which regenerates all three from `inbox/`, and `python -m engine fetch`, which first downloads the portal reports into `inbox/` (writing `out/fetch_log.json`). Files reach `inbox/` either from a scraper or by hand; the parsers don't care which.

## 2. Dani gives Orlando
Contract: `docs/contracts/pulse.md` (Dani owns; agreed and in use). Mocks: `docs/contracts/examples/pulse.sample.json` and `pulse.sample.missing.json`. The shape below is the summary; `pulse.md` is the source of truth:

| File | What it is | Orlando uses it for |
|---|---|---|
| `out/pulse/<YYYY-MM-DD>.json` | One file per day. Per marketplace `{revenue_cents, refunds_cents, fees_cents, orders, customers, customer_basis, status}`, enterprise totals, delta vs prior day, `data_quality` counts (from `warnings.json`), and the definitions used. Money in cents. | The HTML page, summary line, delivery (P-O2, P-O3, P-O4) |
| `out/pulse/latest.json` | Copy of the most recent day, so renderers don't have to find it. | Convenience |

Dani provides `python -m recon.pulse --date YYYY-MM-DD --in-dir out`. The status in the file is keyed by marketplace (`ok`, `stale`, `missing`, plus `not_configured` for `other`), and a marketplace without data has `null` numbers, never `0`.

## 3. Orlando gives the reader, and later the dashboard
Orlando does not calculate anything. He turns the pulse JSON into things people open.

| File | What it is | Who uses it |
|---|---|---|
| `reports/pulse/<YYYY-MM-DD>.html` | The nightly pulse page: four marketplace rows, enterprise total, delta, "no data" state, definitions footnote (P-O2) | Amanda's team, the demo |
| `reports/pulse/<YYYY-MM-DD>.csv` and `.email.html` | A CSV for Excel and an email-ready copy of the page; the page has print CSS for a PDF (P-O4) | Delivery stand-in for the nightly scheduler (`python -m reports.run_nightly`) |
| `reports/pulse/index.html` | Latest report plus links to prior days | The demo, and the phase 2 dashboard entry point |
| `data/sample/<scenario>/inbox/*` | Synthetic exports: clean day, day with a refund, day with eBay missing, day with duplicate rows (P-O1) | Victor's parsers and tests, Dani's tests, the demo |

**Toward the dashboard (phase 2):** the weekly and monthly pages read the daily `out/pulse/<date>.json` files. The metrics that need company data we don't have (cost of goods, labor, inventory) come from a clearly labelled mock internal API (decision 006). Phase 2 now also adds a database and KPI files; see `docs/PLAN_PHASE_2_3.md`.

## Order of work (done)
The three hand-offs above were built against mocks, then swapped for real output (integration I1 and I2). On 2026-10-03 the full chain ran on every sample scenario and matched the answer keys. This section is kept for the record.

## Ownership of generated folders
`out/` is written by the engine (Victor) and the pulse command (Dani). It is generated output, so it should be gitignored; that is a shared-file change, to be claimed in `docs/CLAIMS.md` when someone adds it. `reports/` is Orlando's. Nobody edits a file under another person's folder.
