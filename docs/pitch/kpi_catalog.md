# KPI catalog (decision 005)

Five groups from the team sync. For each KPI: how it is defined, and where the data comes from.
- **Files**: computable today from the exports we parse (`data/sample/`, engine output).
- **Internal API (assumed)**: needs company data we don't have; served by the mock Goodwill internal API with synthetic values, and **labelled "simulated internal data" wherever shown**.

Build priority: **P1** = in the demo, **P2** = if time allows.

## Financial
| KPI | Definition | Source | Pri |
|---|---|---|---|
| Net revenue | Sales minus refunds, excl. shipping and tax (pulse definition) | Files | P1 |
| Marketplace fees % | Fees / net revenue, per marketplace | Files | P1 |
| Payout vs revenue | Cash received from marketplaces / net revenue; in-transit at month end | Files (messy month payouts + bank) | P1 |
| Gross margin | (Net revenue - cost of goods) / net revenue | Internal API (COGS per item or per category) | P2 |
| Shipping recovery | Shipping charged to buyers / shipping cost paid (FedEx) | Files (charged) + Internal API (FedEx cost from BC) | P2 |

## Listings & Production
| KPI | Definition | Source | Pri |
|---|---|---|---|
| Items listed per day | New listings per marketplace per day | Internal API (listing system) | P2 |
| Items listed per labor hour | Listings / production labor hours | Internal API (listings + labor) | P2 |
| Days to sell | Sale date - list date, median | Internal API (list dates) | P2 |

## Sales Effectiveness
| KPI | Definition | Source | Pri |
|---|---|---|---|
| Average order value | Net revenue / orders | Files | P1 |
| Refund rate | Refunded amount / sales | Files | P1 |
| Sell-through rate | Items sold / items listed in the period | Files (sold) + Internal API (listed) | P2 |

## Category Effectiveness
| KPI | Definition | Source | Pri |
|---|---|---|---|
| Revenue by category | Net revenue per category | Internal API (product master: SKU -> category); Upright and Cash Monkey files carry no category | P2 |
| Average price by category | Revenue / units per category | Internal API + Files | P2 |

## Customer & Marketplace
| KPI | Definition | Source | Pri |
|---|---|---|---|
| Orders and customers by marketplace | Pulse definitions, with `customer_basis` shown | Files | P1 |
| Marketplace share of revenue | Marketplace net revenue / enterprise | Files | P1 |
| Repeat buyer rate | Buyers with 2+ orders in the month / buyers (where a buyer id exists: ShopGoodwill via Upright, eBay seller report) | Files | P1 |
| Month-over-month growth | Net revenue vs prior month | Files (needs two months; September + October samples) | P2 |

## Mock internal API (what it must serve)
`GET /api/internal/cogs?month=`, `/labor-hours?month=`, `/listings?month=`, `/products` (SKU -> category). JSON, every response carries `"source": "mock"`. Synthetic values are generated from a seed next to `data/generate.py` so they are consistent with the sample orders (same SKUs).
