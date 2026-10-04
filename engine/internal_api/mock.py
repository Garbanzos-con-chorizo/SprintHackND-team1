"""Mock Goodwill internal API (docs/contracts/internal-api.md): company data we don't have.

Everything here is SYNTHETIC. Every response carries "source": "mock" and the label
"Simulated internal data", which must follow every number built on it. Values are seeded by
metric and date, so re-running a date gives the same numbers, and sized to the sample order
volume (about 75 orders and $2,300 of revenue a day) so the KPIs look plausible.

Two places look at our data, because the real API would know them and the mock can't: category
sales (the day's pulse revenue per marketplace, split with a seeded mix, `revenue_by_marketplace`), so
category totals add up to the revenue on the scorecard; and units sold by days since listing (the
day's units sold from the transactions, spread over ages, `units_sold`).
"""
import math
import random
from datetime import date
from typing import Callable

LABEL = "Simulated internal data"
ENDPOINTS = ["labor", "listings", "costs", "categories"]
MARKETPLACES = ["shopgoodwill", "ebay", "amazon"]
CATEGORIES = ["Collectibles", "Electronics", "Jewelry & Watches", "Books & Media", "Clothing & Shoes",
              "Home & Kitchen", "Toys & Games", "Art & Decor", "Sporting Goods", "Music & Instruments",
              "Tools & Hardware", "Bags & Accessories", "Video Games", "Antiques"]
# Share of each marketplace's revenue by category, in CATEGORIES order, before daily noise:
# auctions skew to collectibles and jewelry, eBay to clothing, Amazon is mostly books.
BASE_MIX = {
    "shopgoodwill": [.18, .12, .16, .04, .07, .10, .06, .07, .04, .04, .03, .04, .02, .03],
    "ebay":         [.10, .15, .06, .05, .22, .10, .07, .04, .05, .04, .04, .05, .02, .01],
    "amazon":       [.01, .03, .00, .82, .00, .03, .03, .00, .01, .02, .01, .00, .04, .00],
}
# Cost of goods (processing, materials, allocated overhead) as a share of sales, per category.
COGS_RATE = dict(zip(CATEGORIES, [.30, .45, .35, .20, .25, .30, .28, .30, .32, .38, .35, .27, .40, .33]))
AGE_BUCKETS = ["0-30", "31-60", "61-90", "91+"]
LISTINGS_PER_DAY = {"shopgoodwill": 62, "ebay": 38, "amazon": 24}
LABOR_HOURS_PER_DAY = 53.0
SHIPPING_NET_COST_PER_DAY = 11000  # cents: paid to carriers minus charged to buyers
ACTIVE_LISTINGS = 3700
UNLISTED_BACKLOG = 1800
WEEKDAY_FACTOR = [1.0, 1.0, 1.0, 1.0, 1.0, 0.6, 0.3]  # Monday..Sunday: production slows at the weekend

RevenueLookup = Callable[[str], dict[str, int | None]]
UnitsLookup = Callable[[str], int | None]


