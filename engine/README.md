# The engine: from Goodwill's reports to clean daily numbers

The engine turns the reports Goodwill already receives (emailed Excel from Upright and Cash Monkey) into three clean files that the pulse calculation reads. It is the part of the nightly pulse that deals with **messy input**. Everything is synthetic until Goodwill gives us a real file; see `docs/ASSUMPTIONS.md` for what we assumed and why.

```
provider API (assumed, simulated)  ->  emailed .xlsx  ->  inbox/        <- or a person drops the file here
                                                            |
                                              python -m engine run
                                                            |
        out/transactions.csv   out/source_status.json   out/warnings.json
                                                            |
                            python -m recon.pulse (Dani)  ->  out/pulse/<date>.json  ->  page, CSV, email (Orlando)
```

## Run it
Python 3.12+ for the whole repo (the engine alone also runs on 3.11, decision 002).
```
pip install -r engine/requirements.txt          # openpyxl, pytest, tzdata
python -m engine fetch --simulate --date 2026-10-02     # demo: the providers' simulated emails land in inbox/
python -m engine run --date 2026-10-02                  # inbox/ -> out/ (add --inbox DIR --out DIR to change folders)
python -m recon.pulse --date 2026-10-02                 # the pulse, from out/
python -m pytest engine -q                              # 140 tests
```
Without `--simulate`, `fetch` calls the real provider APIs, which are stubs that report "not configured" (nobody has seen the APIs). `run` reads whatever is in the inbox, whether a provider delivered it or a person dropped it there.

## What it does to the data
1. **Reads** `.csv`, `.tsv`, `.txt` and `.xlsx` (first sheet). It skips title lines above the header, blank rows and a leading byte-order mark, and matches column names ignoring case, spaces and underscores. Legacy `.xls` is reported as a warning, not read.
2. **Recognizes the source** from the columns first and the file name second (people rename downloads). If two sources match equally it refuses to guess and warns.
3. **Parses** each file into one row per order, in one canonical format (`docs/contracts/transaction.md`): money as integer cents, the marketplace, the customer, the fee, and the **Eastern business day**.
4. **Cleans:** `$1,234.50`, `(12.00)` and `12.00-` become cents; dates in many shapes become the Eastern day; a time stamped in Pacific (Upright) or UTC (Cash Monkey) is converted, so a late-evening sale lands on the right day; the lines of one order are summed; a buyer's email is hashed; `--`, payouts and transfers are skipped; a refund counts on the day it is issued.
5. **De-duplicates** across files: the same transaction in two downloads counts once, and the log says which copy was dropped (and says so if the two copies disagree).
6. **Never crashes and never hides a loss:** a bad row, an unreadable file or an unrecognized file becomes a line in `warnings.json`. A missing report becomes `missing` or `stale` in `source_status.json`, so the pulse shows "no data" instead of $0.

The three outputs are the contract with Dani's side: `transactions.csv` (clean rows), `source_status.json` (per marketplace: `ok`, `stale`, `missing`), `warnings.json` (what was dropped and why). For the month-end close the same run also writes `payouts.csv` (eBay `Payout` and Amazon `Transfer` rows, de-duplicated) and `bank.csv` (every bank line, credits positive): `docs/contracts/close-inputs.md`.

## Month-end sources for the close (simulated APIs)
```
python -m engine fetch --simulate --close-month 2026-09 --inbox out/sim/inbox --out out/sim   # the files and their answer key
python -m engine run --inbox out/sim/inbox --out out/sim/out --date 2026-09-30               # ledger.csv, statements.csv, jewelry.csv, bank.csv
```
Goodwill's slide 38 lists month-end sources nobody has shown us. We assume each can be fetched through an API (`docs/ASSUMPTIONS.md` 2c) and build each as a provider whose real client is a stub and whose simulator writes the file the API would have delivered. **Every layout and every value is ours and synthetic.** The only values that are Goodwill's are the four FedEx codes on the slide.

| Source | What the simulator writes | Engine output |
|---|---|---|
| FedEx (Business Central ledger) | G/L entries: charges on 40356 / department 180 / vendor V00122, BNKDEPOSIT refunds, and rows the filter must leave out | `ledger.csv` |
| OSM, PB, EasyPost (bank account 0101) | the account's month: carrier debits, other debits, the Goodwill Books payment as a credit | rows of `bank.csv` with account `0101` |
| Goodwill Books | the prior month's payment statement | `statements.csv` |
| Jewelry | the month's jewelry sales without a supplier, and a supplier lookup with one item missing | `jewelry.csv` (the engine joins them; an unknown item is a `missing_supplier` warning) |
| ShopGoodwill periodic report | on request only (`--source shopgoodwill_periodic`): the sample months have their own in `data/sample/<month>/periodic/` | ShopGoodwill rows of `payouts.csv`, each with its period |

