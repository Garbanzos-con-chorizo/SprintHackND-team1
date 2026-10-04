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
102 tests (133 with the pulse), all passing.

- `test_kpi_calc.py`: all 15 KPIs against values worked out by hand on two days of a week, then one test per state: a missing day, a day never loaded, no data at all, real zeros, no prior period, a partial comparison, different bases, no internal data, internal data for some days, an old snapshot, zero divisors, more than ten categories.
- `test_kpi_periods.py`: ids, to-date windows, comparison windows, labels.
- `test_kpi_store.py`: reading the store built from `engine/store/schema.sql`, optional tables, read-only access, errors.
- `test_kpi_cli.py`: the command on the sample database. **It reproduces the four contract examples exactly**, September revenue equals the answer key of `data/sample/clean_month` to the cent (7,075,396), `kpi_values` is written and replaced on a re-run, and the error exits.
- `kpi_samples.py` (not a test): builds the test databases and regenerates the contract examples.

## Known limits
- **Run on Victor's loader, but only on two fixture days, and never on the engine's own output.** Checked by hand on 2026-10-03: `recon/tests/fixtures/clean_day` -> `recon.pulse` -> `engine.store` `load_day` -> `recon.kpi --date 2026-10-02` gives revenue 30,147 with the prior day 25,800, the pulse's own numbers, and writes `kpi_values`. What has not been run: the engine's real output for a month (its dependencies are not installed on this machine), and anything with internal data, because `internal_api pull` does not exist yet. Both are checkpoint 1.
- **11 of the 15 KPIs are simulated** until Goodwill's internal data is real.
- Growth compares with the period before, not year over year (needs 13 months stored).
- Average selling price and sell-through are per order until the transactions carry `units`.
- Categories come from splitting revenue by the internal category shares, not from each sale's own category.
- Repeat buyer rate covers only marketplaces that give a buyer id, and is not computed for a single day.
- A whole month is compared with the whole month before, so 30 days can face 31.

## What is left
1. Checkpoint 1: run on the store once September is loaded (V2.4, V2.6); revenue must read 7,075,396.
2. D2.11, with Orlando: delete the math from `reports/kpi.py` once the page reads the KPI file.
3. Apply Goodwill's answers to the open definitions (one constant each, top of `kpis.py`).
