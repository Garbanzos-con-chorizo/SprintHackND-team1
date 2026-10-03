# Status — Victor (core engine, `engine/`)

Only the owner edits this file, except the "Requests to me" section, where teammates/agents may append.

**Last updated:** 2026-10-03 · **Branch:** victor/ingest-framework

## Done
- Phase split of all tasks: `docs/PHASES.md`
- Phase 1 transaction contract (draft): `docs/contracts/transaction.md`, mock `docs/contracts/examples/transactions.sample.csv`
- Handoff map: `docs/HANDOFFS.md` (PR #4)
- `out/.gitignore` so generated output is not committed (no root file touched)

- V1 scaffold in `engine/` (branch `victor/v1-scaffold`): `python -m engine run` writes valid empty `transactions.csv`, `source_status.json` (all sources `missing`) and `warnings.json`; 2 tests pass. No parsers yet.

- Portal acquisition skeleton (branch `victor/scraper-skeleton`, stacked on V2): `python -m engine fetch` runs one scraper per portal (HTTP or browser backend), saves reports to `inbox/`, logs to `out/fetch_log.json`. Upright is a skeleton only (no URLs/selectors known). Decision 003 proposed.

- V3 parsers (branch `victor/v3-parsers`, stacked on the scraper skeleton): ShopGoodwill, eBay, Amazon on a shared `OrderReportParser`; money/date cleaning in `engine/clean.py`; 56 tests pass. Checked against Orlando's synthetic samples (`data/sample/*`): 64 of 66 marketplace-days off at first, now all match except the overlapping eBay re-download, which needs P-V5. Column names are still not from real Goodwill files, and ShopGoodwill's layout is a guess on both sides. Not yet done: cross-file dedupe (P-V5), source status (P-V4), day cutoff config (P-V3 beyond timezone).

- P-V5 cross-file dedupe (`engine/dedupe.py`): keeps the first copy, logs the rest, flags conflicting amounts. All 5 of Orlando's scenarios now match their answer keys (0 of 66 marketplace-days off).
- `docs/contracts/source-formats.md`: what the deck actually shows about the real files. **Finding: the nightly ShopGoodwill file is probably Upright's Paid Orders report and eBay/Amazon probably come from one Cash Monkey Orders CSV, not the seller-portal reports our samples imitate.** Orlando should read it before changing `data/generate.py`.

- Pluggable ingestion (branch `victor/ingest-framework`): `engine/ingest/` with `DataIngestAdapter.fetch_and_normalize()`, `EmailAttachmentAdapter` (CSV/TSV/TXT/XLSX from the inbox folder, which is also where manual exports and ERP file drops land), `MockScraperAdapter` (synthetic fixture, no network), and `ingest()` which merges adapters and dedupes. `python -m engine run` now goes through it. 8 new tests, 70 in total.

### Assumptions (stated on purpose, change any of them and tell Victor)
1. **Lane and paths:** the request named `src/ingest/` and `tests/test_ingest.py`. Our lane is `engine/` and new top-level dirs need a decision record, so it lives in `engine/ingest/` and `engine/tests/test_ingest.py`. Branch is `victor/ingest-framework` (team convention) not `feature/ingest-framework`.
2. **Reuse, not rewrite:** reading and cleaning reuse the existing source parsers (ShopGoodwill, eBay, Amazon). "Normalized format" means the canonical transaction CSV in `docs/contracts/transaction.md`.
3. **Email is a folder:** we do not connect to a mailbox. Someone saves the attachment (or the ERP's export) into `inbox/`. Reading an actual email account is not built.
4. **ERP drop = a file drop:** an ERP export is only supported if it is CSV/XLSX and a parser exists for its columns. No ERP API.
5. **Extensions:** `.csv .tsv .txt .xlsx`. Legacy `.xls` and `.xlsm` are reported as a warning, not read. Only the first sheet of a workbook is read.
6. **Sources are the three we have parsers for**, whose column names come from the team's synthetic samples, not real Goodwill files (see `docs/contracts/source-formats.md`: the real nightly sources are probably Upright and Cash Monkey, which have no parser yet).
7. **Scraper is a stub:** `MockScraperAdapter` is handed the records a scraper would have extracted (a JSON fixture or a list of dicts keyed by the source's column names). No login, no network, no paging, no retries. The real scrapers in `engine/scrapers/` are separate and still skeletons.
8. **Duplicates across adapters:** the same transaction from two adapters counts once; the first adapter's copy wins and the other is logged.

## In progress (claimed, so nobody doubles up)
- P-V4 real `source_status.json`, P-V3 day cutoff config, V9 runner summary (all `engine/`)
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
