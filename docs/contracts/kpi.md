# Contract: KPI file, phase 2 (task C2)

- **Owner:** Dani (`recon/kpi/`). **Consumers:** Orlando (scorecard page, print layout), Victor (KPI CSV, PDF and email exports; `kpi_values` in the store).
- **Status:** draft v0.4, implemented in `recon/kpi/`. The tests reproduce every example file from the calculator.
- **Inputs:** the store, `docs/contracts/store.md` (the SQLite database of decision 007): the daily pulse, the transactions and the internal API snapshots of the period. What is read from it is under "Inputs the KPIs read".

## What this contract does
Turns a period of stored nightly data into Goodwill's own scorecard (deck slide 35): **15 KPIs, five areas, three each**. The page, the PDF and the CSV all render this one file, so they cannot disagree, and none of them does arithmetic or decides what missing data means.

```
database (pulse_daily, transactions, internal_daily)
   └─> python -m recon.kpi --period month --month 2026-09  ─> out/kpi/month-2026-09.json   + latest-month.json
       python -m recon.kpi --period week  --week 2026-W38  ─> out/kpi/week-2026-W38.json   + latest-week.json
       python -m recon.kpi --period day   --date 2026-10-02 ─> out/kpi/day-2026-10-02.json + latest-day.json
                                                            ─> and the same numbers into kpi_values (see below)
```
- Options: `--db PATH` (default: the `ECOM_DB` environment variable, else `out/store/ecom.db`), `--out-dir` (default `out/kpi`), `--through YYYY-MM-DD` (see Period). Without `--date`, `--week` or `--month`, the period is the one containing the latest stored business date (`--period month` alone is "this month to date"). With one of them, `--period` may be left out.
- Re-running a period overwrites its file. `latest-<type>.json` is a copy of the file with the greatest period of that type.
- Exit code 0 whenever a file is written, including when KPIs are `partial` or `no_data`. Exit code 1 if the database is absent or unreadable, 2 if the options make no sense (a bad id, or no latest period in an empty database); nothing is written then.

## File
JSON, UTF-8. Money is integer USD cents. Examples, all in `examples/`: `kpi.sample.month.json` (September, complete), `kpi.sample.month.partial.json` (October to date, one eBay day missing), `kpi.sample.week.json` (the week of September 28, same gap) and `kpi.sample.day.json` (Sunday October 4, when nothing was listed).

### Top level
| Field | Type | Rule |
|---|---|---|
| `schema_version` | integer | `1`. |
| `generated_at` | datetime | ISO 8601 with offset. |
| `currency` | string | `"USD"`. |
| `period` | object | The period reported. See Period. |
| `prior_period` | object | The window every `prior_value` comes from. See Period. |
| `coverage` | object | How much of the period has marketplace data. See Coverage. |
| `internal_data` | object or null | `{ "source": "mock" \| "api", "label", "as_of" }`. `source` is `mock` unless every internal row of the period came from the real API. `label` is the badge text to print: "Simulated internal data" for `mock`, "Goodwill internal data" for `api`. `as_of` is the newest day with internal data. `null` if no internal data is stored for the period. |
| `areas` | object[] | Always five, in display order: `{ "id", "name" }` with ids `financial`, `productivity`, `inventory`, `sales`, `category_customer`. |
| `pillars` | object[] | Always five, in the order of slide 32: `{ "id", "name" }` with ids `growth`, `profitability`, `productivity`, `inventory`, `engagement`. See Pillars. |
| `kpis` | object[] | **Always exactly 15, in display order** (area by area, three per area, the order of the table below). |
| `definitions` | object | Keys `revenue`, `period`, `comparison`, `simulated`: sentences to print as is. Each KPI also carries its own `definition`. |

