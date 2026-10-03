# Contract: nightly pulse JSON, phase 1 (task P0)

- **Owner:** Dani (`recon/pulse/`). **Consumers:** Orlando (pulse rendering P-O2 to P-O4, later the dashboard).
- **Status:** draft
- **Inputs:** the three files in `docs/contracts/transaction.md` (`out/transactions.csv`, `out/source_status.json`, `out/warnings.json`).

## What this contract does
Turns the clean transaction rows into the daily numbers, so the renderer does no arithmetic and makes no decisions about missing data.

```
out/transactions.csv   ┐
out/source_status.json ├─> python -m recon.pulse --date YYYY-MM-DD ─> out/pulse/<YYYY-MM-DD>.json
out/warnings.json      ┘                                           ─> out/pulse/latest.json
```
- `--date` is optional; the default is `business_date` from `source_status.json`.
- Re-running a date overwrites its file. `latest.json` is a copy of the file with the greatest date in `out/pulse/`.
- Exit code 0 whenever a pulse file is written, including with missing sources. Non-zero only if `transactions.csv` is absent or unreadable.

## `out/pulse/<YYYY-MM-DD>.json`
JSON, UTF-8. All money is integer USD cents. Examples: `examples/pulse.sample.json` (clean day, computed from `examples/transactions.sample.csv`) and `examples/pulse.sample.missing.json` (eBay file missing).

### Top level
| Field | Type | Rule |
|---|---|---|
| `schema_version` | integer | `1`. |
| `business_date` | date | `YYYY-MM-DD`, the day reported. |
| `generated_at` | datetime | ISO 8601 with offset. |
| `currency` | string | `"USD"`. |
| `marketplaces` | object | Always exactly four keys, in display order: `shopgoodwill`, `amazon`, `ebay`, `other`. |
| `enterprise` | object | Totals over the marketplaces with `status = ok`. |
| `data_quality` | object or null | Counts from `warnings.json`; `null` if that file is absent. |
| `definitions` | object | The definitions used, as text to print in the footnote. |

### `marketplaces.<name>`
| Field | Type | Rule |
|---|---|---|
| `status` | enum | `ok`, `missing`, `stale`, `unknown`, `not_configured`. See Status below. |
| `gross_cents` | integer or null | Sum of `gross_cents` over `sale` rows. |
| `refunds_cents` | integer or null | Sum of `gross_cents` over `refund` rows, so zero or negative. |
| `revenue_cents` | integer or null | `gross_cents + refunds_cents`. This is the headline number. |
| `fees_cents` | integer or null | Sum of `fee_cents`. Reported separately, never subtracted from revenue. |
| `orders` | integer or null | Distinct `order_id` over `sale` rows. A refund is not an order. |
| `customers` | integer or null | Distinct `customer_id` over `sale` rows with `customer_basis = buyer`, plus distinct `order_id` over `sale` rows with `customer_basis = order`. |
| `customer_basis` | enum or null | `buyer`, `order`, or `mixed` if the marketplace has both kinds of row. Label the metric with it. |
| `delta` | object | Change against the prior day. See Delta below. |

**When `status` is not `ok`, every numeric field and `customer_basis` is `null`, never `0`.** Render `null` as "no data". A `0` only ever means a real zero (for example a day whose sales were all refunded).

### Status
The pulse is keyed by marketplace, `source_status.json` by source. A marketplace's status comes from the sources mapped to it (1:1 in phase 1).

| Status | Meaning | In totals |
|---|---|---|
| `ok` | The source is `ok` in `source_status.json`. | yes |
| `missing` | No file for the source. | no |
| `stale` | A file exists but has no rows for this date. Treated as no data, since we can't tell a quiet day from an old export. | no |
| `unknown` | `source_status.json` is absent or is for a different date, and the marketplace has no rows for this date. (With rows it is `ok`.) | no |
| `not_configured` | No source feeds this marketplace. Only `other` in phase 1, until Q9 is answered. The renderer may show a dash or hide the row. | no |

