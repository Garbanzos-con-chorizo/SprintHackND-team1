# Contract: Goodwill internal API (mock today) and its daily snapshot

- **Owner:** Victor (`engine/internal_api/`). **Consumers:** Dani (`recon/kpi/`, reads the snapshot from the store), Orlando (badges).
- **Status:** draft v0.4: client, mock and `pull` built (`engine/internal_api/`). The metric list is the one Dani asked for in `docs/contracts/kpi.md` ("Inputs the KPIs need"), names and dimensions unchanged.
- **Why it exists:** 11 of the 15 KPIs need company data we don't have (labor, employees, listings, inventory, costs, categories). Decision 006 point 9 and `docs/ASSUMPTIONS.md` 2b assume Goodwill exposes it through an internal API. We have never seen one, so we build a **mock with synthetic values** behind a client interface; a real API replaces the mock without changing anything downstream.

```
engine.internal_api (mock | http client) ──> python -m engine.internal_api pull --date D ──> store: internal_daily
                                                                                    (docs/contracts/store.md)
```

## Rules
- **Every value from the mock is simulated.** Each response says `"source": "mock"` and carries the label `"Simulated internal data"`. Each stored row keeps `source = 'mock'`, and every KPI built on one of them must be badged on the page, in the CSV and in the PDF.
- The mock is **deterministic**: seeded by metric and date, so re-running a date gives the same numbers.
- A real internal API would report **current state only**. That's why the nightly run stores a snapshot. The mock also answers for past dates, so `backfill` can fill September.
- The KPIs read **only the store** (`internal_daily`), never the API or the mock directly.
- **Category sales add up to the files' revenue.** A real API would take category sales from the product master. The mock can't know those, so `pull` splits the day's `pulse_daily` revenue (marketplaces with `status = 'ok'`) across categories with a seeded mix per marketplace. That is why `pull` runs after `store load` for the same date. On a day with no pulse there are no category rows (no data, not 0).

## Endpoints (the shape a real API is assumed to have)
`GET <base>/api/internal/<endpoint>?date=YYYY-MM-DD` returns:
```json
{ "source": "mock", "label": "Simulated internal data", "endpoint": "labor", "date": "2026-09-14",
  "data": { "labor_hours": 53.6, "labor_cost_cents": 106400, "employees": 9 } }
```
| Endpoint | `data` fields -> stored metrics |
|---|---|
| `labor` | `labor_hours`, `labor_cost_cents`, `employees` |
| `listings` | `listings_created` by marketplace, `active_listings_by_age` by age bucket, `unlisted_backlog`, `donation_to_listing_days` (days -> items), `listing_to_sale_days` (days -> units sold) |
| `costs` | `shipping_net_cost_cents`, `category_cogs_cents` by category |
| `categories` | `category_sales_cents` by category |

Python interface (`engine/internal_api/`): `get(endpoint, day) -> dict` with two implementations, `MockInternalApi` (default) and `HttpInternalApi` (base URL from `INTERNAL_API_URL`). The setting `INTERNAL_API=mock|http` picks one (`make_client`). `snapshot_rows(api, day)` turns the four responses into `internal_daily` rows (63 a day with the mock). `HttpInternalApi` is tested only against a local stand-in server that answers with the mock, since we have no real API.

`reports/mock_api.py` (Orlando's first mock: by period, 4 functions) and `reports/kpi.py`, the only code that used it, were deleted on 2026-10-04 (L6) once the weekly page read Dani's KPI file (D2.11).

## Stored metrics (`internal_daily`)
One row per `(business_date, metric, dimension)`. **Flow** metrics are the day's amount; to get a period, sum them. **Snapshot** metrics are the state at the end of that day; for a period, take the last day (or the average for `employees`). A single-value metric uses `dimension = 'total'`. A metric never has both a `total` row and detail rows, so summing never double-counts.

| `metric` | `dimension` | Kind | `unit` | Used by KPI |
|---|---|---|---|---|
| `labor_hours` | `total` | flow | `hours` | 5 |
| `labor_cost_cents` | `total` | flow | `cents` | 3 |
| `employees` | `total` (full-time equivalents) | snapshot | `fte` | 6, 12 |
| `listings_created` | marketplace | flow | `listings` | 4, 6, 11 |
| `donation_to_listing_days` | whole days as text (`"0"`, `"1"`, ...); value = items listed that day with that age | flow | `items` | 7 (an exact median from the summed counts) |
| `listing_to_sale_days` | whole days as text; value = units sold that day that had been listed that many days before | flow | `items` | 11, sell-through's two boxes (kpi.md "Sell-through in two boxes") |
| `unlisted_backlog` | `total` | snapshot | `items` | 8 |
| `active_listings_by_age` | `0-30`, `31-60`, `61-90`, `91+` (days listed) | snapshot | `listings` | 9 |
| `shipping_net_cost_cents` | `total`: paid to carriers minus charged to buyers | flow | `cents` | 3 |
| `category_sales_cents` | category | flow | `cents` | 13, 14 |
| `category_cogs_cents` | category | flow | `cents` | 3, 14 |

**Categories (14, so a top 10 means something):** Collectibles, Electronics, Jewelry & Watches, Books & Media, Clothing & Shoes, Home & Kitchen, Toys & Games, Art & Decor, Sporting Goods, Music & Instruments, Tools & Hardware, Bags & Accessories, Video Games, Antiques. **Marketplaces:** `shopgoodwill`, `ebay`, `amazon` (as in `pulse_daily`).

## Not covered (say so if asked)
- Real endpoint names, auth, paging: unknown, so the HTTP client is a guess.
- Cost of goods for donated items is a seeded share of category sales. Goodwill may track processing cost per item instead; that changes only the mock, not this table or the KPI file.

## Changelog
- draft v0.5 (2026-10-04, Victor): `listing_to_sale_days`, asked by Dani. The mock spreads the day's units sold, read from the store's sale rows (an order without a unit count counts once), over ages with a seeded distribution (median about 6 days, few on day 0). There are no rows on a day without sales. `store backfill` also pulls the snapshot of the day before its range, so sell-through's "left from earlier" box has its stock count.
- draft v0.4 (2026-10-04, Victor): `python -m engine.internal_api pull (--date D | --from D1 --to D2)` built. It writes `internal_daily` per date (delete then insert, one transaction, a failed pull changes nothing), logs a `pull` run, and says when there's no pulse for the date (no category rows). `store backfill` pulls each day after loading it.
- draft v0.3 (2026-10-04, Victor): built. Seeded sizes: about 53 labor hours a day at $17.25-18.25 an hour, 9 FTE plus or minus 1 (changes by ISO week), 124 listings a day (less at the weekend), donation-to-listing median about 6 days, 3,700 active listings, 1,800 unlisted, shipping net cost about $110 a day, cost of goods 20-45% of sales by category. On September (`clean_month`) that gives revenue per labor hour about $52 and net margin about 23%.
- draft v0.2 (2026-10-03, Victor): metric names, dimensions and kinds switched to Dani's list in `kpi.md` (`employees`, `donation_to_listing_days`, `active_listings_by_age`, `shipping_net_cost_cents`, `category_sales_cents`, `category_cogs_cents`; single values use `dimension = 'total'`). Category sales are scaled to the pulse revenue.
- draft v0.1 (2026-10-03, Victor): initial, from `docs/PLAN_PHASE_2_3.md` section 5. Replaces the four functions of `reports/mock_api.py`, which move into `engine/internal_api/`.
