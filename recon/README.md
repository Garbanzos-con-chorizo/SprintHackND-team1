# Dani's lane: nightly pulse calculation (phase 1)

Summary of everything built so far for Dani's part of phase 1, as of 2026-10-03 16:45 EDT. For live status see `docs/members/dani.md`.

Phase 2, the scorecard KPIs, is in `recon/kpi/README.md`.

## What this part does

The nightly pulse answers one question each night: how much did we sell, and to how many customers, on each marketplace and in total. Three people share it:

```
Victor (engine/)        ->  Dani (recon/pulse/)       ->  Orlando (reports/)
messy exports to            clean rows to                 daily numbers to
clean rows                  daily numbers                 a page people read
out/transactions.csv        out/pulse/<date>.json         reports/pulse/<date>.html
```

Dani's piece is the middle one. It reads the clean files Victor's engine writes, does all the arithmetic, and writes one JSON file per day. Orlando's renderer only displays that file; it never calculates.

## State of the work

| Task | What | State |
|---|---|---|
| P0 | Pulse contract and two mock files | Done, PR #9 open, not merged |
| D1 | `recon/` scaffold and mock input (fixtures) | Done |
| P-D1 | Revenue: gross, refunds, net, fees separate | Done |
| P-D2 | Orders, customers, enterprise totals, missing sources left out | Done |
| P-D3 | Day-over-day delta | Done |
| P-D4 | Pulse JSON files and the `pulse --date` command | Done |
| P-D5 | Tests for the five scenarios | Done on hand-made fixtures; to re-run on Orlando's sample days (P-O1) |

Everything runs on mock data only. It has **not** been run against Victor's real engine output, because the engine does not exist yet. That happens at integration (I1).

Branches:
- `claude/phase-1-data-processing-plan-fd1a0c`: the contract, mocks and status file. This is PR #9.
- `d/pulse-scaffold`: all the code, stacked on the branch above. Pushed, no PR yet; open it when PR #9 merges.

## What was written

### The contract: `docs/contracts/pulse.md`
The agreement between Dani and Orlando on the shape of the pulse file. The main decisions in it:

- **Always four marketplaces**, in display order: `shopgoodwill`, `amazon`, `ebay`, `other`.
- **Money is integer cents.** No floating point, so no rounding drift.
- **Revenue = sales minus refunds.** `revenue_cents = gross_cents + refunds_cents` (refunds are negative). Fees are reported in `fees_cents` and never subtracted.
- **Orders** = distinct order ids on sale rows. A refund is not an order.
- **Customers** = distinct buyer ids where the marketplace gives one, otherwise distinct orders. `customer_basis` says which (`buyer`, `order` or `mixed`) so the report can label it honestly.
- **No data is `null`, never `0`.** A marketplace whose file is missing shows "no data". A `0` only means a real zero.
- **Five statuses.** `ok`; `missing` (no file); `stale` (a file, but no rows for that day); `unknown` (no status information for that day); `not_configured` (nothing feeds it, which is `other` for now).
- **Enterprise total = sum of the `ok` marketplaces only**, with `included` and `excluded` lists so a partial total is visible as partial.
- **Delta** against the prior calendar day, with a `reason` whenever the comparison is not valid.

Two mock files sit beside it for Orlando to build against: `examples/pulse.sample.json` (clean day) and `examples/pulse.sample.missing.json` (eBay missing). Their prior-day figures are invented.

These rules are defaults. Questions 5 to 7, 9, 11 and 12 in `docs/OFFICE_HOURS.md` are still open with Amanda, and an answer may change a definition.

### The code: `recon/pulse/`
Python, standard library only, so no dependency was added.

| File | Role |
|---|---|
| `io.py` | Reads `transactions.csv`, `source_status.json`, `warnings.json` and an earlier pulse file; writes the pulse files. |
| `calc.py` | All the numbers. Pure functions: rows in, dictionary out, no file access. |
| `cli.py` | The command: parses arguments, calls `io` and `calc`, prints one summary line. |
| `__main__.py` | Makes `python -m recon.pulse` work. |

How `calc.py` builds a day:

