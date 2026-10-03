# Status — Dani (reconciliation and pulse calculation, `recon/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 16:10 EDT · **Branch:** d/pulse-scaffold (stacked on claude/phase-1-data-processing-plan-fd1a0c, the contract PR)

## Done
- P0 pulse contract (draft): `docs/contracts/pulse.md`, mocks `docs/contracts/examples/pulse.sample.json` (clean day) and `pulse.sample.missing.json` (eBay missing)
- D1 scaffold: `recon/pulse/` (`io` loaders work, `cli` parses arguments and loads inputs, `calc.build_pulse` is a stub) and five fixture scenarios in `recon/tests/fixtures/` (see its README)

## In progress
- P-D1 revenue calculator (not started)

## Blocked / needs from others
- Orlando: read `pulse.md` and say if the renderer needs anything else (task 0.6); P-O1 sample days for my tests (P-D5). Until then I use hand-made fixtures.
- Victor: `out/` is ignored by your `out/.gitignore` on `victor/phase1-contracts`, not merged yet. I write `out/pulse/` there and add no ignore rule of my own.
- Victor: I accept decision 002 (Python). The pulse uses the standard library only, tests with `unittest`, so it adds no dependency.

## Next (phase 1, in order)
1. P-D1 revenue calculator, P-D2 aggregation and totals
2. P-D4 pulse JSON and CLI, end to end on the mock
3. P-D3 delta (first to cut)
4. P-D5 tests: clean day, refunds, missing source, duplicates, zero-revenue marketplace

## How to run / test my part
- Tests: `python -m unittest discover -s recon -t .` from the repo root (5 pass, loaders and fixtures only).
- `python -m recon.pulse --in-dir recon/tests/fixtures/clean_day` loads the inputs, then exits 2 because the calculation is still a stub. No pulse file is written yet.
- On my machine Python 3.13 is only on the `py` launcher, so `py -m ...`.

## Requests to me (append only: `- [from X, time] request`)
