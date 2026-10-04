# Status — Dani (pulse and scorecard KPIs, `recon/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 21:20 EDT · **Branch:** d/kpi-calc (stacked on d/kpi-contract-v02)

## Done
- P0 pulse contract (draft): `docs/contracts/pulse.md`, mocks `docs/contracts/examples/pulse.sample.json` (clean day) and `pulse.sample.missing.json` (eBay missing). Merged in PR #9.
- D1 scaffold: `recon/pulse/` (`io`, `calc`, `cli`) and five fixture scenarios in `recon/tests/fixtures/` (see its README)
- P-D1 and P-D2 in `recon/pulse/calc.py`: gross, refunds, revenue, fees, orders, customers with basis, marketplace status, enterprise totals with `included`/`excluded`, `data_quality`, `definitions`
- P-D3 delta per marketplace and enterprise, with the `reason` guards. Prior day comes from `out/pulse/<prior>.json` if present, else from the rows.
- P-D4 `python -m recon.pulse [--date YYYY-MM-DD] [--in-dir out] [--out-dir out/pulse]` writes `<date>.json` and `latest.json`
- The calculator reproduces both published mocks exactly from `transactions.sample.csv` (tested)
- Summary of the whole lane: `recon/README.md`

- Added `docs/goodwill-project-context.md` (deck, rubric and problem-sheet extraction) for the whole team, linked from `docs/PROBLEM.md`

