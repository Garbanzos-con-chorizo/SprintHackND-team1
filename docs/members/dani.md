# Status — Dani (reconciliation and pulse calculation, `recon/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 16:20 EDT · **Branch:** d/pulse-scaffold (stacked on claude/phase-1-data-processing-plan-fd1a0c, the contract PR)

## Done
- P0 pulse contract (draft): `docs/contracts/pulse.md`, mocks `docs/contracts/examples/pulse.sample.json` (clean day) and `pulse.sample.missing.json` (eBay missing)
- D1 scaffold: `recon/pulse/` (`io` loaders work, `cli`, `calc`) and five fixture scenarios in `recon/tests/fixtures/` (see its README)
- P-D1 and P-D2 in `recon/pulse/calc.py`: gross, refunds, revenue, fees, orders, customers with basis, marketplace status, enterprise totals with `included`/`excluded`, `data_quality`, `definitions`. Matches `pulse.sample.json` except for `delta`.

## In progress
- P-D4 file output (not started)

## Blocked / needs from others
- Orlando: read `pulse.md` and say if the renderer needs anything else (task 0.6); P-O1 sample days for my tests (P-D5). Until then I use hand-made fixtures.
- Victor: `out/` is ignored by your `out/.gitignore` on `victor/phase1-contracts`, not merged yet. I write `out/pulse/` there and add no ignore rule of my own.
- Victor: I accept decision 002 (Python). The pulse uses the standard library only, tests with `unittest`, so it adds no dependency.

## Next (phase 1, in order)
1. P-D4 write `out/pulse/<date>.json` and `latest.json`
2. P-D3 delta (first to cut); until then the output has no `delta` objects, so it is not fully to contract
3. P-D5: the five scenarios are already tested on my fixtures; re-run on Orlando's P-O1 sample days

## How to run / test my part
- Tests: `python -m unittest discover -s recon -t .` from the repo root (18 pass).
- `python -m recon.pulse --in-dir recon/tests/fixtures/clean_day` prints the pulse JSON to stdout. No pulse file is written yet (P-D4).
- On my machine Python 3.13 is only on the `py` launcher, so `py -m ...`.

## Requests to me (append only: `- [from X, time] request`)
