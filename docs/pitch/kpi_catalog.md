# KPI catalog: the 15 KPIs of the COO scorecard

Rewritten 2026-10-04 (task L7). The earlier version listed 34 KPIs in five groups of our own (decision 006); decision 007 replaced them with **Goodwill's own scorecard: 15 KPIs in five areas, three each (deck slide 35)**. This page is a reading aid for the presentation. The definitions that count are in `docs/contracts/kpi.md`; the code is `recon/kpi/`.

**Source** says where the number comes from:
- **Files**: the sales exports the engine parses. All sample data is synthetic.
- **Internal (simulated)**: Goodwill's internal data (labor hours, listings, stock, cost of goods), which we have never seen. A mock API stands in for it (`engine/internal_api/`), and the KPI is **badged "Simulated internal data"** on the page, in the CSV and in the PDF.
- **Mixed (simulated)**: revenue from the files combined with simulated internal data. Badged the same way.

**Pillar** is the one of slide 32's five (growth, profitability, productivity, inventory, engagement) each KPI speaks to. September values are from the scheduled run on the synthetic samples (`python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04`).

## Financial
| KPI | Definition | Pillar | Source | September (synthetic) |
|---|---|---|---|---|
| Total E-Commerce Revenue | Sales minus refunds, before marketplace fees. Excludes shipping and tax | Growth | Files | $70,753.96 |
| Revenue Growth % | Change in revenue against the period before, over the same number of days | Growth | Files | -33.3% (August is simulated: illustrative only) |
| Net Margin % | (Revenue - marketplace fees - cost of goods - net shipping cost - labor cost) / revenue | Profitability | Mixed (simulated) | 23.0% |

## Productivity
| KPI | Definition | Pillar | Source | September (synthetic) |
|---|---|---|---|---|
| Listings Created | New listings created in the period, all marketplaces | Productivity | Internal (simulated) | 3,120 |
| Revenue per Labor Hour | Revenue / e-commerce labor hours | Productivity | Mixed (simulated) | $51.93 |
| Listings per Employee | Listings created / average e-commerce employees (full-time equivalents) | Productivity | Internal (simulated) | 322.8 |

## Inventory
| KPI | Definition | Pillar | Source | September (synthetic) |
|---|---|---|---|---|
| Days from Donation to Listing | Median days between donation and listing, for items listed in the period | Inventory | Internal (simulated) | 6 days |
| Unlisted Inventory Backlog | Items sent to e-commerce and not yet listed, on the last day of the period | Inventory | Internal (simulated) | 1,720 |
| Unsold Inventory % | Active listings older than 30 days / active listings, on the last day of the period | Inventory | Internal (simulated) | 45.1% |

## Sales
| KPI | Definition | Pillar | Source | September (synthetic) |
|---|---|---|---|---|
| Average Selling Price | Revenue / units sold | Growth | Files | $28.67 |
| Sell-Through Rate | Units sold / units listed, in the period. Shown as two boxes: listed in the period, and left from earlier | Inventory | Mixed (simulated) | 79.1% (61.3% and 15.3%) |
| Sales per Employee | Revenue / average e-commerce employees (full-time equivalents) | Productivity | Mixed (simulated) | $7,319.38 |

## Category + Customer
| KPI | Definition | Pillar | Source | September (synthetic) |
|---|---|---|---|---|
| Top 10 Categories by Revenue | Revenue split by category using the internal sales-by-category shares, largest first | Growth | Mixed (simulated) | Books & Media, Collectibles, Electronics lead |
| Top 10 Categories by Margin | Category revenue minus category cost of goods, largest first | Profitability | Mixed (simulated) | Books & Media, Collectibles, Clothing & Shoes lead |
| Repeat Buyer Rate | Buyers with two or more orders in the period / buyers, where the marketplace gives a buyer id | Engagement | Files | 56.8%, marked partial: Amazon gives no buyer id |

## In one line
**4 KPIs from the sales files, 11 that need internal data and are simulated and badged.** No KPI shows $0 for missing data: a period without data reads "No data", and an incomplete one reads "partial" with the reason.

How to show them: `docs/pitch/demo_script_scorecard.md`.