## Done (phase 2)
- **C2** KPI contract `docs/contracts/kpi.md`: v0.1 merged (#15). **v0.2 (contract change, announced here):** the examples are now the calculator's own output, two more examples (`kpi.sample.week.json`, `kpi.sample.day.json`, asked by Orlando), inputs point to `store.md` and `internal-api.md`, each KPI carries slide 32's `pillar` (Victor's alignment note), the KPIs are also recorded in `kpi_values`, and several rules are spelled out (changelog in the file).
- **D2.1 to D2.9** `recon/kpi/`: the 15 KPIs for a day, an ISO week or a month, with status (`ok` / `partial` / `no_data`), note, prior value and change. `python -m recon.kpi --month 2026-09` (or `--week`, `--date`, or `--period month` alone for the period of the latest stored day) writes `out/kpi/<type>-<id>.json`, `latest-<type>.json` and `kpi_values`. Summary: `recon/kpi/README.md`.
- **D2.10** tests: 103 new (134 in `recon`). All 15 KPIs against hand-computed values; the command reproduces the four contract examples exactly; September revenue equals the `clean_month` answer key to the cent (7,075,396). The test databases are built from Victor's `engine/store/schema.sql`.
- Decision 007: resolution appended (SQLite agreed by all three).

## In progress
- Two PRs: `d/kpi-contract-v02` (contract v0.2 and the four examples, docs only) and `d/kpi-calc` (the calculator and its tests, stacked on it).

## Not verified yet (be careful what you claim)
- **`recon.kpi` ran on Victor's real loader only for two fixture days.** By hand: `recon/tests/fixtures/clean_day` -> `recon.pulse` -> `engine.store` `load_day` -> `recon.kpi --date 2026-10-02`: revenue 30,147, prior day 25,800, change 4,347, the pulse's own numbers; `kpi_values` and the `runs` line written; the `other` row (`not_configured`) ignored. **Not run:** the engine's real output for a whole month (its dependencies are not installed on this machine) and anything with internal data (`internal_api pull` does not exist yet, so the 11 internal KPIs have only ever seen my test rows). That is checkpoint 1.
- 11 of the 15 KPIs rest on simulated internal data; ASP and sell-through are per order until the transactions carry `units`.

## For teammates: what the new context file changes
- **Orlando (P-O2):** Goodwill's own nightly table (slide 31) labels the rows SHOPGOODWILL, AMAZON, EBAY, OTHER E-COMMERCE CHANNELS and TOTAL E-COMMERCE, with columns DAILY REVENUE and DAILY CUSTOMERS. Use their labels.
- **All:** the rubric constraint for Goodwill is "tools they already pay for". The building closes 9:00 PM Saturday; code freeze is 4:00 PM Sunday; demo is in Pod B, room 154.
- **All:** Amanda Baumer is listed for Saturday 3:00-5:00 PM only, and no Goodwill staff for Sunday. Open definitions (revenue, customers, day boundary, "other") may stay unanswered, so the report must state the definition it used. The pulse JSON already carries them in `definitions`.
- **Victor:** nothing here contradicts `docs/contracts/source-formats.md`; it agrees that staff count rows (orders) as customers. The pulse takes `customer_basis` from the engine's rows, so no pulse change is needed either way.

## Blocked / needs from others
- Nothing blocks me. For checkpoint 1 I need September in the store (Victor: V2.4 backfill, V2.6 internal pull).
- Orlando: tell me when the page reads `out/kpi/*.json`, then we delete the math in `reports/kpi.py` (D2.11).

## Next (task ids from `docs/PLAN_PHASE_2_3.md`)
1. Checkpoint 1: `python -m recon.kpi --month 2026-09` on the loaded store must read 7,075,396; fix whatever differs.
2. If the store is late (Victor's 10:00 tripwire in 007): one function in `recon/kpi/store.py` that builds the same `WindowData` from `out/pulse/*.json`. Not built.
3. D2.11 with Orlando.
4. Phase 3: Orlando already has the export and the reconciliation on `main` (`reports/bc_export.py`, `reports/reconcile.py`); ask at checkpoint 1 what is left to split.

## How to run / test my part
- Tests: `python -m unittest discover -s recon -t .` from the repo root (134 pass). On my machine Python 3.13 is only on the `py` launcher, so `py -m ...`.
- Pulse: `python -m recon.pulse --in-dir recon/tests/fixtures/clean_day --out-dir <some folder>`.
- KPIs without the real store: `python -m recon.tests.kpi_samples --db out/store/ecom.db` (synthetic September and October 1 to 4; refuses to overwrite an existing database), then `python -m recon.kpi --period month`, `--week 2026-W40`, `--date 2026-10-03`.
- Regenerate the contract examples after a deliberate change: `python -m recon.tests.kpi_samples`.

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
- [from Orlando, 2026-10-03 21:50] **C5 done: `kpi.md` (your `d/kpi-contract` branch) has everything the scorecard page needs; please merge it.** What the page will use, so nothing gets dropped: `period.label` / `prior_period.label` for titles and "vs ..."; `coverage.gaps` and `coverage.complete` for the red banner; per KPI `name`, `value` + `unit` + `per` for the number ("$45.74 per labor hour"), `status` + `note` for the partial / no-data line, `delta.value` / `delta.pct` / `delta.reason` + `good_direction` for the coloured change (ratio deltas shown as percentage points), `simulated` + `internal_data.label` for the badge, `definition` for the footnote, `rows` (`rank`, `label`, `value`, `share`, `ratio`) for the two top-10 tables. I ignore `inputs`. Four requests, none blocking:
  1. **Merge the contract and both examples to `main`** (docs only), so O2.1 builds against `main`.
  2. **One `day` and one `week` example** (can be small) for the period switch (O2.3), covering states the month files can't: `period_too_short` (KPI 15 on a day), `zero_denominator`, `missing_internal_days`.
  3. **The headline sentence:** the portal shows each page's `<p class="summary">`. I'll write it from KPIs 1 and 2 and `coverage` on the page side unless you'd rather ship a `summary` string in the file; tell me which.
  4. **Keep `simulated` true on the two rankings** (they split real revenue by internal shares), so the tables get the badge too. Your examples already do; just keep it in the calculator.
  Facts for your inputs, checked on `main` just now: one `python -m engine run --inbox data/sample/clean_month/inbox --out <dir> --date 2026-09-30` gives all of September in one `transactions.csv` (2,425 rows, Sep 1-30), usable for D2.10 before the store exists. On Goodwill's formats (`gw_*`), Upright rows keep `customer_id` (119 of 119) and Cash Monkey rows have none, so KPI 15 is `partial` / `no_buyer_ids` covering ShopGoodwill only, as your contract expects. There is no `units` column yet, so KPIs 10 and 11 stay on their per-order basis. SQLite is accepted now (amendment in 007), so your "Inputs" line stands as written.
- [from Victor, 2026-10-03 23:15] **KPI contract and KPI identification are yours; one gap to close.** `docs/contracts/kpi.md` follows slide 35 (five areas, 15 KPIs, stable ids), but slide 32 names five *pillars* (Growth, Profitability, Productivity, Inventory, Engagement) that appear nowhere in the contract. A proposed pillar-to-KPI mapping is in `docs/PHASE1_ALIGNMENT.md` (last section). Please decide: add a `pillar` field per KPI, or leave it to the page? Also note `sales.asp` and `sales.sell_through` need `units` in `transactions.csv` (not built yet), and `cust.repeat_buyer_rate` needs a buyer id (Upright has one, Cash Monkey none).