### Period
| Field | Type | Rule |
|---|---|---|
| `type` | enum | `day`, `week`, `month`. |
| `id` | string | `2026-10-02`, `2026-W38` (ISO week, Monday to Sunday), `2026-09`. |
| `label` | string | Text for the page title, for example `"September 2026"` or `"October 2026 (to date)"`. |
| `start`, `end` | date | First and last calendar day of the period. Business days are Eastern, as in the pulse. |
| `through` | date | Last day actually covered. Equals `end` if the latest stored business date is on or after `end`; otherwise it is that latest date (a period "to date"), or `start` if nothing is stored that late. `--through` overrides it. |
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
| `area` | enum | An `areas[].id`: where the KPI sits on the scorecard (slide 35). |
| `pillar` | enum | A `pillars[].id`: which pillar of the monthly dashboard (slide 32) it speaks to. See Pillars. |
| `name` | string | Goodwill's wording from slide 35. |
| `kind` | enum | `scalar` (one number) or `ranking` (a top 10 list). |
| `unit` | enum | `cents`, `ratio` (0.195 means 19.5%), `count`, `number` (one decimal), `days` (one decimal). |
| `per` | string or null | What the value is per: `"labor hour"`, `"employee"`, `"unit"`. Print as "$45.74 per labor hour". It follows `basis`: average selling price says `"order"` while it is computed per order. |
| `value` | number or null | The KPI. `null` when `status = no_data` and always `null` for a `ranking`. |
| `rows` | object[] or null | Only for a `ranking` (else `null`): up to 10 rows, largest first. See Rankings. `[]` when `no_data`. |
| `parts` | object[] or null | Only for a KPI that is shown as several boxes (else `null`). Today that is sell-through, always with two. See "Sell-through in two boxes". |
| `status` | enum | `ok`, `partial`, `no_data`. See Status. |
| `reason` | enum or null | Why it is not `ok`. `null` when `ok`. |
| `note` | string or null | One sentence to print under the number: what is missing, or which fallback definition was used. Can be set when `status = ok` (a fallback). |
| `basis` | string or null | Which variant of the definition was used, when there is more than one (see the table). |
| `covers` | string[] or null | Marketplaces the value covers, when it is not all of them. `null` = every marketplace with data. |
| `prior_value` | number or null | The same KPI over `prior_period`. `null` for a `ranking`, when it has no data there, and when it was computed on another `basis` (per order against per unit). |
| `delta` | object | Change against `prior_value`. See Delta. |
| `good_direction` | enum | `up` or `down`: which way is an improvement (backlog and days to list are `down`). For colouring the delta. |
| `source` | enum | `files` (marketplace exports only), `internal` (internal API only), `mixed`. |
| `simulated` | boolean | `true` when the value uses internal data and `internal_data.source` is `mock`. **Every simulated number must be badged** with `internal_data.label`. |
| `definition` | string | The definition actually used, as a sentence for the footnote. |
| `inputs` | object | The numbers the value was computed from (keys per KPI below). Every key is always there; one that could not be read is `null`. For tooltips, the CSV and audit; the renderer may ignore it. |

### Status
**No data is never 0.** A `0` only ever means a real zero.

| Status | Meaning | `value` |
|---|---|---|
| `ok` | Computed from complete data. | set |
| `partial` | Computed, but from incomplete data. Show it, flagged, with `note`. | set |
| `no_data` | Cannot be computed. Show "no data" and `note`. | `null` |

| `reason` | Status | When |
|---|---|---|
| `missing_days` | partial | A KPI that uses the marketplace files, and `coverage.complete` is false. For revenue growth also when the comparison window has gaps. |
| `missing_internal_days` | partial | Internal data is stored for only part of the period (for a snapshot KPI: the latest snapshot is older than `through`), or a category has no cost of goods (counted as zero). |
| `no_buyer_ids` | partial, or no_data | Some marketplaces give no buyer id; `covers` lists the ones that do. `no_data` when none does, or when no transactions are stored for the period. |
| `no_prior_period` | no_data | Revenue growth, when the comparison window has no marketplace data. |
| `no_internal_data` | no_data | The internal data this KPI needs is not stored for the period (or the donation ages are not whole days). |
| `no_marketplace_data` | no_data | No marketplace-day in the period is `ok`. |
| `zero_denominator` | no_data | The divisor is zero (no labor hours, no listings, no revenue). |
| `period_too_short` | no_data | Repeat buyer rate for a `day` period. |

If several apply, `status` is the worst of them, `reason` is the first reason of that status in this order, and `note` strings together the notes of that status. A fallback note ("Per order, not per unit...") comes last, and is dropped when there is no value.

