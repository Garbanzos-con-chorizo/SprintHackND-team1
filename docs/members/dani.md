# Status — Dani (reconciliation and pulse calculation, `recon/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 16:35 EDT · **Branch:** d/pulse-scaffold (stacked on claude/phase-1-data-processing-plan-fd1a0c, the contract PR #9)

## Done
- P0 pulse contract (draft): `docs/contracts/pulse.md`, mocks `docs/contracts/examples/pulse.sample.json` (clean day) and `pulse.sample.missing.json` (eBay missing). PR #9, open.
- D1 scaffold: `recon/pulse/` (`io`, `calc`, `cli`) and five fixture scenarios in `recon/tests/fixtures/` (see its README)
- P-D1 and P-D2 in `recon/pulse/calc.py`: gross, refunds, revenue, fees, orders, customers with basis, marketplace status, enterprise totals with `included`/`excluded`, `data_quality`, `definitions`
- P-D3 delta per marketplace and enterprise, with the `reason` guards. Prior day comes from `out/pulse/<prior>.json` if present, else from the rows.
- P-D4 `python -m recon.pulse [--date YYYY-MM-DD] [--in-dir out] [--out-dir out/pulse]` writes `<date>.json` and `latest.json`
- The calculator reproduces both published mocks exactly from `transactions.sample.csv` (tested)

## In progress
- Nothing. The pulse command is complete on mock data.

## Blocked / needs from others
- Orlando: read `pulse.md` and say if the renderer needs anything else (task 0.6); P-O1 sample days for my tests (P-D5). Until then I use hand-made fixtures.
- Victor: `out/` is ignored by your `out/.gitignore` on `victor/phase1-contracts`, not merged yet. I write `out/pulse/` there and add no ignore rule of my own.
- Victor: I accept decision 002 (Python). The pulse uses the standard library only, tests with `unittest`, so it adds no dependency.
- Not run against real engine output yet; that is integration (I1).

## Next (phase 1, in order)
1. Open the PR for `d/pulse-scaffold` once PR #9 merges
2. P-D5: the five scenarios are tested on my fixtures; re-run on Orlando's P-O1 sample days when they exist
3. I1: run on Victor's real `out/`

## How to run / test my part
- Tests: `python -m unittest discover -s recon -t .` from the repo root (31 pass).
- `python -m recon.pulse --in-dir recon/tests/fixtures/clean_day --out-dir <some folder>` writes the pulse files for the fixture. Without `--out-dir` it writes to `<in-dir>/pulse`, so pass one when pointing at a fixture.
- On my machine Python 3.13 is only on the `py` launcher, so `py -m ...`.

## Requests to me (append only: `- [from X, time] request`)
