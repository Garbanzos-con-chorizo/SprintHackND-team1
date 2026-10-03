# Status — Dani (reconciliation and pulse calculation, `recon/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 17:10 EDT · **Branch:** d/goodwill-context

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
- Nothing. PR #9 and PR #10 are merged.

## For teammates: what the new context file changes
- **Orlando (P-O2):** Goodwill's own nightly table (slide 31) labels the rows SHOPGOODWILL, AMAZON, EBAY, OTHER E-COMMERCE CHANNELS and TOTAL E-COMMERCE, with columns DAILY REVENUE and DAILY CUSTOMERS. Use their labels.
- **All:** the rubric constraint for Goodwill is "tools they already pay for". The building closes 9:00 PM Saturday; code freeze is 4:00 PM Sunday; demo is in Pod B, room 154.
- **All:** Amanda Baumer is listed for Saturday 3:00-5:00 PM only, and no Goodwill staff for Sunday. Open definitions (revenue, customers, day boundary, "other") may stay unanswered, so the report must state the definition it used. The pulse JSON already carries them in `definitions`.
- **Victor:** nothing here contradicts `docs/contracts/source-formats.md`; it agrees that staff count rows (orders) as customers. The pulse takes `customer_basis` from the engine's rows, so no pulse change is needed either way.

## Blocked / needs from others
- Orlando: read `pulse.md` and say if the renderer needs anything else (task 0.6); P-O1 sample days for my tests (P-D5). Until then I use hand-made fixtures.
- Victor: I accept decision 002 (Python). The pulse uses the standard library only, tests with `unittest`, so it adds no dependency.
- Not run against real engine output yet; that is integration (I1). The engine landed on main in PR #8.

## Next (phase 1, in order)
1. I1: run the pulse on the engine's real `out/` and fix what differs
2. P-D5: the five scenarios are tested on my fixtures; re-run on Orlando's P-O1 sample days when they exist

## How to run / test my part
- Tests: `python -m unittest discover -s recon -t .` from the repo root (31 pass).
- `python -m recon.pulse --in-dir recon/tests/fixtures/clean_day --out-dir <some folder>` writes the pulse files for the fixture. Without `--out-dir` it writes to `<in-dir>/pulse`, so pass one when pointing at a fixture.
- On my machine Python 3.13 is only on the `py` launcher, so `py -m ...`.

## Requests to me (append only: `- [from X, time] request`)
