# Contract: the store (SQLite database of the nightly runs)

- **Owner:** Victor (`engine/store/`). **Consumers:** Dani (`recon.kpi` reads it and writes `kpi_values`), phase 3 close (reads `transactions`).
- **Status:** draft v0.1. Schema: `engine/store/schema.sql` (the schema is that file; this page explains it).
- **Decision:** 007 point 2 (SQLite for the data, pages stay static), accepted by all three (Orlando's amendment, Victor's response).

## What it does
The engine and the pulse still write their files every night (`transaction.md`, `pulse.md`); those files stay the contract between them. The store is **where those files pile up**, so a week or a month of transactions, pulse rows and internal API snapshots can be queried in one place.

```
out/transactions.csv, out/pulse/<D>.json, out/warnings.json ──> python -m engine.store load --date D ──┐
internal API (mock)                                         ──> python -m engine.internal_api pull ────┼──> out/store/ecom.db
                                                                python -m recon.kpi (writes kpi_values) ┘
```

## Where and how
- **File:** `out/store/ecom.db` (under `out/`, so it's not committed). The `ECOM_DB` setting overrides the path. Python standard library `sqlite3`, no server, no new dependency.
- **Moving later:** the SQL is kept plain so it moves to Azure SQL or Postgres with a short migration script. The SQLite-only parts are marked `sqlite:` in `schema.sql`: `PRAGMA user_version` and the `date(...)` expressions in `v_weekly`.

| Command | State | What it does |
|---|---|---|
| `python -m engine.store [--db PATH] init` | built | Creates the database from `schema.sql`. Safe on an existing database. |
| `python -m engine.store [--db PATH] load --in-dir out [--date D] [--pulse-dir DIR]` | built | Loads one business date (rules below). `--date` defaults to the one in `source_status.json`; the pulse file defaults to `<in-dir>/pulse/<D>.json`. Exit 1 and nothing changed if an input is missing or wrong. |
| `python -m engine.store backfill --inbox DIR --from D1 --to D2 [--out out]` | built | Reads the inbox once, then for each day writes the engine files for that date (exactly what `engine run --date` writes), runs `recon.pulse`, loads the day and pulls that day's internal API snapshot. A failed day is listed and skipped; the others load; exit 1 if any day failed. The pulse files land in `<out>/pulse/`, the history Orlando's pages read. September: about 12 s. |
| `python -m engine.store status [--month M \| --from D1 --to D2]` | built | Per marketplace: days ok, missing, stale, unknown and not loaded, and revenue over the ok days ("no data" when none). Lists partial days (loaded, but an expected marketplace isn't ok) and days not loaded, and how many days have an internal API snapshot (and whether it's simulated). Default: the latest month in the store. |

## Conventions (all tables)
- Money: `INTEGER` cents. Dates: `TEXT 'YYYY-MM-DD'`, the Eastern business date. Timestamps: `TEXT`, ISO 8601 with offset.
- Key columns are never `NULL`. (SQLite treats NULLs in a primary key as all different, which would allow duplicate rows.) A single-value internal metric uses `dimension = 'total'` (`internal-api.md`); a single-value KPI uses `dimension = ''`.
- **A `NULL` measure means no data, never 0**, as in the pulse.

## Tables and views
| Name | One row per | Key | Written by |
|---|---|---|---|
| `transactions` | sale or refund: the columns of `transaction.md`, plus `units` (NULL until V2.7) and `run_id` | `txn_id` | `store load` |
| `pulse_daily` | business date and marketplace, from the pulse: `status` and the money/count fields. Measures are NULL when `status <> 'ok'` | `(business_date, marketplace)` | `store load` |
| `internal_daily` | business date, metric, dimension: `value`, `unit`, `source` (`mock` or `api`). Metric list: `internal-api.md` | `(business_date, metric, dimension)` | `internal_api pull` |
| `runs` | command that wrote to the store: when, which date, files read, rows written, warnings, result | `run_id` | every writer |
| `warnings` | engine warning, with the business date of the run that loaded it | `(run_id, seq)` | `store load` |
| `kpi_values` | period, KPI and dimension (`''`, or the category of a top 10 row): value, unit, status, source | `(period_type, period_start, kpi_id, dimension)` | `recon.kpi` |
| `v_daily` | business date: enterprise totals over the `ok` marketplaces, how many were ok and how many had no data | | view |
| `v_weekly` | ISO week (`week_start` = Monday, `week_end` = Sunday) and marketplace: `days_loaded`, `days_ok`, sums over `ok` days | | view |
| `v_monthly` | month (`'YYYY-MM'`) and marketplace: same fields as `v_weekly` | | view |

The views leave out `customers` on purpose: adding daily counts doesn't give distinct buyers over a week. Count distinct buyers from `transactions` instead (`customer_basis = 'buyer'`, per marketplace, since buyer ids aren't comparable across marketplaces).

