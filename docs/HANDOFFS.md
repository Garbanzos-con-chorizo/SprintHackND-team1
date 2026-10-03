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

Victor also provides the command `engine run` (name set in V1) that regenerates all three from `inbox/`.

## 2. Dani gives Orlando
Contract: `docs/contracts/pulse.md` (**Dani owns, P0, not written yet**). Mock: Dani publishes `docs/contracts/examples/pulse.sample.json` with the contract. Proposed shape for Dani to confirm or change:

| File | What it is | Orlando uses it for |
|---|---|---|
| `out/pulse/<YYYY-MM-DD>.json` | One file per day. Per marketplace `{revenue_cents, refunds_cents, fees_cents, orders, customers, customer_basis, status}`, enterprise totals, delta vs prior day, `data_quality` counts (from `warnings.json`), and the definitions used. Money in cents. | The HTML page, summary line, delivery (P-O2, P-O3, P-O4) |
| `out/pulse/latest.json` | Copy of the most recent day, so renderers don't have to find it. | Convenience |

Dani provides the command `pulse --date YYYY-MM-DD` (P-D4).

## 3. Orlando gives the reader, and later the dashboard
Orlando does not calculate anything. He turns the pulse JSON into things people open.

| File | What it is | Who uses it |
|---|---|---|
| `reports/pulse/<YYYY-MM-DD>.html` | The nightly pulse page: four marketplace rows, enterprise total, delta, "no data" state, definitions footnote (P-O2) | Amanda's team, the demo |
| `reports/pulse/<YYYY-MM-DD>.pdf` or `.email.html` | Print or email-ready copy of the same page (P-O4, cut if time is short) | Delivery stand-in for the nightly scheduler |
| `reports/pulse/index.html` | Latest report plus links to prior days | The demo, and the phase 2 dashboard entry point |
| `data/sample/<scenario>/inbox/*` | Synthetic exports: clean day, day with a refund, day with eBay missing, day with duplicate rows (P-O1) | Victor's parsers and tests, Dani's tests, the demo |

**Toward the dashboard (phase 2):** the dashboard reads the whole month of `out/transactions.csv` and the daily `out/pulse/*.json` files already produced, so Orlando needs no new files from Victor or Dani for phase 1. The metrics that need extra data (COGS, labor, inventory) are not in these files and wait on Amanda's answers.

## Order of work
1. Today: Victor commits `transaction.md` (this PR). Dani writes `pulse.md` and its sample JSON. Orlando writes sample exports.
2. Until the engine exists: Dani builds on `transactions.sample.csv`, Orlando builds on Dani's `pulse.sample.json`.
3. Swap the mocks for real output at integration (I1).

## Ownership of generated folders
`out/` is written by the engine (Victor) and the pulse command (Dani). It is generated output, so it should be gitignored; that is a shared-file change, to be claimed in `docs/CLAIMS.md` when someone adds it. `reports/` is Orlando's. Nobody edits a file under another person's folder.