The fetch log, `<inbox>/_simulated.json` and `source_coverage.json` mark every simulated file. `expected_close_sources.json` is the answer key, computed from the generated records and never by a parser. The engine applies no rule to these files: which ledger rows are FedEx and which bank lines are a carrier is the close's job. Columns: `docs/contracts/close-inputs.md`.

## Where things are
| Path | What it is |
|---|---|
| `engine/cli.py` | the `run` and `fetch` commands |
| `engine/table.py` | reads any CSV or Excel into a table; no parser opens a file itself |
| `engine/parsers.py` | the `Parser` base class, the registry, and source detection |
| `engine/sources/` | **one file per source** (`upright.py`, `cashmonkey.py`, and the older single-marketplace `ebay.py`, `amazon.py`, `shopgoodwill.py`); `_common.py` is the shared order-report parser |
| `engine/clean.py` | money, dates and timezones, buyer hashing |
| `engine/dedupe.py`, `engine/status.py`, `engine/writer.py` | cross-file dedupe, the source status, writing the three files |
| `engine/ingest/` | the adapter layer: `DataIngestAdapter`, the inbox reader, a mock scraper adapter, and `ingest()` which merges them |
| `engine/scrapers/` | one class per provider with a real-API stub and a **simulator** (`simulation.py`); the `fetch` command |
| `engine/tools/make_sample.py` | generates synthetic inboxes plus an answer key, and checks the pipeline against it |
| `engine/store/`, `engine/internal_api/` | phase 2 (database and the mock internal API); see `docs/contracts/store.md` and `docs/contracts/internal-api.md` |

## Add a source or a provider
- **A new report layout:** one file in `engine/sources/` with a `Parser` subclass and `@register`. Declare the column names, the filename pattern, the timezone of its timestamps and (if it lists several marketplaces) a channel map. If it is one row per order or line, the shared `OrderReportParser` does the rest. Nothing else changes: it is found automatically. The recipe is the docstring of `engine/parsers.py`.
- **A new provider API:** one file in `engine/scrapers/` with a `Scraper` subclass, `@register_scraper`, a `fetch` that raises "not configured" until the API is documented, and a `simulate` that writes the report it would have emailed. `fetch --simulate` picks it up.
- **A new marketplace on the pulse** (a fifth row) is *not* just a file: the pulse has exactly four keys, so it needs a change to `docs/contracts/pulse.md`.

## How we know it works
- **Answer keys we did not get from the engine.** `python -m engine.tools.make_sample --scenario messy_day --check --pulse` builds synthetic orders, renders them as the messy files, computes the expected numbers **from the orders**, then runs the real engine and Dani's real pulse and compares. The same is done with Orlando's independently written samples in `data/sample/`: all 8 scenarios match their answer keys through the pulse (24 of 24 marketplace-days).
- **Checks that can fail.** We broke the timezone handling and the duplicate rule on purpose and confirmed the tests catch it. One of those sabotage runs first slipped through because the random data had no early-morning order, so the simulator now plants boundary orders every day.
- **Messy cases covered:** duplicated downloads, an overlapping re-download, refunds, a missing report, a malformed row, a bad date, a blank line, another channel mixed into a file, sales that cross midnight in UTC or Pacific, and one line per unit.

## What it does not do (say this out loud)
- **No real Goodwill file has been read.** Upright's columns come from a screenshot (a few headers are cut off, and a couple are guessed). Cash Monkey's columns are guesses: the deck never shows the file. Both spellings we have seen of two column names are accepted as a hedge, not as proof.
- **No real API client.** Amanda told us to assume an Upright API that emails the report; we have never seen it. The clients are stubs and the simulators produce synthetic data. The simulators are labelled in the fetch log.
- **No scheduler.** `python -m reports.run_nightly` runs once when called. In production Windows Task Scheduler or cron would call it just after midnight Eastern.
- **No mailbox reader.** An email rule would save attachments into `inbox/`.
- **Brick and mortar is out of scope.** For the month-end close the engine only hands over clean files (`docs/contracts/close-inputs.md`); the rules, the matching and the Business Central files are `reports/`.
- **No month-end source is real.** The Business Central ledger, the bank feed of account 0101, the Goodwill Books statement, the Jewelry Report with its supplier lookup and the ShopGoodwill periodic report are simulated, with layouts we made up.
- Two unknowns could change the numbers: whether Cash Monkey's report covers only Goodwill Books, and how staff count customers for it. See `docs/PHASE1_ALIGNMENT.md`.