1. `marketplace_statuses` decides the status of each marketplace from `source_status.json`. If that file is absent or is for another day, a marketplace with rows is `ok` and one without is `unknown`.
2. `summarize` computes the numbers for each `ok` marketplace. The others get `null`.
3. `day_summary` adds the enterprise totals over the `ok` marketplaces.
4. `add_deltas` compares with the prior day.
5. `build_pulse` assembles the file, with `data_quality` (warning counts) and `definitions` (footnote text).

How the delta gets its prior day: it uses `out/pulse/<prior date>.json` if that file exists, because that file knows which sources were missing that day. Otherwise it recomputes the prior day from the rows.

| `reason` | When | What is null |
|---|---|---|
| `null` | Valid comparison | Nothing |
| `current_not_ok` | Today has no data for this marketplace | The change fields |
| `prior_unavailable` | No data for the prior day | The change fields and prior figures |
| `prior_zero` | Prior revenue was zero | Only the percentage |
| `coverage_changed` | Enterprise only: different marketplaces reported on the two days | The change fields |

Safety behaviour in `io.py`:
- A row that breaks the transaction contract stops the run with the file and line number, rather than producing a wrong total.
- A repeated `txn_id` is dropped (first one wins) and reported, even though the engine is supposed to dedupe already.
- An unreadable prior pulse file is ignored and the prior day is recomputed from the rows.

### Mock input: `recon/tests/fixtures/`
Five folders, each shaped like the engine's `out/` folder, all reporting 2026-10-02. Hand-made, so work is not blocked on Victor or Orlando.

| Scenario | What it proves |
|---|---|
| `clean_day` | Normal day, with prior-day rows so the delta works |
| `refund_day` | Refunds reduce revenue, including a refund of a sale from the day before |
| `missing_source` | eBay missing and Amazon stale are shown as no data and left out of the total |
| `duplicate_rows` | A repeated row does not double count; duplicate warnings are counted |
| `zero_revenue` | A fully refunded day is a real `0`, not "no data" |

### Tests: `recon/tests/`
31 tests, all passing.

- `test_io.py`: the loaders, and that every fixture follows the transaction contract.
- `test_calc.py`: the five scenarios, totals equal the sum of the rows shown, status when the status file is absent or for another day, every delta `reason`, and that the calculator reproduces both published mock files exactly.
- `test_cli.py`: files are written, `latest.json` stays on the greatest date, the prior pulse file is used, and the error exits.

## How to run it

From the repo root. On Dani's machine Python is only on the `py` launcher; elsewhere use `python`.

```bash
py -m unittest discover -s recon -t .
```

```bash
py -m recon.pulse --date 2026-10-02
```

| Option | Default | Meaning |
|---|---|---|
| `--date` | The date in `source_status.json` | Business day to report |
| `--in-dir` | `out` | Folder with the engine's three files |
| `--out-dir` | `<in-dir>/pulse` | Where the pulse files go |

It writes `<date>.json` and refreshes `latest.json`. Exit code 0 when a file is written, even with missing sources; 1 if `transactions.csv` cannot be read or no date can be determined.

To try it now, with no engine, point it at a fixture and pass `--out-dir` so nothing is written inside the fixture folder:

```bash
py -m recon.pulse --in-dir recon/tests/fixtures/missing_source --out-dir out/pulse
```

## Known limits

- Runs on mock data only until integration.
- When there is no prior pulse file, the recomputed prior day cannot tell a missing source from a day without sales. It treats a marketplace with no rows as unavailable, so the delta is `null` rather than a comparison against zero.
- If `source_status.json` says a source is `missing` or `stale` but rows for that day exist anyway, the status file wins and the marketplace shows no data.
- Enterprise customers is a sum across marketplaces, so a person buying on two of them counts twice. Buyer ids are not comparable across marketplaces.
- `data_quality` counts cover the whole engine run, not one day, because warnings carry no date.
- `other` is always `not_configured` until a source is mapped to it (Q9).
- The `out/` folder is ignored by git only on Victor's unmerged branch `victor/phase1-contracts`.

## What is left for Dani in phase 1

1. Get PR #9 (contract) reviewed and merged, then open the PR for `d/pulse-scaffold`.
2. Re-run the tests on Orlando's P-O1 sample days when they exist.
3. Integration (I1): run on Victor's real `out/` and fix what differs.
4. Apply Amanda's answers if they change a definition.