### Delta
| Field | Type | Rule |
|---|---|---|
| `value` | number or null | `value - prior_value`, in the KPI's unit and rounded like it. For `ratio` it is a difference of ratios: 0.0465 is +4.65 percentage points. |
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
| 11 | `sales.sell_through` | Sell-Through Rate | ratio | up | mixed | units sold / units listed, in the period (one listing = one unit). Shown as two boxes, see below | `units_sold`, `orders`, `units_listed`, `opening_stock` |
| 12 | `sales.sales_per_employee` | Sales per Employee | cents per employee | up | mixed | revenue / average daily e-commerce employees | `revenue_cents`, `employees` |
| 13 | `cat.top_revenue` | Top 10 Categories by Revenue | ranking, cents | up | mixed | Revenue (KPI 1) split by the internal sales-by-category shares | `revenue_cents`, `internal_sales_cents`, `categories`, `rest_cents` |
| 14 | `cat.top_margin` | Top 10 Categories by Margin | ranking, cents | up | mixed | Category revenue (KPI 13) minus category cost of goods; `ratio` = margin / category revenue | `revenue_cents`, `cogs_cents`, `margin_cents`, `categories`, `rest_cents` |
| 15 | `cust.repeat_buyer_rate` | Repeat Buyer Rate | ratio | up | files | Buyers with two or more orders in the period / buyers, over sale rows that have a `customer_id` | `buyers`, `repeat_buyers`, `orders_with_buyer_id`, `orders` |

Variants (`basis`) and fallbacks, each stated in `definition` and `note`:
| KPI | `basis` | Meaning |
|---|---|---|
| 2 | `prior_period` (default), `year_over_year` | Slide 33 says year over year. We compare with the period before until 13 months are stored. |
| 10 | `per_unit`, `per_order` | `per_unit` when every sale row of the period has a unit count (they do since `transaction.md` v0.4); otherwise `per_order` (revenue / orders), with a note. |
| 11 | `units`, `orders` | Same rule: `orders` (orders / listings created) only when a sale row has no unit count. |
| 13, 14 | `internal_split`, `item_level` | `internal_split` today: the files carry no category, so the internal shares are applied to the files' revenue and the list adds up to KPI 1. `item_level` later, when each sale carries a category. |

**Sell-through in two boxes (KPI 11).** One rate hides two different things: how fast what was just listed sells, and how fast the stock left from before sells. Over a short period the single rate can even pass 100%, because older listings sell too (207.7% on the real run for Sunday October 4: 81 units sold, 39 listed). So the page shows two boxes, from `parts`:

| `parts[].id` | `name` | `value` | `sold` | `available` |
|---|---|---|---|---|
| `listed_in_period` | Listed in the period | `sold / available` | What sold, up to what was listed in the period | Listings created in the period |
| `left_from_earlier` | Left from earlier | `sold / available` | The rest of what sold | Listings still active the night before the period (`inputs.opening_stock`) |

- **The assumption, stated in `note`:** the data does not say which listing each sale came from, so what was listed in the period is taken to sell first. The first box is therefore the most the period's own listings can account for, and the second the least that came from older stock. The second box is 0 whenever no more sold than was listed. Exact figures need sales by listing date from the listing system (a metric to add to `internal-api.md`).
- The rule is applied to the period as a whole: a month's box 1 is "of what was listed this month, how much sold this month".
- There are always exactly two parts, in this order. A `value` is `null` when it cannot be computed: nothing listed in the period (first box), or no stock count for the day before the period (second box, `available` is `null` too). Without marketplace or listing data, both are `null`.
- `value` of the KPI itself stays the overall rate, uncapped (it is the one stored in `kpi_values` and compared with the prior period). The page shows the two boxes in its place.
- Real run, Sunday October 4: first box 100.0% (39 of 39), second box 1.2% (42 of the 3,519 left from earlier); note: "Assumes what was listed in the period sold first: 39 of the 81 units sold count against the 39 listed in the period, 42 against the 3,519 left from earlier."

Consistency rules: cost of goods in KPI 3 is the sum of the category cost of goods of KPI 14, so the two never disagree. KPIs 8 and 9 are snapshots on `through`; their `prior_value` is the snapshot on `prior_period.through`. KPI 15 uses `customer_id` even where the pulse counts customers by order (Upright keeps the buyer hash).

Rounding: cents and counts are integers; `ratio` has four decimals; `number` and `days` one decimal. Rounding happens once, on the final value.

### Pillars
Goodwill describes the dashboard twice: slide 32 asks it to balance five **pillars** (growth, profitability, productivity, inventory management, customer engagement), slide 35 lays the 15 KPIs out in five **areas**. The file keeps the areas as the layout and tags each KPI with its pillar, so the page can show both without holding a mapping of its own.

