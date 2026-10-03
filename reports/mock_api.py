"""Mock Goodwill internal API (decision 005): company data we don't have.

Everything here is SYNTHETIC. Each response carries "source": "mock" and the label
"Simulated internal data", which every page must show next to numbers built on it.
Values are seeded by the period, so reruns match, and sized to the sample order volume
so they look plausible. In production each function becomes an HTTP call; the
docstring of each one names the endpoint it stands in for. Nothing here reads our
order files: the internal API would not know about them.
"""
import random
from datetime import date

LABEL = "Simulated internal data"
MARKETPLACES = ["shopgoodwill", "amazon", "ebay"]
CATEGORIES = ["Collectibles", "Electronics", "Jewelry & Watches", "Books & Media", "Clothing & Shoes",
              "Home & Kitchen", "Toys & Games"]
# Typical category mix per marketplace (before weekly noise): auctions skew to collectibles and
# jewelry, Amazon is mostly books.
BASE_MIX = {
    "shopgoodwill": [0.24, 0.16, 0.20, 0.06, 0.10, 0.16, 0.08],
    "ebay": [0.14, 0.18, 0.08, 0.06, 0.30, 0.14, 0.10],
    "amazon": [0.02, 0.04, 0.00, 0.88, 0.00, 0.03, 0.03],
}


def _rng(name, start, end):
    return random.Random(f"{name}:{start.isoformat()}:{end.isoformat()}")


def _days(start, end):
    return (end - start).days + 1


def _envelope(endpoint, start, end, **data):
    return {"source": "mock", "label": LABEL, "endpoint": endpoint,
            "from": start.isoformat(), "to": end.isoformat(), **data}


def labor_hours(start: date, end: date) -> dict:
    """GET /api/internal/labor-hours?from=&to= : e-commerce production hours by activity."""
    r = _rng("labor", start, end)
    per_day = {"processing_listing": 26.0, "photography": 9.0, "pick_pack_ship": 18.0}
    hours = {k: round(v * _days(start, end) * r.uniform(0.9, 1.1), 1) for k, v in per_day.items()}
    hours["total"] = round(sum(hours.values()), 1)
    return _envelope("/api/internal/labor-hours", start, end, hours=hours)


def listings(start: date, end: date) -> dict:
    """GET /api/internal/listings?from=&to= : new listings per marketplace and active at period end."""
    r = _rng("listings", start, end)
    per_day = {"shopgoodwill": 62, "ebay": 38, "amazon": 24}
    new = {m: round(n * _days(start, end) * r.uniform(0.85, 1.15)) for m, n in per_day.items()}
    active = {m: round(n * 30 * r.uniform(0.9, 1.1)) for m, n in per_day.items()}
    return _envelope("/api/internal/listings", start, end, new_listings=new, active_listings=active)


def cost_per_order(start: date, end: date) -> dict:
    """GET /api/internal/cost-per-order?from=&to= : average cost of goods sold per order, in cents
    (donated goods: processing, materials and allocated overhead), by marketplace."""
    r = _rng("cogs", start, end)
    base = {"shopgoodwill": 1150, "ebay": 820, "amazon": 540}
    return _envelope("/api/internal/cost-per-order", start, end,
                     cost_per_order_cents={m: round(c * r.uniform(0.93, 1.07)) for m, c in base.items()})


def category_mix(start: date, end: date) -> dict:
    """GET /api/internal/category-mix?from=&to= : share of each marketplace's revenue by category,
    as the product master (SKU -> category) would give it. Shares sum to 1 per marketplace."""
    r = _rng("mix", start, end)
    mix = {}
    for m, shares in BASE_MIX.items():
        noisy = [s * r.uniform(0.85, 1.15) for s in shares]
        total = sum(noisy)
        mix[m] = {c: round(s / total, 4) for c, s in zip(CATEGORIES, noisy)}
    return _envelope("/api/internal/category-mix", start, end, mix=mix)
