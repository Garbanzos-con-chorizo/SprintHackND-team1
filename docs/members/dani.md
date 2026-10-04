# Status — Dani (reconciliation and pulse calculation, `recon/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 20:55 EDT · **Branch:** d/kpi-contract

## Done
- P0 pulse contract (draft): `docs/contracts/pulse.md`, mocks `docs/contracts/examples/pulse.sample.json` (clean day) and `pulse.sample.missing.json` (eBay missing). Merged in PR #9.
- D1 scaffold: `recon/pulse/` (`io`, `calc`, `cli`) and five fixture scenarios in `recon/tests/fixtures/` (see its README)
- P-D1 and P-D2 in `recon/pulse/calc.py`: gross, refunds, revenue, fees, orders, customers with basis, marketplace status, enterprise totals with `included`/`excluded`, `data_quality`, `definitions`
- P-D3 delta per marketplace and enterprise, with the `reason` guards. Prior day comes from `out/pulse/<prior>.json` if present, else from the rows.
- P-D4 `python -m recon.pulse [--date YYYY-MM-DD] [--in-dir out] [--out-dir out/pulse]` writes `<date>.json` and `latest.json`
- The calculator reproduces both published mocks exactly from `transactions.sample.csv` (tested)
- Summary of the whole lane: `recon/README.md`

- Added `docs/goodwill-project-context.md` (deck, rubric and problem-sheet extraction) for the whole team, linked from `docs/PROBLEM.md`

## In progress
- **C2, KPI contract (draft v0.1, new contract, announced here):** `docs/contracts/kpi.md` with two example files, `docs/contracts/examples/kpi.sample.month.json` (September, complete) and `kpi.sample.month.partial.json` (October to date, eBay missing one day). 15 KPIs in Goodwill's five scorecard areas, always all 15, with `status` (`ok` / `partial` / `no_data`), `note`, `prior_value`, `delta`, `source`, `simulated`.
  - **Orlando:** build the scorecard page against the two example files; the "Mock for parallel work" section lists the states they cover. Tell me what the page needs that is missing.
  - **Victor:** the section "Inputs the KPIs need" is my request for `store.md` and `internal-api.md` (tables, and the ten internal metrics with their dimensions).
- Decision 007: the team agreed on **SQLite** (resolution appended to 007). The KPI contract names the three tables the calculator reads (`pulse_daily`, `transactions`, `internal_daily`) until Victor's `store.md` exists.
- No calculator code yet: `recon/kpi/` starts with D2.1.

## For teammates: what the new context file changes
- **Orlando (P-O2):** Goodwill's own nightly table (slide 31) labels the rows SHOPGOODWILL, AMAZON, EBAY, OTHER E-COMMERCE CHANNELS and TOTAL E-COMMERCE, with columns DAILY REVENUE and DAILY CUSTOMERS. Use their labels.
- **All:** the rubric constraint for Goodwill is "tools they already pay for". The building closes 9:00 PM Saturday; code freeze is 4:00 PM Sunday; demo is in Pod B, room 154.
- **All:** Amanda Baumer is listed for Saturday 3:00-5:00 PM only, and no Goodwill staff for Sunday. Open definitions (revenue, customers, day boundary, "other") may stay unanswered, so the report must state the definition it used. The pulse JSON already carries them in `definitions`.
- **Victor:** nothing here contradicts `docs/contracts/source-formats.md`; it agrees that staff count rows (orders) as customers. The pulse takes `customer_basis` from the engine's rows, so no pulse change is needed either way.

## Blocked / needs from others
- Orlando: read `pulse.md` and say if the renderer needs anything else (task 0.6); P-O1 sample days for my tests (P-D5). Until then I use hand-made fixtures.
- Victor: I accept decision 002 (Python). The pulse uses the standard library only, tests with `unittest`, so it adds no dependency.
- Not run against real engine output yet; that is integration (I1). The engine landed on main in PR #8.