| Pillar | KPIs |
|---|---|
| Growth | `fin.revenue`, `fin.revenue_growth`, `sales.asp`, `cat.top_revenue` |
| Profitability | `fin.net_margin`, `cat.top_margin` |
| Productivity | `prod.listings_created`, `prod.revenue_per_labor_hour`, `prod.listings_per_employee`, `sales.sales_per_employee` |
| Inventory | `inv.days_donation_to_listing`, `inv.unlisted_backlog`, `inv.unsold_pct`, `sales.sell_through` (slide 36 calls it inventory velocity) |
| Engagement | `cust.repeat_buyer_rate` (the only customer KPI of the 15) |

## Example (one KPI, from `kpi.sample.month.partial.json`)
```json
{ "id": "fin.revenue", "area": "financial", "pillar": "growth", "name": "Total E-Commerce Revenue", "kind": "scalar",
  "unit": "cents", "per": null, "value": 981461, "rows": null,
  "status": "partial", "reason": "missing_days", "note": "eBay has no data on 2026-10-03, so this is partial.",
  "basis": null, "covers": null, "prior_value": 895886,
  "delta": { "value": 85575, "pct": 9.6, "reason": "partial_period" },
  "good_direction": "up", "source": "files", "simulated": false,
  "definition": "Sales minus refunds, before marketplace fees. Excludes shipping and tax.",
  "inputs": { "gross_cents": 986909, "refunds_cents": -5448, "fees_cents": 66661, "orders": 321 } }
```

## Inputs the KPIs read
The store is defined by `docs/contracts/store.md` (schema: `engine/store/schema.sql`) and the internal metrics by `docs/contracts/internal-api.md`; both took the names first asked for here. The calculator opens the database read-only and reads three tables. `recon/kpi/store.py` is the only module that knows their names, so reading from somewhere else (the files, if the store is late: the 10:00 tripwire in decision 007) means replacing one function.

| Table | Columns read | Notes |
|---|---|---|
| `pulse_daily` | `business_date`, `marketplace`, `status`, `gross_cents`, `refunds_cents`, `revenue_cents`, `fees_cents`, `orders` | **Required.** `other` counts only on a day it is `ok`; it is never an expected marketplace. |
| `transactions` | `business_date`, `marketplace`, `type`, `order_id`, `customer_id`, `units` | Sale rows only. Without the table, or for a period with no rows, KPI 15 is `no_data`; while `units` is NULL, KPIs 10 and 11 use their per-order variants. |
| `internal_daily` | `business_date`, `metric`, `dimension`, `value`, `source` | Without it every internal KPI is `no_data`. Also read for the day before the period: `active_listings_by_age`, the stock that sell-through's second box is measured against. |

The internal metrics read (a copy for convenience; `internal-api.md` is the authority). Flows are the day's amount; snapshots are the state at the end of the day:
| `metric` | `dimension` | Kind | Used by |
|---|---|---|---|
| `labor_hours` | `total` | flow | 5 |
| `labor_cost_cents` | `total` | flow | 3 |
| `employees` | `total` (full-time equivalents) | snapshot | 6, 12 |
| `listings_created` | marketplace | flow | 4, 6, 11 |
| `donation_to_listing_days` | whole days as text (`"0"`, `"1"`, ...); value = items listed that day with that age | flow | 7 (a median cannot be rebuilt from daily medians; it can from daily counts). A day on which nothing was listed has no rows, so KPI 7 is `no_data` only when the whole period has none |
| `unlisted_backlog` | `total` | snapshot | 8 |
| `active_listings_by_age` | `0-30`, `31-60`, `61-90`, `91+` | snapshot | 9, and 11 (the night before the period) |
| `shipping_net_cost_cents` | `total`: paid to carriers minus charged to buyers | flow | 3 |
| `category_sales_cents` | category | flow | 13, 14 |
| `category_cogs_cents` | category | flow | 3, 14 |

## History in the store (`kpi_values`)
After writing the file, the command records the same numbers in the store, by the rules of `store.md`: the period's rows are deleted and inserted again in one transaction, and a `runs` line with `command = 'kpi'` logs it. Re-running a period therefore replaces its rows.

| Column | From the file |
|---|---|
| `period_type`, `period_start` | `period.type`, `period.start` |
| `period_end` | `period.through`: the last day the values cover, so a period to date shows as one |
| `kpi_id` | `id` |
| `dimension` | `''` for a single value. For a ranking, one row per category with its `label` (a ranking without data is one row with `''` and a NULL value) |
| `value`, `unit`, `status`, `source` | As in the file; `value` is NULL when `no_data` |
| `computed_at` | `generated_at` |

If the table is missing (an older database), the file is still written, the command says so on stderr and exits 0. The two boxes of sell-through are not stored, only its overall value.