If several sources feed one marketplace later: `ok` if any is `ok`, and the non-ok ones are listed in `enterprise.excluded`.

### `enterprise`
| Field | Type | Rule |
|---|---|---|
| `gross_cents`, `refunds_cents`, `revenue_cents`, `fees_cents`, `orders`, `customers` | integer | Sum of the same field over marketplaces with `status = ok`. **Always equals the sum of the rows shown.** `0` if none are `ok`. |
| `customer_basis` | enum or null | The single basis if all included marketplaces share it, else `mixed`. `null` if none are `ok`. |
| `included` | string[] | Marketplaces summed. |
| `excluded` | object[] | `{ "marketplace", "status" }` for each one left out as `missing`, `stale` or `unknown`. `not_configured` is not listed. Non-empty means the total is partial; say so on the report. |
| `delta` | object | See Delta below. |

`customers` is a sum, so a buyer who buys on two marketplaces counts twice. Buyer ids are not comparable across marketplaces.

### Delta
Prior day is the calendar day before `business_date`. Prior values come from `out/pulse/<prior>.json` if it exists, otherwise they are recomputed from `transactions.csv`.

| Field | Type | Rule |
|---|---|---|
| `prior_date` | date | |
| `prior_revenue_cents`, `prior_customers` | integer or null | |
| `revenue_cents`, `customers` | integer or null | Current minus prior. |
| `revenue_pct` | number or null | Percent change, one decimal. `null` if prior revenue is zero or negative. |
| `reason` | enum or null | `null` when the delta is valid. Otherwise why it is not, and the delta fields are `null`. |

`reason` values: `current_not_ok` (today has no data), `prior_unavailable` (no data for the prior day), `coverage_changed` (enterprise only: the set of included marketplaces differs between the two days, so the totals are not comparable), `prior_zero` (the amounts are valid, only `revenue_pct` is `null`).

### `data_quality`
```json
{ "warnings_total": 3, "by_kind": { "duplicate": 2, "bad_date": 1 } }
```
Counts for the whole engine run, not only this date, because warnings carry no date. `by_kind` lists only kinds that occurred.

### `definitions`
Keys `revenue`, `fees`, `customers`, `day`, each a sentence to print as is. They state the defaults in `transaction.md` until Amanda answers Q5 to Q7, and change here when she does.

## Example (clean day, shortened)
```json
{
  "schema_version": 1,
  "business_date": "2026-10-02",
  "marketplaces": {
    "ebay": {
      "status": "ok",
      "gross_cents": 4449, "refunds_cents": -2599, "revenue_cents": 1850, "fees_cents": 576,
      "orders": 2, "customers": 2, "customer_basis": "buyer",
      "delta": { "prior_date": "2026-10-01", "prior_revenue_cents": 1600, "prior_customers": 1,
                 "revenue_cents": 250, "revenue_pct": 15.6, "customers": 1, "reason": null }
    }
  }
}
```

## Mock for parallel work
Orlando builds P-O2 against the two example files. They are hand-written to this contract; the prior-day figures in them are invented.

## Open questions (default applies until answered)
- Revenue definition (Q5): net of refunds, fees separate. A change renames nothing; only `revenue_cents` and the `definitions` text change.
- Customer definition (Q6): buyers, falling back to orders.
- Comparison wanted (Q11): prior calendar day. Same day last week would add a second delta object, not change this one.
- Missing source (Q11): excluded from totals and shown as no data.
- `other` (Q9): `not_configured` until a source maps to it.
- Enterprise scope (Q12): e-commerce only.

## Changelog
- draft v0.1: initial. Field names follow `docs/HANDOFFS.md` (`*_cents`), which supersedes the shorter names in the P0 row of `docs/TASKS.md`; adds `gross_cents`, the `unknown` and `not_configured` statuses and the delta `reason`.