## Next (phase 2, in order; task ids from `docs/PLAN_PHASE_2_3.md`)
1. ~~C2: KPI contract and sample files~~ drafted, waiting for Orlando's and Victor's comments
2. D2.1 to D2.3: `recon/kpi/` scaffold, periods, a fixture database built from Victor's `schema.sql` (hand-made until it exists)
3. D2.4 to D2.9: the 15 KPIs and `python -m recon.kpi`
4. D2.10: tests, including September revenue against `data/sample/clean_month/expected.json`
- Phase 1 leftovers (I1, P-D5) are done in practice: Victor and Orlando ran the pulse on the real engine output and all 8 sample scenarios match their answer keys.

## How to run / test my part
- Tests: `python -m unittest discover -s recon -t .` from the repo root (31 pass).
- `python -m recon.pulse --in-dir recon/tests/fixtures/clean_day --out-dir <some folder>` writes the pulse files for the fixture. Without `--out-dir` it writes to `<in-dir>/pulse`, so pass one when pointing at a fixture.
- On my machine Python 3.13 is only on the `py` launcher, so `py -m ...`.

## Requests to me (append only: `- [from X, time] request`)
- [from Orlando, 2026-10-03 18:45] **Business Central export module (D6-D8): proposed CSV schemas, yours to accept or change in `docs/contracts/outputs.md` (task 0.3).** Format: CSV, UTF-8, header row, columns in the same order as the BC page so staff can paste rows into the General Journal / Sales Invoice grid or use "Edit in Excel" (no new tools, per the partner constraint). Amounts in dollars with 2 decimals; BC sign convention: positive = debit, negative = credit; every Document No. sums to 0.00. Test data: `data/sample/messy_month/` (September; `expected.json` -> `close` has month totals, every payout, every bank deposit with the payouts it matches, and the planted exceptions). **All account numbers, customer numbers and the department code below are placeholders** except the pattern from the deck (FedEx: G/L 40356, Dept 180): the real mapping lives in the E-Commerce Allocation workbook's Journal Entry and Invoices tabs, which we have not seen.

  **1. `general_journal_<YYYY-MM>.csv`** (one balanced document per source per month, plus one per bank deposit):
  ```
  Posting Date,Document Type,Document No.,Account Type,Account No.,Description,Amount,Department Code
  09/30/2026,,ECOM-2609-EBAY,G/L Account,11310,eBay net receivable Sep 2026,16853.62,180
  09/30/2026,,ECOM-2609-EBAY,G/L Account,40120,eBay sales Sep 2026,-20052.32,180
  09/30/2026,,ECOM-2609-EBAY,G/L Account,40190,eBay refunds Sep 2026,94.97,180
  09/30/2026,,ECOM-2609-EBAY,G/L Account,61210,eBay marketplace fees Sep 2026,3103.73,180
  09/04/2026,Payment,BNK-0904-EBAY,Bank Account,OPERATING,EBAY PAYOUT 0901 deposit,469.47,180
  09/04/2026,Payment,BNK-0904-EBAY,G/L Account,11310,EBAY PAYOUT 0901 deposit,-469.47,180
  ```
  (The ECOM-2609-EBAY figures are the real messy-month eBay totals from the files: sales 20,052.32, refunds 94.97, fees 3,103.73.)

  **2. `ar_invoice_<YYYY-MM>.csv`** (sales invoice lines; header fields repeated on each line so it stays one flat CSV):
  ```
  Document No.,Customer No.,Posting Date,Type,No.,Description,Quantity,Unit Price,Amount,Department Code
  SI-ECOM-2609-SGW,C-SHOPGOODWILL,09/30/2026,G/L Account,40110,ShopGoodwill sales Sep 2026,1,39118.00,39118.00,180
  SI-ECOM-2609-SGW,C-SHOPGOODWILL,09/30/2026,G/L Account,40115,ShopGoodwill handling Sep 2026,1,3522.00,3522.00,180
  ```
  `Type` is `Item` or `G/L Account`; `Amount = Quantity x Unit Price`.

  **Rules to keep it safe:** (a) each source's revenue posts through exactly one path, journal or invoice, never both (the mapping table decides; which sources go on the invoice is a question for Amanda); (b) refuse to write a document that doesn't sum to 0.00 (D7) and list it as an exception instead; (c) write a `control_totals_<YYYY-MM>.csv` next to them (source, files read, revenue from files, posted amount, difference) so the close shows "source-to-BC totals" as the deck asks; (d) anything in `close.exceptions` (missing file, unmatched deposit, refund of a prior-month order) stays out of the journal until resolved.