## Mock for parallel work
Orlando builds the scorecard against the four example files. **They are the calculator's output** on a test database, so the page and the calculator cannot disagree on shape: `python -m recon.tests.kpi_samples` rewrites them, and a test fails if they drift from the code. **What is real in them:** revenue, refunds, fees and orders are the answer keys of `data/sample/clean_month` (September) and of the four `day_*` scenarios (October 1 to 4, eBay missing on the 3rd). **What is invented:** every internal number, the buyers and the unit counts (one order in eight has two units). Three things are staged to show states: no donation dates in October (an internal `no_data`), no backlog snapshot on October 4 (an old snapshot), and no production on Sundays (real zeros and zero divisors).

| Example | States it shows |
|---|---|
| `kpi.sample.month.json` | `ok`; `no_data` / `no_prior_period` (growth, nothing stored for August); `partial` / `no_buyer_ids`; sell-through's second box without a stock count; every delta `no_prior_period` |
| `kpi.sample.month.partial.json` | A period to date; `partial` / `missing_days` and `missing_internal_days`; `no_data` / `no_internal_data`; deltas clean, `partial_period`, `current_no_data`, `not_applicable` |
| `kpi.sample.week.json` | A complete week with one gap: `missing_days`, `missing_internal_days`, clean deltas on the internal KPIs; both sell-through boxes with a value |
| `kpi.sample.day.json` | `no_data` / `period_too_short` (KPI 15), `zero_denominator` (KPIs 5 and 11: no labor hours, nothing listed), `no_internal_data`; real zeros that stay `ok` (KPIs 4 and 6); sell-through with nothing listed, so only its second box has a value; a clean value whose delta is `partial_period` because the day before had a gap |

To see any other period before the real database exists:
```
python -m recon.tests.kpi_samples --db out/store/ecom.db    # the same test database, September and October 1 to 4
python -m recon.kpi --period week                           # out/kpi/week-2026-W40.json
python -m recon.kpi --date 2026-10-03                       # a day with eBay missing
```

## Open questions (default applies until answered)
- Growth year over year or against the prior period (KPI 2): prior period, labelled.
- Does margin include labor and shipping (KPIs 3, 14): net margin includes both; category margin is revenue minus cost of goods only.
- What "unsold" means (KPI 9): active listings older than 30 days; the threshold is one constant.
- Which listings a sale came from (KPI 11): unknown, so the period's own listings are taken to sell first and the two boxes are bounds. The overall rate is sold / listed in the period and can exceed 1; the page must not assume a ratio stays under 100%.
- Who counts as an e-commerce employee (KPIs 6, 12): full-time equivalents, as the internal API reports them.
- Net shipping cost (KPI 3): carrier cost minus shipping charged to buyers, from the internal API until `transactions` carries shipping.

## Changelog
- draft v0.4: sell-through is shown as two boxes (Dani's decision): new field `parts` on every KPI (`null` except KPI 11), `inputs.opening_stock`, and the note now states the assumption. This replaces v0.3's `from_period`, `from_earlier` and `sold_from_earlier` inputs and its "100% + ..." note, which nobody used yet. The examples now carry unit counts, so average selling price and sell-through are on their per-unit basis, as on the real pipeline since `transaction.md` v0.4.
- draft v0.3: sell-through over 100% is split into what the period's own listings can account for and what must have been listed earlier: three more `inputs` on KPI 11 (`from_period`, `from_earlier`, `sold_from_earlier`) and a note when the value is over 1. Additive: no field changes meaning, and the value itself is unchanged.
- draft v0.2: implemented. The example files are now generated by the calculator (differences from v0.1: a few cents in the margin ranking, `inputs.items_listed` is `null` when there are no donation dates, a note now carries the gap sentence before a fallback sentence, and in the partial month the backlog snapshot is a day old). Two more examples, a week and a day, asked for by Orlando (C5). New fields `pillar` per KPI and `pillars` at the top level, asked for by Victor (slide 32's five pillars; mapping under Pillars). Inputs now point to `store.md` and `internal-api.md`; the KPIs are also recorded in `kpi_values`. Clarified: exit codes, `--period` alone, `through` when nothing is stored, `prior_value` across bases, `inputs` keys always present, how `status`, `reason` and `note` combine, `no_buyer_ids` as `no_data`, the `internal_data` label.
- draft v0.1: initial. Replaces the KPI list of `docs/pitch/kpi_catalog.md` and the rows produced by `reports/kpi.py` (decision 007).
