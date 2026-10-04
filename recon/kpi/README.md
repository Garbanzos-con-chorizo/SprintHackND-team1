# Dani's lane, phase 2: the scorecard KPIs

Contract: `docs/contracts/kpi.md`. Plan: `docs/PLAN_PHASE_2_3.md` (tasks D2.1 to D2.11). For live status see `docs/members/dani.md`.

## What this part does
Goodwill's own scorecard (deck slide 35) is 15 KPIs in five areas. This part reads a day, a week or a month of what the nightly runs stored, does all the arithmetic, and writes one JSON file. The page, the PDF and the CSV only display that file.

```
Victor (engine/store/)           ->  Dani (recon/kpi/)             ->  Orlando (reports/), Victor (exports)
out/store/ecom.db                    out/kpi/<type>-<id>.json          scorecard page, PDF, CSV
pulse_daily, transactions,           15 KPIs, each with its status,
internal_daily                       note, prior value and change
```

## How to run it
From the repo root. On Dani's machine Python is only on the `py` launcher; elsewhere use `python`. Standard library only.

```bash
py -m unittest discover -s recon -t .
```

```bash
py -m recon.kpi --month 2026-09
```

| Option | Default | Meaning |
|---|---|---|
| `--date D`, `--week YYYY-Www`, `--month YYYY-MM` | | The period to report |
| `--period day\|week\|month` | implied by the option above | Alone: the period that contains the latest stored day ("this month to date") |
| `--through D` | The period's end, or the latest stored day if earlier | Last day to cover |
| `--db` | `ECOM_DB`, else `out/store/ecom.db` | The store |
| `--out-dir` | `out/kpi` | Where the files go |

It writes `<type>-<id>.json`, refreshes `latest-<type>.json`, and records the same numbers in the store's `kpi_values`. Exit code 0 when a file is written, even if KPIs have no data; 1 if the store cannot be read; 2 if the options make no sense.

To try it before the real store is loaded, build the test database (synthetic: September and October 1 to 4) and point the command at it:

```bash
py -m recon.tests.kpi_samples --db out/store/ecom.db
```

```bash
py -m recon.kpi --period week
```

## The code
| File | Role |
|---|---|
| `catalog.py` | The 15 KPIs in display order: id, area, Goodwill's name, unit, which way is good, source, definition. |
| `periods.py` | Day, ISO week, month; what "to date" means; the window a period is compared with; labels. |
| `store.py` | The only module that knows the store's tables. Reads through a read-only connection; writes only `kpi_values` and its `runs` line. |
| `facts.py` | What is stored for one window, summed up once: coverage, totals from the files, buyers, internal flows and snapshots, the revenue split by category. |
| `kpis.py` | One function per KPI, from the facts of its window (and of the comparison window, for growth). Each says what was missing. |
| `calc.py` | Shapes the file: status, reason and note of each KPI, prior value and change, the period and coverage blocks. |
| `io.py`, `cli.py` | Write the files; the command. |

Everything from `facts.py` to `calc.py` is pure: data in, dictionary out. If the store is late (the 10:00 tripwire in decision 007), reading the files instead means one more function that returns the same `WindowData` as `store.load`.

Rules that hold for every KPI (they are in the contract; the tests pin them):
- **No data is `null`, never 0.** A 0 is a real zero: a Sunday with nothing listed is `0`, a Sunday with no labor hours makes revenue per labor hour `no_data`, not infinity.
- **`partial` is shown, flagged.** A missing marketplace-day flags every KPI that uses the files and leaves the internal ones alone.
- **Simulated stays visible.** 11 of the 15 KPIs use internal data; while that comes from the mock, each is `simulated: true`.
- The top 10 categories add up to total revenue to the cent, and net margin uses the same cost of goods as the margin ranking.

## Tests: `recon/tests/test_kpi_*.py`
113 tests (144 with the pulse), all passing.

- `test_kpi_calc.py`: all 15 KPIs against values worked out by hand on two days of a week, then one test per state: a missing day, a day never loaded, no data at all, real zeros, no prior period, a partial comparison, different bases, no internal data, internal data for some days, an old snapshot, zero divisors, more than ten categories.
- `test_kpi_periods.py`: ids, to-date windows, comparison windows, labels.
- `test_kpi_store.py`: reading the store built from `engine/store/schema.sql`, optional tables, read-only access, errors.
- `test_kpi_cli.py`: the command on the sample database. **It reproduces the four contract examples exactly**, September revenue equals the answer key of `data/sample/clean_month` to the cent (7,075,396), `kpi_values` is written and replaced on a re-run, and the error exits.
- `kpi_samples.py` (not a test): builds the test databases and regenerates the contract examples.

## Known limits
- **Verified end to end on 2026-10-03** (checkpoint 1), with the real commands: `engine.store backfill` on `clean_month` (engine, pulse, store load and internal pull for 30 days), then `recon.kpi --month 2026-09`. Revenue 7,075,396, refunds, fees and orders all equal the answer key; 13 KPIs `ok`, growth `no_data` (nothing stored for August), repeat buyers `partial` (Amazon gives no buyer id). The four `day_*` nights through `reports.run_nightly` and the `messy_month` (revenue 6,850,986 = its key, the three stale marketplace-days flagged) agree too. Every scalar KPI of those files was recomputed with plain SQL on the store: no difference.
- **Sell-through is two boxes in the file; the split behind them is simulated.** The single rate (sold / listed in the period) passes 100% on short periods because older listings sell too. So `parts` gives two boxes: what sold of the period's own listings, and what sold of the stock left from earlier (the listings still active the night before). Which listing a sale came from is read from the internal API's sales by listing date (`listing_to_sale_days`, the mock today): September on the real pipeline reads 61.3% and 15.3%. If that metric is missing, the calculator assumes that what was listed in the period sells first and says so (`inputs.split_basis` = `period_first`). **The page does not draw the two boxes yet** (Orlando was paged; see the handoff in `docs/members/dani.md`).
- The whole suite passes on this machine since Victor's PDF and content-type fixes: `python -m pytest engine recon reports -q` -> 347 passed, 1 skipped (2026-10-03 23:40).
- **11 of the 15 KPIs are simulated** until Goodwill's internal data is real.
- Growth compares with the period before, not year over year (needs 13 months stored).
- Average selling price and sell-through are per unit since the transactions carry `units` (per order only if a sale row has none).
- Categories come from splitting revenue by the internal category shares, not from each sale's own category.
- Repeat buyer rate covers only marketplaces that give a buyer id, and is not computed for a single day.
- A whole month is compared with the whole month before, so 30 days can face 31.

## What is left
1. ~~D2.11: delete the math from `reports/kpi.py`~~ done (L6, 2026-10-04): the weekly page reads the KPI file; `reports/kpi.py` and `reports/mock_api.py` are gone.
2. Apply Goodwill's answers to the open definitions (one constant each, top of `kpis.py`).