- [from Orlando, 2026-10-03 20:30] **Phase 3 (D2-D8) is now the team's top priority**; phase 1 runs end to end on the real engine + your pulse. Everything you need is on `main`: the BC CSV schema proposal (my request above), and `data/sample/messy_month/` (September). Status of the inputs: `python -m engine run --inbox data/sample/messy_month/inbox --out out --date 2026-09-30` gives `transactions.csv` that matches the answer key for ShopGoodwill (Upright), eBay and Amazon to the cent, with the planted mess flagged (1 bad amount, 1 bad date, 248 duplicate rows). The bank file `bank_activity_2026-09.csv` is not parsed yet (Victor's V5): read it directly in `recon/` if you don't want to wait (columns `Posting Date, Description, Debit, Credit, Balance`, MM/DD/YYYY, amounts with thousands separators). Payout amounts are in the eBay `Payout` rows and Amazon `Transfer` rows of the same files. Answer key for your tests: `expected.json` -> `close` (payouts with `deposit_date` / `in_transit`, `bank_deposits` with the payouts each one matches, 4 many-to-one deposits, 1 unmatched deposit, `exceptions`). Suggested order: D2-D4 matching + exceptions, then D6-D8 journal + export with the balance check. Ping me for anything in the data.
- [from Orlando, 2026-10-03 21:00] **Decision 007: your 15-KPI scorecard is accepted** (my response is appended to 007): I'll turn the weekly and monthly pages into renderers of your KPI file; please keep a `source` field per KPI so the 11 simulated ones stay tagged. Two changes: **no SQLite** (flat files only, the KPIs read a period's `out/pulse/*.json`, `transactions.csv` and `out/internal/<date>.json`), and **phase 3 is not deferred**: I'm starting the Business Central export (General Journal, AR invoice, control totals, balance check; mapping as editable CSV) now in `reports/bc_export.py`. It takes a JSON payload (month totals per source, deposits matched to sources, exceptions), so your matching (D2-D4) can feed it later without changing the export; I'll post the payload shape in `docs/contracts/` once it's verified.
- [from Orlando, 2026-10-03 21:30] **SQLite accepted** (amendment appended to decision 007): your plan stands, Victor builds the store, your `recon/kpi/` reads it. Phase 3 still runs **now, in parallel**: the BC export (D6-D8) is in `reports/bc_export.py`, balanced on a mock close; next it runs on `messy_month` with open balances explained by the exceptions. Your matching (D2-D4) only needs to produce `docs/contracts/close-payload.md` to plug in.
- [from Victor, 2026-10-03 22:15] **Store and internal API contracts are ready; SQLite is agreed by all three** (Orlando's amendment and my response in 007). PR `victor/store-contract`: (1) `docs/contracts/store.md` + `engine/store/schema.sql`. Build your test database with `executescript(schema.sql)`; the snippet is under "Rules for readers". Read only the named tables and views, and write `kpi_values` as delete-then-insert per `(period_type, period_start)`. (2) `docs/contracts/internal-api.md` uses **your metric list from `kpi.md` unchanged** (`dimension = 'total'` for single values). One detail: `category_sales_cents` is scaled to the day's pulse revenue, so your top 10 plus the rest add up to revenue. (3) `units`: the column is in the store, NULL until V2.7, so code the "per order" fallback. Your merged `kpi.md` inputs match `schema.sql` and `internal-api.md` exactly. One ask: keep every database read in one module of `recon/kpi/` (the 10:00 tripwire in 007).
