"""What is stored for one window, summed up once for all 15 KPIs. Pure functions."""
import math
from dataclasses import dataclass

from . import periods

EXPECTED = ("shopgoodwill", "amazon", "ebay")  # `other` is not configured, as in the pulse
MARKETPLACES = (*EXPECTED, "other")
LABELS = {"shopgoodwill": "ShopGoodwill", "amazon": "Amazon", "ebay": "eBay", "other": "Other"}
SUMS = ("gross_cents", "refunds_cents", "revenue_cents", "fees_cents", "orders")


class Internal:
    """The internal API snapshots of a window (rows of internal_daily)."""

    def __init__(self, rows):
        self._days = {}  # metric -> day -> {dimension: value}
        for r in rows:
            self._days.setdefault(r.metric, {}).setdefault(r.business_date, {})[r.dimension] = r.value
        # Simulated unless every row came from the real API.
        self.source = None if not rows else "api" if all(r.source == "api" for r in rows) else "mock"
        self.as_of = max((r.business_date for r in rows), default=None)

    def days_with(self, metric):
        return len(self._days.get(metric, {}))

    def flow(self, metric):
        """Sum per dimension over the window."""
        parts = {}
        for dims in self._days.get(metric, {}).values():
            for dimension, value in dims.items():
                parts.setdefault(dimension, []).append(value)
        return {dimension: math.fsum(values) for dimension, values in parts.items()}

    def total(self, metric):
        return total(self.flow(metric))

    def average(self, metric):
        """Mean of the daily totals over the days that have the metric, or None."""
        days = [total(dims) for dims in self._days.get(metric, {}).values()]
        return math.fsum(days) / len(days) if days else None

    def daily(self, metric):
        """{day: {dimension: value}} for the days that have the metric."""
        return self._days.get(metric, {})

    def snapshot(self, metric):
        """(day, {dimension: value}) of the newest day with the metric, or (None, {})."""
        days = self._days.get(metric)
        if not days:
            return None, {}
        newest = max(days)
        return newest, days[newest]


def total(dims):
    """The `total` dimension if there is one, otherwise the sum of the dimensions."""
    return dims["total"] if "total" in dims else math.fsum(dims.values())


@dataclass
class Facts:
    """What is stored for one window, summed up once for all 15 KPIs."""

    win: periods.Window
    coverage: dict
    files: dict | None  # sums over the ok marketplace-days; None if there is none
    units: int | None  # units sold; None unless every sale row has a unit count
    buyers: dict
    internal: Internal
    split: dict | None  # revenue and cost of goods per category
    opening_stock: int | None  # listings still active the night before the window; None if not stored


def coverage(win, pulse):
    """The `coverage` object: which expected marketplace-days of the window are ok."""
    status = {(r.business_date, r.marketplace): r.status for r in pulse}
    by_marketplace = dict.fromkeys(EXPECTED, 0)
    gaps, counts = [], {"complete": 0, "partial": 0, "missing": 0}
    for day in (d.isoformat() for d in win.dates()):
        ok = 0
        for m in EXPECTED:
            found = status.get((day, m), "not_loaded")
            if found == "ok":
                ok += 1
                by_marketplace[m] += 1
            else:
                gaps.append({"date": day, "marketplace": m, "status": found})
        counts["complete" if ok == len(EXPECTED) else "partial" if ok else "missing"] += 1
    return {
        "days_expected": win.days,
        "days_complete": counts["complete"],
        "days_partial": counts["partial"],
        "days_missing": counts["missing"],
        "complete": not gaps,
        "by_marketplace": by_marketplace,
        "gaps": gaps,
    }


def file_totals(pulse):
    """Sums over the ok marketplace-days, or None if there is none (no data is not a zero).
    `by_marketplace` is the revenue of each marketplace that has an ok day, in display order."""
    ok = [r for r in pulse if r.status == "ok"]
    if not ok:
        return None
    revenue = {}
    for r in ok:
        revenue[r.marketplace] = revenue.get(r.marketplace, 0) + (r.revenue_cents or 0)
    return {**{k: sum(getattr(r, k) or 0 for r in ok) for k in SUMS},
            "by_marketplace": {m: revenue[m] for m in MARKETPLACES if m in revenue}}


def buyer_stats(sales):
    """Buyers and repeat buyers over the sale rows. Buyer ids are only comparable inside a marketplace."""
    orders_of, every_order, with_id = {}, set(), set()
    for s in sales:
        order = (s.marketplace, s.order_id)
        every_order.add(order)
        if s.customer_id:
            with_id.add(order)
            orders_of.setdefault((s.marketplace, s.customer_id), set()).add(s.order_id)
    covered = {m for m, _ in with_id}
    uncovered = {m for m, _ in every_order - with_id} - covered
    return {
        "buyers": len(orders_of),
        "repeat_buyers": sum(len(orders) >= 2 for orders in orders_of.values()),
        "orders_with_buyer_id": len(with_id),
        "orders": len(every_order),
        "covered": [m for m in MARKETPLACES if m in covered],
        "uncovered": [m for m in MARKETPLACES if m in uncovered],
    }


def category_split(files, internal):
    """Revenue and cost of goods per category, or None if it cannot be made.

    The files carry no category, so total revenue is split by the internal sales-by-category
    shares and the parts add up to it. Each category's cost of goods is its internal cost
    ratio applied to that revenue.
    """
    sales = {c: v for c, v in internal.flow("category_sales_cents").items() if c != "total" and v > 0}
    if not files or files["revenue_cents"] <= 0 or not sales:
        return None
    names = sorted(sales)
    revenue = dict(zip(names, allocate(files["revenue_cents"], [sales[c] for c in names])))
    cost = internal.flow("category_cogs_cents")
    return {
        "revenue": revenue,
        "cogs": {c: round(revenue[c] * cost[c] / sales[c]) for c in names if c in cost},
        "internal_sales_cents": round(math.fsum(sales.values())),
    }


def allocate(total, weights):
    """Split the integer `total` in proportion to `weights` so the parts add up exactly (largest remainder)."""
    whole = math.fsum(weights)
    exact = [total * w / whole for w in weights]
    parts = [math.floor(x) for x in exact]
    largest_remainder_first = sorted(range(len(parts)), key=lambda i: (parts[i] - exact[i], i))
    for i in largest_remainder_first[: total - sum(parts)]:
        parts[i] += 1
    return parts


def facts(win, data):
    internal = Internal(data.internal)
    files = file_totals(data.pulse)
    known = bool(data.sales) and all(s.units is not None for s in data.sales)
    return Facts(
        win=win,
        coverage=coverage(win, data.pulse),
        files=files,
        units=sum(s.units for s in data.sales) if known else None,
        buyers=buyer_stats(data.sales),
        internal=internal,
        split=category_split(files, internal),
        opening_stock=round(math.fsum(r.value for r in data.opening)) if data.opening else None,
    )
