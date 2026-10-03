# Status — Victor (core engine, `engine/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 · **Branch:** victor/phase1-contracts

## Done
- Phase split of all tasks: `docs/PHASES.md`
- Phase 1 transaction contract (draft): `docs/contracts/transaction.md`, mock `docs/contracts/examples/transactions.sample.csv`
- Handoff map: `docs/HANDOFFS.md` (PR #4)
- `out/.gitignore` so generated output is not committed (no root file touched)

- V1 scaffold in `engine/` (branch `victor/v1-scaffold`): `python -m engine run` writes valid empty `transactions.csv`, `source_status.json` (all sources `missing`) and `warnings.json`; 2 tests pass. No parsers yet.

- Portal acquisition skeleton (branch `victor/scraper-skeleton`, stacked on V2): `python -m engine fetch` runs one scraper per portal (HTTP or browser backend), saves reports to `inbox/`, logs to `out/fetch_log.json`. Upright is a skeleton only (no URLs/selectors known). Decision 003 proposed.

- V3 parsers (branch `victor/v3-parsers`, stacked on the scraper skeleton): ShopGoodwill, eBay, Amazon on a shared `OrderReportParser`; money/date cleaning in `engine/clean.py`; 56 tests pass. Checked against Orlando's synthetic samples (`data/sample/*`): 64 of 66 marketplace-days off at first, now all match except the overlapping eBay re-download, which needs P-V5. Column names are still not from real Goodwill files, and ShopGoodwill's layout is a guess on both sides. Not yet done: cross-file dedupe (P-V5), source status (P-V4), day cutoff config (P-V3 beyond timezone).

## In progress (claimed, so nobody doubles up)
- P-V5 cross-file dedupe, P-V4 real `source_status.json`, P-V3 day cutoff config, V9 runner summary (all `engine/`)
- Running `engine` against Orlando's `data/sample/*` and comparing with each `expected.json`
- 0.2 rules contract draft (`docs/contracts/rules.md`), after the items above
- Not mine: pulse calculation (Dani), sample data and HTML report (Orlando)

## Blocked / needs from others
- Dani: write `docs/contracts/pulse.md` (P0); confirm or change the pulse JSON shape proposed in `docs/HANDOFFS.md`
- Anyone who can log in to the portals: run the discovery step in `docs/decisions/003-portal-acquisition.md` (network tab: is the report one replayable request?), starting with Upright (deck slides 21-26) and Cash Monkey (27-30)
- Orlando: sample exports (O1, P-O1) so parsers match real column names; until then I code against hand-made rows
- Team: confirm `transaction.md` (task 0.6) and pick the engine language (V1)

## Next (phase 1, in order)
1. ~~V1 scaffold~~ done
2. ~~V2 parser base interface and source detection~~ done (branch `victor/v2-parsers`, stacked on V1). To add a source: one module in `engine/sources/`, see `engine/parsers.py` docstring
3. ~~V3 parsers: ShopGoodwill, eBay, Amazon~~ done on guessed columns; correct the aliases in `engine/sources/*.py` when real files arrive
4. V6 cleaning and warnings, P-V5 dedupe, P-V3 day boundary
5. P-V1 marketplace tagging, P-V2 customer identity
6. V9 runner and P-V4 source status
Phase 3 (V4, V5, V7, V8, V10, V11, rule contract 0.2) comes after the pulse works end to end.

## How to run / test my part
From the repo root, Python 3.11+:
```
pip install -r engine/requirements.txt
python -m engine run [--inbox inbox] [--out out] [--date YYYY-MM-DD]
python -m pytest engine -q
```
(These commands are not yet in `CLAUDE.md`, to avoid touching a shared file; add them when someone claims it.)

## Requests to me (append only: `- [from X, time] request`)
