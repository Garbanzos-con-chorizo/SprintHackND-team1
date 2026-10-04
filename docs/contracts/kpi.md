# Contract: KPI file, phase 2 (task C2)

- **Owner:** Dani (`recon/kpi/`). **Consumers:** Orlando (scorecard page, print layout), Victor (KPI CSV, PDF and email exports).
- **Status:** draft
- **Inputs:** a period of stored nightly data: the daily pulse, the transactions and the internal API snapshots. **Where they are stored is not settled** (decision 007 proposes a SQLite database; Orlando's response to it proposes flat files). The KPI file below is the same either way; only "Inputs the KPIs need" and the `--db` option depend on it.

## What this contract does
Turns a period of stored nightly data into Goodwill's own scorecard (deck slide 35): **15 KPIs, five areas, three each**. The page, the PDF and the CSV all render this one file, so they cannot disagree, and none of them does arithmetic or decides what missing data means.

```
stored nightly data (daily pulse, transactions, internal snapshots)
   └─> python -m recon.kpi --period month --month 2026-09  ─> out/kpi/month-2026-09.json   + latest-month.json
       python -m recon.kpi --period week  --week 2026-W38  ─> out/kpi/week-2026-W38.json   + latest-week.json
       python -m recon.kpi --period day   --date 2026-10-02 ─> out/kpi/day-2026-10-02.json + latest-day.json
```
- Options: `--out-dir` (default `out/kpi`), `--through YYYY-MM-DD` (see Period), and where to read from: `--db PATH` with a database, or `--in-dir` (default `out`) with flat files.
- Re-running a period overwrites its file. `latest-<type>.json` is a copy of the file with the greatest period of that type.
- Exit code 0 whenever a file is written, including when KPIs are `partial` or `no_data`. Non-zero only if the stored data is absent or unreadable.

## File
JSON, UTF-8. Money is integer USD cents. Examples: `examples/kpi.sample.month.json` (September, complete) and `examples/kpi.sample.month.partial.json` (October to date, one eBay day missing).

### Top level
| Field | Type | Rule |
|---|---|---|
| `schema_version` | integer | `1`. |
| `generated_at` | datetime | ISO 8601 with offset. |
| `currency` | string | `"USD"`. |
| `period` | object | The period reported. See Period. |
| `prior_period` | object | The window every `prior_value` comes from. See Period. |
| `coverage` | object | How much of the period has marketplace data. See Coverage. |
| `internal_data` | object or null | `{ "source": "mock" \| "api", "label", "as_of" }`. `label` is the badge text to print ("Simulated internal data" while `source` is `mock`). `null` if no internal data is stored for the period. |
| `areas` | object[] | Always five, in display order: `{ "id", "name" }` with ids `financial`, `productivity`, `inventory`, `sales`, `category_customer`. |
| `kpis` | object[] | **Always exactly 15, in display order** (area by area, three per area, the order of the table below). |
| `definitions` | object | Keys `revenue`, `period`, `comparison`, `simulated`: sentences to print as is. Each KPI also carries its own `definition`. |

### Period
| Field | Type | Rule |
|---|---|---|
| `type` | enum | `day`, `week`, `month`. |
| `id` | string | `2026-10-02`, `2026-W38` (ISO week, Monday to Sunday), `2026-09`. |
| `label` | string | Text for the page title, for example `"September 2026"` or `"October 2026 (to date)"`. |
| `start`, `end` | date | First and last calendar day of the period. Business days are Eastern, as in the pulse. |
| `through` | date | Last day actually covered. Equals `end` if the latest stored business date is on or after `end`; otherwise it is that latest date (a period "to date"). `--through` overrides it. |
| `days` | integer | Days from `start` to `through`. |
| `complete` | boolean | `through == end`. |

`prior_period` is the period before, **over the same number of days**: the whole prior period when `complete`, otherwise its first `days` days (October 1 to 4 is compared with September 1 to 4). Fields: `id`, `label`, `start`, `through`, `days`, and `available` (`false` if no pulse is stored for that window).

### Coverage
Counts over `start`..`through` for the expected marketplaces (`shopgoodwill`, `amazon`, `ebay`; `other` is not configured, as in the pulse).

| Field | Type | Rule |
|---|---|---|
| `days_expected` | integer | Same as `period.days`. |
| `days_complete` | integer | Days where every expected marketplace is `ok`. |
| `days_partial` | integer | Days where some, not all, are `ok`. |
| `days_missing` | integer | Days where none is `ok`, including days never loaded. |
| `by_marketplace` | object | Days with `ok` data per marketplace. |
| `gaps` | object[] | `{ "date", "marketplace", "status" }` for each marketplace-day that is not `ok`. `status` is the pulse status, or `not_loaded` if the day has no pulse row. |
| `complete` | boolean | `gaps` is empty. |

### `kpis[]`
Every KPI has every key, so the renderer needs no existence checks.

| Field | Type | Rule |
|---|---|---|
| `id` | string | Stable id from the table below. |
| `area` | enum | An `areas[].id`. |
| `name` | string | Goodwill's wording from slide 35. |
| `kind` | enum | `scalar` (one number) or `ranking` (a top 10 list). |
| `unit` | enum | `cents`, `ratio` (0.195 means 19.5%), `count`, `number` (one decimal), `days` (one decimal). |
| `per` | string or null | What the value is per: `"labor hour"`, `"employee"`, `"unit"`. Print as "$45.74 per labor hour". It follows `basis`: average selling price says `"order"` while it is computed per order. |
| `value` | number or null | The KPI. `null` when `status = no_data` and always `null` for a `ranking`. |
| `rows` | object[] or null | Only for a `ranking` (else `null`): up to 10 rows, largest first. See Rankings. `[]` when `no_data`. |
| `status` | enum | `ok`, `partial`, `no_data`. See Status. |
| `reason` | enum or null | Why it is not `ok`. `null` when `ok`. |
| `note` | string or null | One sentence to print under the number: what is missing, or which fallback definition was used. Can be set when `status = ok` (a fallback). |
| `basis` | string or null | Which variant of the definition was used, when there is more than one (see the table). |
| `covers` | string[] or null | Marketplaces the value covers, when it is not all of them. `null` = every marketplace with data. |
| `prior_value` | number or null | The same KPI over `prior_period`. `null` for a `ranking`. |
| `delta` | object | Change against `prior_value`. See Delta. |
| `good_direction` | enum | `up` or `down`: which way is an improvement (backlog and days to list are `down`). For colouring the delta. |
| `source` | enum | `files` (marketplace exports only), `internal` (internal API only), `mixed`. |
| `simulated` | boolean | `true` when the value uses internal data and `internal_data.source` is `mock`. **Every simulated number must be badged** with `internal_data.label`. |
| `definition` | string | The definition actually used, as a sentence for the footnote. |
| `inputs` | object | The numbers the value was computed from (keys per KPI below). For tooltips, the CSV and audit; the renderer may ignore it. |

### Status
**No data is never 0.** A `0` only ever means a real zero.

| Status | Meaning | `value` |
|---|---|---|
| `ok` | Computed from complete data. | set |
| `partial` | Computed, but from incomplete data. Show it, flagged, with `note`. | set |
| `no_data` | Cannot be computed. Show "no data" and `note`. | `null` |

| `reason` | Status | When |
|---|---|---|
| `missing_days` | partial | A KPI that uses the marketplace files, and `coverage.complete` is false. |
| `missing_internal_days` | partial | Internal data is stored for only part of the period (for a snapshot KPI: the latest snapshot is older than `through`). |
| `no_buyer_ids` | partial | Some marketplaces give no buyer id; `covers` lists the ones that do. |
| `no_prior_period` | no_data | Revenue growth, when `prior_period.available` is false. |
| `no_internal_data` | no_data | The internal data this KPI needs is not stored for the period. |
| `no_marketplace_data` | no_data | No marketplace-day in the period is `ok`. |
| `zero_denominator` | no_data | The divisor is zero (no labor hours, no listings, no revenue). |
| `period_too_short` | no_data | Repeat buyer rate for a `day` period. |

If several apply, `reason` is the first in this order and `note` names them all.

### Delta
| Field | Type | Rule |
|---|---|---|
| `value` | number or null | `value - prior_value`, in the KPI's unit. For `ratio` it is a difference of ratios: 0.0465 is +4.65 percentage points. |
| `pct` | number or null | Percent change, one decimal. `null` for `ratio` KPIs and when `prior_value` is zero or negative. |
| `reason` | enum or null | `null` when the comparison is clean. |

| `delta.reason` | `value`, `pct` | Meaning |
|---|---|---|
| `null` | set | Both periods `ok`. |
| `partial_period` | **set** | One of the two is `partial`. Show the change with a warning. (Unlike the pulse, which blanks the delta: over a month a single missing day would otherwise hide every comparison.) |
| `no_prior_period` | null | `prior_value` is `null`. |
| `current_no_data` | null | `value` is `null`. |
| `not_applicable` | null | Rankings have no delta. |

### Rankings
`rows[]`: `{ "rank", "label", "value", "share", "ratio" }`. `value` is in the KPI's `unit`. `share` is the row's part of the total over **all** categories, not only the ten shown. `ratio` is `null` for revenue; for margin it is margin / that category's revenue. `inputs.categories` is how many categories exist and `inputs.rest_cents` what the ones below the top 10 add up to, so `sum(rows.value) + rest_cents` equals the total.

## The 15 KPIs
| # | `id` | Name | Unit | Good | Source | Formula | `inputs` |
|---|---|---|---|---|---|---|---|
| 1 | `fin.revenue` | Total E-Commerce Revenue | cents | up | files | Sum of `revenue_cents` over the `ok` marketplace-days (pulse definition: sales minus refunds, no shipping, no tax, fees not subtracted) | `gross_cents`, `refunds_cents`, `fees_cents`, `orders` |
| 2 | `fin.revenue_growth` | Revenue Growth % | ratio | up | files | (revenue - prior revenue) / prior revenue | `revenue_cents`, `prior_revenue_cents` |
| 3 | `fin.net_margin` | Net Margin % | ratio | up | mixed | (revenue - marketplace fees - cost of goods - net shipping cost - labor cost) / revenue | `revenue_cents`, `fees_cents`, `cogs_cents`, `shipping_net_cost_cents`, `labor_cost_cents`, `net_profit_cents` |
| 4 | `prod.listings_created` | Listings Created | count | up | internal | New listings in the period | `by_marketplace` |
| 5 | `prod.revenue_per_labor_hour` | Revenue per Labor Hour | cents per labor hour | up | mixed | revenue / e-commerce labor hours | `revenue_cents`, `labor_hours` |
| 6 | `prod.listings_per_employee` | Listings per Employee | number per employee | up | internal | listings created / average daily e-commerce employees (full-time equivalents) | `listings_created`, `employees` |
| 7 | `inv.days_donation_to_listing` | Days from Donation to Listing | days | down | internal | Median of (list date - donation date) over items listed in the period | `items_listed` |
| 8 | `inv.unlisted_backlog` | Unlisted Inventory Backlog | count | down | internal | Items sent to e-commerce and not yet listed, on `through` | `as_of` |
| 9 | `inv.unsold_pct` | Unsold Inventory % | ratio | down | internal | Active listings older than 30 days / active listings, on `through` | `as_of`, `active_listings`, `active_over_threshold`, `threshold_days` |
| 10 | `sales.asp` | Average Selling Price | cents per unit | up | files | revenue / units sold | `revenue_cents`, `units`, `orders` |
| 11 | `sales.sell_through` | Sell-Through Rate | ratio | up | mixed | units sold / units listed, in the period (one listing = one unit) | `units_sold`, `orders`, `units_listed` |
| 12 | `sales.sales_per_employee` | Sales per Employee | cents per employee | up | mixed | revenue / average daily e-commerce employees | `revenue_cents`, `employees` |
| 13 | `cat.top_revenue` | Top 10 Categories by Revenue | ranking, cents | up | mixed | Revenue (KPI 1) split by the internal sales-by-category shares | `revenue_cents`, `internal_sales_cents`, `categories`, `rest_cents` |
| 14 | `cat.top_margin` | Top 10 Categories by Margin | ranking, cents | up | mixed | Category revenue (KPI 13) minus category cost of goods; `ratio` = margin / category revenue | `revenue_cents`, `cogs_cents`, `margin_cents`, `categories`, `rest_cents` |
| 15 | `cust.repeat_buyer_rate` | Repeat Buyer Rate | ratio | up | files | Buyers with two or more orders in the period / buyers, over sale rows that have a `customer_id` | `buyers`, `repeat_buyers`, `orders_with_buyer_id`, `orders` |

Variants (`basis`) and fallbacks, each stated in `definition` and `note`:
| KPI | `basis` | Meaning |
|---|---|---|
| 2 | `prior_period` (default), `year_over_year` | Slide 33 says year over year. We compare with the period before until 13 months are stored. |
| 10 | `per_unit`, `per_order` | `per_order` (revenue / orders) until `transactions` carries `units`. |
| 11 | `units`, `orders` | `orders` (orders / listings created) until `units` exists. |
| 13, 14 | `internal_split`, `item_level` | `internal_split` today: the files carry no category, so the internal shares are applied to the files' revenue and the list adds up to KPI 1. `item_level` later, when each sale carries a category. |

Consistency rules: cost of goods in KPI 3 is the sum of the category cost of goods of KPI 14, so the two never disagree. KPIs 8 and 9 are snapshots on `through`; their `prior_value` is the snapshot on `prior_period.through`. KPI 15 uses `customer_id` even where the pulse counts customers by order (Upright keeps the buyer hash).

Rounding: cents and counts are integers; `ratio` has four decimals; `number` and `days` one decimal. Rounding happens once, on the final value.

## Example (one KPI, from `kpi.sample.month.partial.json`)
```json
{ "id": "fin.revenue", "area": "financial", "name": "Total E-Commerce Revenue", "kind": "scalar",
  "unit": "cents", "per": null, "value": 981461, "rows": null,
  "status": "partial", "reason": "missing_days", "note": "eBay has no data on 2026-10-03, so this is partial.",
  "basis": null, "covers": null, "prior_value": 895886,
  "delta": { "value": 85575, "pct": 9.6, "reason": "partial_period" },
  "good_direction": "up", "source": "files", "simulated": false,
  "definition": "Sales minus refunds, before marketplace fees. Excludes shipping and tax.",
  "inputs": { "gross_cents": 986909, "refunds_cents": -5448, "fees_cents": 66661, "orders": 321 } }
```

## Inputs the KPIs need (request to Victor: storage and `internal-api.md`)
The same data is needed whichever storage the team picks. With the database of decision 007 these are the tables `pulse_daily`, `transactions` and `internal_daily`; with flat files they are `out/pulse/<date>.json`, the transactions of the period and `out/internal/<date>.json`.

From the marketplace side, already defined by `transaction.md` and `pulse.md`:
- The daily pulse, every day of the period: per marketplace `status`, `gross_cents`, `refunds_cents`, `revenue_cents`, `fees_cents`, `orders`. Already kept as `out/pulse/<date>.json`.
- **The transactions of the whole period**, not only the last run: `business_date`, `marketplace`, `type`, `order_id`, `customer_id`, and `units` when it exists. KPI 15 (repeat buyers) and the per-unit variants of KPIs 10 and 11 cannot be computed from the pulse. Today each run writes its own `transactions.csv`, so nothing holds a month of them yet; this is the one input that needs new storage in either option.

From the internal API, one snapshot per night with these values (`business_date`, `metric`, `dimension`, `value`, `source`). Flows are the day's amount; snapshots are the state at the end of the day.
| `metric` | `dimension` | Kind | Used by |
|---|---|---|---|
| `labor_hours` | `total` (activities optional) | flow | 5 |
| `labor_cost_cents` | `total` | flow | 3 |
| `employees` | `total` (full-time equivalents) | snapshot | 6, 12 |
| `listings_created` | marketplace | flow | 4, 6, 11 |
| `donation_to_listing_days` | whole days as text (`"0"`, `"1"`, ...); value = items listed that day with that age | flow | 7 (a median cannot be rebuilt from daily medians; it can from daily counts) |
| `unlisted_backlog` | `total` | snapshot | 8 |
| `active_listings_by_age` | `0-30`, `31-60`, `61-90`, `91+` | snapshot | 9 |
| `shipping_net_cost_cents` | `total`: paid to carriers minus charged to buyers | flow | 3 |
| `category_sales_cents` | category | flow | 13, 14 |
| `category_cogs_cents` | category | flow | 3, 14 |

## Mock for parallel work
Orlando builds the scorecard against the two example files. They follow this contract and their arithmetic is consistent (the top 10 adds up to revenue, the deltas match the values). **What is real in them:** revenue, refunds, fees and orders are the answer keys of `data/sample/clean_month` (September, and September 1 to 4 as the comparison) and of the four `day_*` scenarios (October 1 to 4, eBay missing on the 3rd). **What is invented:** every internal number, the buyer counts, and the missing donation dates in the partial file (there to show an internal `no_data`).

States the two files cover: `ok`; `partial` with `missing_days` and with `no_buyer_ids`; `no_data` with `no_prior_period` and `no_internal_data`; a fallback `basis` with a note; a period to date; deltas that are clean, `partial_period`, `no_prior_period`, `current_no_data` and `not_applicable`.

## Open questions (default applies until answered)
- Growth year over year or against the prior period (KPI 2): prior period, labelled.
- Does margin include labor and shipping (KPIs 3, 14): net margin includes both; category margin is revenue minus cost of goods only.
- What "unsold" means (KPI 9): active listings older than 30 days; the threshold is one constant.
- Who counts as an e-commerce employee (KPIs 6, 12): full-time equivalents, as the internal API reports them.
- Net shipping cost (KPI 3): carrier cost minus shipping charged to buyers, from the internal API until `transactions` carries shipping.

## Changelog
- draft v0.1: initial. Replaces the KPI list of `docs/pitch/kpi_catalog.md` and the rows produced by `reports/kpi.py` (decision 007).