class MockInternalApi:
    """Same interface as HttpInternalApi: get(endpoint, day) -> response envelope."""
    source = "mock"

    def __init__(self, revenue_by_marketplace: RevenueLookup | None = None, units_sold: UnitsLookup | None = None):
        self.revenue_by_marketplace = revenue_by_marketplace or (lambda day: {})
        self.units_sold = units_sold or (lambda day: None)

    def get(self, endpoint: str, day: str) -> dict:
        handlers = {"labor": self._labor, "listings": self._listings, "costs": self._costs,
                    "categories": lambda d: {"category_sales_cents": self._category_sales(d)}}
        if endpoint not in handlers:
            raise KeyError(f"unknown endpoint {endpoint!r}; known: {', '.join(ENDPOINTS)}")
        return {"source": self.source, "label": LABEL, "endpoint": endpoint, "date": day,
                "data": handlers[endpoint](day)}

    def _labor(self, day: str) -> dict:
        r = rng("labor", day)
        hours = round(LABOR_HOURS_PER_DAY * weekday(day) * r.uniform(0.9, 1.1), 1)
        iso = date.fromisoformat(day).isocalendar()
        # headcount changes from week to week, not day to day
        employees = 9 + rng("employees", f"{iso.year}-W{iso.week}").choice([-1, 0, 0, 1])
        return {"labor_hours": hours, "labor_cost_cents": round(hours * r.uniform(17.25, 18.25) * 100),
                "employees": employees}

    def _listings(self, day: str) -> dict:
        r = rng("listings", day)
        created = {m: round(n * weekday(day) * r.uniform(0.85, 1.15)) for m, n in LISTINGS_PER_DAY.items()}
        ages: dict[str, int] = {}
        for _ in range(sum(created.values())):  # median about 6 days, a long tail of slow items
            age = str(min(120, round(r.gammavariate(1.6, 5.0))))
            ages[age] = ages.get(age, 0) + 1
        active = split(round(ACTIVE_LISTINGS * r.uniform(0.95, 1.05)),
                       [s * r.uniform(0.9, 1.1) for s in (.55, .22, .12, .11)])
        doy = date.fromisoformat(day).timetuple().tm_yday
        backlog = round(UNLISTED_BACKLOG + 150 * math.sin(doy / 9) + r.uniform(-60, 60))
        return {"listings_created": created,
                "donation_to_listing_days": dict(sorted(ages.items(), key=lambda kv: int(kv[0]))),
                "unlisted_backlog": backlog, "active_listings_by_age": dict(zip(AGE_BUCKETS, active)),
                "listing_to_sale_days": self._listing_to_sale(day)}

    def _listing_to_sale(self, day: str) -> dict[str, int]:
        """The day's units sold, by days since they were listed (for sell-through's two boxes, kpi.md).
        Auctions run about a week: few sell on the day they're listed, the median is about 6 days, and a
        tail sells weeks later. No sales that day (or no transactions stored) -> no rows."""
        units = self.units_sold(day) or 0
        r = rng("listing_to_sale", day)
        ages: dict[str, int] = {}
        for _ in range(units):
            age = str(min(120, round(r.gammavariate(2.0, 3.5))))
            ages[age] = ages.get(age, 0) + 1
        return dict(sorted(ages.items(), key=lambda kv: int(kv[0])))

    def _costs(self, day: str) -> dict:
        r = rng("costs", day)
        cogs = {c: round(cents * COGS_RATE[c] * r.uniform(0.95, 1.05))
                for c, cents in self._category_sales(day).items()}
        return {"shipping_net_cost_cents": round(SHIPPING_NET_COST_PER_DAY * weekday(day) * r.uniform(0.85, 1.15)),
                "category_cogs_cents": cogs}

    def _category_sales(self, day: str) -> dict[str, int]:
        """The day's revenue per marketplace split across categories; empty when no marketplace has data."""
        r = rng("categories", day)
        totals = dict.fromkeys(CATEGORIES, 0)
        revenue = {m: c for m, c in self.revenue_by_marketplace(day).items() if c is not None and m in BASE_MIX}
        if not revenue:
            return {}
        for m in MARKETPLACES:
            if m in revenue:
                for c, cents in zip(CATEGORIES, split(revenue[m], [s * r.uniform(0.85, 1.15) for s in BASE_MIX[m]])):
                    totals[c] += cents
        return totals


def rng(name: str, key: str) -> random.Random:
    return random.Random(f"{name}:{key}")


def weekday(day: str) -> float:
    return WEEKDAY_FACTOR[date.fromisoformat(day).weekday()]


def split(total: int, weights: list[float]) -> list[int]:
    """Whole numbers in proportion to `weights` that add up to `total` exactly (largest remainder)."""
    sign, total = (-1 if total < 0 else 1), abs(total)
    s = sum(weights)
    raw = [total * w / s for w in weights]
    out = [int(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[:total - sum(out)]:
        out[i] += 1
    return [sign * v for v in out]
