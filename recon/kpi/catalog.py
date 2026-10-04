"""The 15 scorecard KPIs (deck slide 35) in display order: ids, names, units and default definitions,
and the pillar of the monthly dashboard (deck slide 32) each one speaks to."""
from dataclasses import dataclass

AREAS = (
    ("financial", "Financial"),
    ("productivity", "Productivity"),
    ("inventory", "Inventory"),
    ("sales", "Sales"),
    ("category_customer", "Category + Customer"),
)

# Slide 32: "balance growth, profitability, productivity, inventory management and customer engagement".
PILLARS = (
    ("growth", "Growth"),
    ("profitability", "Profitability"),
    ("productivity", "Productivity"),
    ("inventory", "Inventory"),
    ("engagement", "Engagement"),
)
PILLAR = {
    "fin.revenue": "growth", "fin.revenue_growth": "growth", "sales.asp": "growth", "cat.top_revenue": "growth",
    "fin.net_margin": "profitability", "cat.top_margin": "profitability",
    "prod.listings_created": "productivity", "prod.revenue_per_labor_hour": "productivity",
    "prod.listings_per_employee": "productivity", "sales.sales_per_employee": "productivity",
    "inv.days_donation_to_listing": "inventory", "inv.unlisted_backlog": "inventory", "inv.unsold_pct": "inventory",
    "sales.sell_through": "inventory",
    "cust.repeat_buyer_rate": "engagement",
}


@dataclass(frozen=True)
class Kpi:
    id: str
    area: str
    name: str  # Goodwill's wording
    kind: str  # scalar | ranking
    unit: str  # cents | ratio | count | number | days
    per: str | None
    good_direction: str  # up | down
    source: str  # files | internal | mixed
    definition: str


KPIS = (
    Kpi("fin.revenue", "financial", "Total E-Commerce Revenue", "scalar", "cents", None, "up", "files",
        "Sales minus refunds, before marketplace fees. Excludes shipping and tax."),
    Kpi("fin.revenue_growth", "financial", "Revenue Growth %", "scalar", "ratio", None, "up", "files",
        "Change in revenue against the comparison period."),
    Kpi("fin.net_margin", "financial", "Net Margin %", "scalar", "ratio", None, "up", "mixed",
        "(Revenue - marketplace fees - cost of goods - net shipping cost - labor cost) / revenue."),
    Kpi("prod.listings_created", "productivity", "Listings Created", "scalar", "count", None, "up", "internal",
        "New listings created in the period, all marketplaces."),
    Kpi("prod.revenue_per_labor_hour", "productivity", "Revenue per Labor Hour", "scalar", "cents", "labor hour",
        "up", "mixed", "Revenue / e-commerce labor hours."),
    Kpi("prod.listings_per_employee", "productivity", "Listings per Employee", "scalar", "number", "employee",
        "up", "internal", "Listings created / average e-commerce employees (full-time equivalents)."),
    Kpi("inv.days_donation_to_listing", "inventory", "Days from Donation to Listing", "scalar", "days", None,
        "down", "internal", "Median days between donation and listing, for items listed in the period."),
    Kpi("inv.unlisted_backlog", "inventory", "Unlisted Inventory Backlog", "scalar", "count", None, "down",
        "internal", "Items sent to e-commerce and not yet listed, on the last day of the period."),
    Kpi("inv.unsold_pct", "inventory", "Unsold Inventory %", "scalar", "ratio", None, "down", "internal",
        "Active listings older than 30 days / active listings, on the last day of the period."),
    Kpi("sales.asp", "sales", "Average Selling Price", "scalar", "cents", "unit", "up", "files",
        "Revenue / units sold."),
    Kpi("sales.sell_through", "sales", "Sell-Through Rate", "scalar", "ratio", None, "up", "mixed",
        "Units sold / units listed, in the period."),
    Kpi("sales.sales_per_employee", "sales", "Sales per Employee", "scalar", "cents", "employee", "up", "mixed",
        "Revenue / average e-commerce employees (full-time equivalents)."),
    Kpi("cat.top_revenue", "category_customer", "Top 10 Categories by Revenue", "ranking", "cents", None, "up",
        "mixed", "Revenue split by category using the internal sales-by-category shares, largest first."),
    Kpi("cat.top_margin", "category_customer", "Top 10 Categories by Margin", "ranking", "cents", None, "up",
        "mixed", "Category revenue minus category cost of goods, largest first, with margin as a share of "
        "category revenue."),
    Kpi("cust.repeat_buyer_rate", "category_customer", "Repeat Buyer Rate", "scalar", "ratio", None, "up", "files",
        "Buyers with two or more orders in the period / buyers, where the marketplace gives a buyer id."),
)

DEFINITIONS = {
    "revenue": "Sales minus refunds, before marketplace fees. Excludes shipping and tax.",
    "period": "Business days in Eastern time. Weeks run Monday to Sunday.",
    "comparison": "The period before, over the same number of days.",
    "simulated": "Numbers marked as simulated use a mock of Goodwill's internal systems, not Goodwill's real figures.",
}