## Load rules (`store load --date D`)
- **One date, one database transaction, all or nothing.** Load deletes every `transactions`, `pulse_daily` and `warnings` row for D, then inserts the new ones (`INSERT OR REPLACE` on `txn_id`, so a row whose date moved since the last load moves with it). **Re-running a date gives the same data** (only `run_id` and the `runs` log change), and rows a fixed engine no longer produces disappear (a plain per-row upsert would leave them behind).
- Only rows of `transactions.csv` with `business_date = D` are loaded; the file can hold other days (the month samples do).
- All four marketplaces of the pulse are stored, including `not_configured`, so "no data" is always a row, never a gap.
- Load needs `transactions.csv` and the pulse file for D (it says to run `recon.pulse` first if that's missing); `warnings.json` and `source_status.json` are optional. A pulse file for another date, or a missing required column, fails the load.
- A failed load writes nothing except a `runs` row with `result = 'failed'`; the previous load of D stays.
- `internal_api pull --date D` follows the same rule for `internal_daily`.

## Rules for readers (Dani)
- Read **only the tables and views above, by these names**. Don't import `engine.store`; that keeps the store's Python free to change.
- Open read-only when only reading: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`.
- **Writing `kpi_values`:** in one transaction, delete the rows for `(period_type, period_start)`, then insert the period's rows. `unit`, `status` and `source` follow `kpi.md`.
- **Test database without the loader:** the schema is enough.
  ```python
  import sqlite3; from pathlib import Path
  db = sqlite3.connect(":memory:")
  db.executescript(Path("engine/store/schema.sql").read_text(encoding="utf-8"))
  db.executemany("INSERT INTO pulse_daily VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)  # hand-made rows
  ```
- `PRAGMA user_version` is the schema version (1). Adding a column or a table is non-breaking; renaming or removing one changes this contract first.

## For the pitch (Orlando: use what helps on the slides and in the video)
How the store helps on the rubric. Every claim below is true of what we build; say "SQLite on the laptop" plainly.
- **Fits Their Constraints, "tools they already pay for" (19 pts).** The database is one file. There's no server, no licence, nothing for IT to install (it comes with Python), and it backs up like a spreadsheet. The next step stays inside what Goodwill already runs: the same tables move to **Azure SQL** (Microsoft, like Business Central and Microsoft 365), and Power BI connects to it directly. Today Power BI reads the KPI CSV.
- **Working Evidence (26 pts): a month, not one night.** The store keeps every night, so the demo can show September loaded (`store status --month 2026-09`: 30 of 30 days). The same data gives the day, week and month views, and a day with a missing file reads "no data", never $0.
- **Technical Substance (15 pts): the hard part is ours, and we know its limits.** Re-running a night gives the same database (load deletes the day and inserts it again in one transaction). Every number traces back: KPI -> `kpi_values` -> `pulse_daily` -> `transactions` -> `source_file` and `source_row` in the export staff dropped, and `runs` logs who wrote what and when. Limits to say out loud: one machine, one writer at a time, internal data simulated.
- **Partner Problem Fit (22 pts).** The COO's scorecard needs history: growth against the prior period, trends, repeat buyers over a month. Without a store each of those is a manual spreadsheet job.
- **Demo moments that take seconds:** (1) `store status` showing the month; (2) load the same night twice and show the totals don't move; (3) open the database in any SQLite viewer and query `v_monthly` live; (4) one KPI traced to the rows behind it.
- **Don't claim:** live Azure, multi-user access, or real internal data. The rubric's overclaim flag drops Working Evidence to level 1.

## Changelog
- v0.4 (2026-10-04, Victor): backfill also pulls the internal snapshot; status shows internal coverage; `runs.command` is `load` or `pull` so far.
- v0.3 (2026-10-03, Victor): `status` and `backfill` built.
- v0.2 (2026-10-03, Victor): `init` and `load` built (`engine/store/`, tests in `engine/tests/test_store.py`). Wording: a re-run gives the same data, not the same file. Load's required and optional inputs are listed.
- draft v0.1 (2026-10-03, Victor): initial, from `docs/PLAN_PHASE_2_3.md` section 6. Adds `warnings` and `v_daily` (not in the plan), `units` in `transactions`, and the delete-then-insert load rule.
