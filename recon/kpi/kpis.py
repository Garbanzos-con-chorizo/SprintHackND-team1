"""The 15 KPIs, each computed from the facts of its window (docs/contracts/kpi.md, "The 15 KPIs")."""
import math
import re
from dataclasses import dataclass, field

from . import periods
from .facts import LABELS, MARKETPLACES, total

# Open definitions (kpi.md, "Open questions"): one constant each.
GROWTH_BASIS = "prior_period"  # `year_over_year` once 13 months are stored
UNSOLD_THRESHOLD_DAYS = 30
TOP = 10

# How a note names each internal metric.
THINGS = {
    "labor_hours": "labor hours", "labor_cost_cents": "labor cost", "employees": "headcount",
    "listings_created": "listings", "donation_to_listing_days": "donation dates",
    "unlisted_backlog": "backlog count", "active_listings_by_age": "active listings",
    "shipping_net_cost_cents": "shipping cost", "category_sales_cents": "sales by category",
    "category_cogs_cents": "cost of goods",
}
PER_ORDER = ("Revenue / orders (per order until unit counts are available).",
             "Per order, not per unit: the exports do not give unit counts yet.")
BY_ORDERS = ("Orders / listings created in the period (a stand-in for units sold / units listed).",
             "Orders / listings created, until unit counts are available.")


@dataclass
class Result:
    """One KPI before it is shaped for the file."""

    value: object = None  # a number, or the rows of a ranking
    inputs: dict = field(default_factory=dict)
    problems: list = field(default_factory=list)  # (status, reason, note)
    basis: str | None = None
    covers: list | None = None
    per: str | None = None  # replaces the catalog's when a fallback changes it
    definition: str | None = None  # same
    note: str | None = None  # said even when the KPI is ok (a fallback)

    def problem(self, status, reason, note):
        self.problems.append((status, reason, note))


# ---- what can be wrong with the inputs ----

def _join(words, last):
    words = list(words)
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} {last} {words[-1]}"


def gap_note(cov):
    days = {}
    for gap in cov["gaps"]:
        days.setdefault(gap["marketplace"], []).append(gap["date"])
    parts = [f"{LABELS[m]} has no data on {d[0] if len(d) == 1 else f'{len(d)} days'}" for m, d in days.items()]
    return "; ".join(parts) + ", so this is partial."


def _no_files(res, f):
    """Flag `res` for missing marketplace data. True if there is none at all."""
    if f.files is None:
        res.problem("no_data", "no_marketplace_data", "No marketplace has data in this period.")
        return True
    if not f.coverage["complete"]:
        res.problem("partial", "missing_days", gap_note(f.coverage))
    return False


def _no_internal(res, f, *metrics, every_day=True):
    """Flag `res` for internal metrics missing on all or (if `every_day`) some days. True if one is missing entirely."""
    days = {m: f.internal.days_with(m) for m in metrics}
    absent = [THINGS[m] for m in metrics if not days[m]]
    short = [f"{THINGS[m]} ({days[m]} of {f.win.days} days)" for m in metrics if 0 < days[m] < f.win.days]
    short = short if every_day else []
    if absent:
        res.problem("no_data", "no_internal_data",
                    f"The internal API returned no {_join(absent, 'or')} for this period.")
    if short:
        res.problem("partial", "missing_internal_days", f"Internal data is incomplete: {_join(short, 'and')}.")
    return bool(absent)


def _snapshot(res, f, metric):
    """The newest snapshot of `metric` in the window, flagged if it is older than the last day."""
    as_of, dims = f.internal.snapshot(metric)
    if as_of is None:
        res.problem("no_data", "no_internal_data",
                    f"The internal API returned no {THINGS[metric]} for this period.")
    elif as_of < f.win.through.isoformat():
        res.problem("partial", "missing_internal_days", f"The latest {THINGS[metric]} snapshot is from {as_of}.")
    return as_of, dims


def _zero(res, what):
    res.problem("no_data", "zero_denominator", what)
    return res


# ---- the 15 KPIs: each takes the facts of its window and of the comparison window ----

def _revenue(f, prev):
    res = Result(inputs=dict.fromkeys(("gross_cents", "refunds_cents", "fees_cents", "orders")))
    if _no_files(res, f):
        return res
    res.value = f.files["revenue_cents"]
    res.inputs = {k: f.files[k] for k in res.inputs}
    return res


def _revenue_growth(f, prev):
    res = Result(basis=GROWTH_BASIS, inputs={"revenue_cents": f.files and f.files["revenue_cents"],
                                             "prior_revenue_cents": None})
    stop = _no_files(res, f)
    compared = periods.comparison_label(prev.win)
    if prev.files is None:
        res.problem("no_data", "no_prior_period", f"No data stored for {compared}.")
        return res
    before = res.inputs["prior_revenue_cents"] = prev.files["revenue_cents"]
    if not prev.coverage["complete"]:
        res.problem("partial", "missing_days", f"The comparison period ({compared}) is partial.")
    if stop:
        return res
    if before <= 0:
        return _zero(res, f"Revenue in {compared} is zero.")
    res.value = round((f.files["revenue_cents"] - before) / before, 4)
    return res


def _net_margin(f, prev):
    res = Result(inputs=dict.fromkeys(("revenue_cents", "fees_cents", "cogs_cents", "shipping_net_cost_cents",
                                       "labor_cost_cents", "net_profit_cents")))
    stop = _no_files(res, f)
    stop |= _no_internal(res, f, "category_sales_cents", "category_cogs_cents", "shipping_net_cost_cents",
                         "labor_cost_cents")
    if f.files:
        res.inputs.update(revenue_cents=f.files["revenue_cents"], fees_cents=f.files["fees_cents"])
    if stop:
        return res
    if f.split is None:
        return _zero(res, "Revenue is zero.")
    _missing_cogs(res, f.split)
    revenue, fees = f.files["revenue_cents"], f.files["fees_cents"]
    cogs = sum(f.split["cogs"].values())  # the same cost of goods as the margin ranking
    shipping = round(f.internal.total("shipping_net_cost_cents"))
    labor = round(f.internal.total("labor_cost_cents"))
    profit = revenue - fees - cogs - shipping - labor
    res.inputs.update(cogs_cents=cogs, shipping_net_cost_cents=shipping, labor_cost_cents=labor,
                      net_profit_cents=profit)
    res.value = round(profit / revenue, 4)
    return res


def _listings(f):
    """New listings per marketplace, in display order."""
    flow = {k: round(v) for k, v in f.internal.flow("listings_created").items() if k != "total"}
    return {k: flow[k] for k in sorted(flow, key=lambda k: (MARKETPLACES.index(k) if k in MARKETPLACES else 99, k))}


def _listings_created(f, prev):
    res = Result(inputs={"by_marketplace": None})
    if _no_internal(res, f, "listings_created"):
        return res
    res.inputs["by_marketplace"] = _listings(f)
    res.value = round(f.internal.total("listings_created"))
    return res


def _revenue_per_labor_hour(f, prev):
    res = Result(inputs={"revenue_cents": f.files and f.files["revenue_cents"], "labor_hours": None})
    stop = _no_files(res, f)
    stop |= _no_internal(res, f, "labor_hours")
    if stop:
        return res
    hours = f.internal.total("labor_hours")
    res.inputs["labor_hours"] = round(hours, 1)
    if hours <= 0:
        return _zero(res, "No labor hours in the period.")
    res.value = round(f.files["revenue_cents"] / hours)
    return res


def _per_employee(res, f, amount, digits):
    """`amount` / average employees, into `res`."""
    employees = f.internal.average("employees")
    res.inputs["employees"] = round(employees, 2)
    if employees <= 0:
        return _zero(res, "No e-commerce employees in the period.")
    res.value = round(amount / employees, digits)
    return res


def _listings_per_employee(f, prev):
    res = Result(inputs={"listings_created": None, "employees": None})
    if _no_internal(res, f, "listings_created", "employees"):
        return res
    listed = res.inputs["listings_created"] = round(f.internal.total("listings_created"))
    return _per_employee(res, f, listed, 1)


def _days_donation_to_listing(f, prev):
    res = Result(inputs={"items_listed": None})
    # A day on which nothing was listed has no rows, so only a period without any row is flagged.
    if _no_internal(res, f, "donation_to_listing_days", every_day=False):
        return res
    ages = f.internal.flow("donation_to_listing_days")
    if not all(re.fullmatch(r"\d+", age) for age in ages):
        res.problem("no_data", "no_internal_data", "The internal donation ages are not whole days.")
        return res
    counts = sorted((int(age), round(n)) for age, n in ages.items())
    items = res.inputs["items_listed"] = sum(n for _, n in counts)
    if items <= 0:
        return _zero(res, "No items with a donation date were listed in the period.")
    res.value = round(median(counts), 1)
    return res


def median(counts):
    """Median of a histogram [(value, count)] sorted by value: the mean of the two middle items when even."""
    n = sum(count for _, count in counts)
    middle = ((n + 1) // 2, n // 2 + 1)  # 1-based positions of the middle item(s)
    seen, picked = 0, []
    for value, count in counts:
        seen += count
        while len(picked) < 2 and seen >= middle[len(picked)]:
            picked.append(value)
    return sum(picked) / 2


def _unlisted_backlog(f, prev):
    res = Result(inputs={"as_of": None})
    as_of, dims = _snapshot(res, f, "unlisted_backlog")
    if as_of is None:
        return res
    res.inputs["as_of"] = as_of
    res.value = round(total(dims))
    return res


def _unsold_pct(f, prev):
    res = Result(inputs={"as_of": None, "active_listings": None, "active_over_threshold": None,
                         "threshold_days": UNSOLD_THRESHOLD_DAYS})
    as_of, by_age = _snapshot(res, f, "active_listings_by_age")
    if as_of is None:
        return res

    def youngest(bucket):  # "31-60" -> 31, "91+" -> 91
        m = re.match(r"\d+", bucket)
        return int(m[0]) if m else 0

    active = round(math.fsum(by_age.values()))
    old = round(math.fsum(n for bucket, n in by_age.items() if youngest(bucket) > UNSOLD_THRESHOLD_DAYS))
    res.inputs.update(as_of=as_of, active_listings=active, active_over_threshold=old)
    if active <= 0:
        return _zero(res, "No active listings.")
    res.value = round(old / active, 4)
    return res


def _asp(f, prev):
    res = Result(inputs={"revenue_cents": None, "units": f.units, "orders": None})
    if _no_files(res, f):
        return res
    revenue, orders = f.files["revenue_cents"], f.files["orders"]
    res.inputs.update(revenue_cents=revenue, orders=orders)
    if f.units is None:
        res.basis, res.per = "per_order", "order"
        res.definition, res.note = PER_ORDER
    else:
        res.basis = "per_unit"
    sold = orders if f.units is None else f.units
    if sold <= 0:
        return _zero(res, "Nothing was sold in the period.")
    res.value = round(revenue / sold)
    return res


def _sell_through(f, prev):
    res = Result(inputs={"units_sold": f.units, "orders": f.files and f.files["orders"], "units_listed": None})
    stop = _no_files(res, f)
    stop |= _no_internal(res, f, "listings_created")
    if stop:
        return res
    listed = res.inputs["units_listed"] = round(f.internal.total("listings_created"))  # one listing = one unit
    if f.units is None:
        res.basis = "orders"
        res.definition, res.note = BY_ORDERS
    else:
        res.basis = "units"
    if listed <= 0:
        return _zero(res, "No listings were created in the period.")
    res.value = round((f.files["orders"] if f.units is None else f.units) / listed, 4)
    return res


def _sales_per_employee(f, prev):
    res = Result(inputs={"revenue_cents": f.files and f.files["revenue_cents"], "employees": None})
    stop = _no_files(res, f)
    stop |= _no_internal(res, f, "employees")
    if stop:
        return res
    return _per_employee(res, f, f.files["revenue_cents"], None)


def _missing_cogs(res, split):
    missing = [c for c in split["revenue"] if c not in split["cogs"]]
    if missing:
        res.problem("partial", "missing_internal_days",
                    f"No cost of goods for {_join(missing, 'and')}; counted as zero.")


def _rank(values, of=None):
    """The top rows of {label: value}, largest first, and what the others add up to."""
    total = sum(values.values())
    rows = [
        {
            "rank": i + 1,
            "label": c,
            "value": values[c],
            "share": round(values[c] / total, 4) if total > 0 else None,
            "ratio": round(values[c] / of[c], 4) if of and of[c] else None,
        }
        for i, c in enumerate(sorted(values, key=lambda c: (-values[c], c))[:TOP])
    ]
    return rows, total - sum(row["value"] for row in rows)


def _top_revenue(f, prev):
    res = Result(value=[], basis="internal_split",
                 inputs={"revenue_cents": f.files and f.files["revenue_cents"], "internal_sales_cents": None,
                         "categories": None, "rest_cents": None})
    stop = _no_files(res, f)
    stop |= _no_internal(res, f, "category_sales_cents")
    if stop:
        return res
    if f.split is None:
        return _zero(res, "Revenue is zero.")
    res.value, rest = _rank(f.split["revenue"])
    res.inputs.update(internal_sales_cents=f.split["internal_sales_cents"], categories=len(f.split["revenue"]),
                      rest_cents=rest)
    return res


def _top_margin(f, prev):
    res = Result(value=[], basis="internal_split",
                 inputs={"revenue_cents": f.files and f.files["revenue_cents"], "cogs_cents": None,
                         "margin_cents": None, "categories": None, "rest_cents": None})
    stop = _no_files(res, f)
    stop |= _no_internal(res, f, "category_sales_cents", "category_cogs_cents")
    if stop:
        return res
    if f.split is None:
        return _zero(res, "Revenue is zero.")
    _missing_cogs(res, f.split)
    revenue, cogs = f.split["revenue"], f.split["cogs"]
    margin = {c: revenue[c] - cogs.get(c, 0) for c in revenue}
    res.value, rest = _rank(margin, of=revenue)
    res.inputs.update(cogs_cents=sum(cogs.values()), margin_cents=sum(margin.values()), categories=len(revenue),
                      rest_cents=rest)
    return res


def _repeat_buyer_rate(f, prev):
    res = Result(inputs=dict.fromkeys(("buyers", "repeat_buyers", "orders_with_buyer_id", "orders")))
    if f.win.period.type == "day":
        res.problem("no_data", "period_too_short", "One day is too short to measure repeat buyers.")
        return res
    if _no_files(res, f):
        return res
    b = f.buyers
    res.inputs = {k: b[k] for k in res.inputs}
    if not b["buyers"]:
        stored = "No marketplace gives a buyer id." if b["orders"] else "No transactions are stored for this period."
        res.problem("no_data", "no_buyer_ids", stored)
        return res
    res.value = round(b["repeat_buyers"] / b["buyers"], 4)
    if b["orders_with_buyer_id"] < b["orders"]:
        res.covers = b["covered"]
        share = f"{round(100 * b['orders_with_buyer_id'] / b['orders'])}% of orders"
        if b["uncovered"]:
            names = [LABELS[m] for m in b["uncovered"]]
            who = f"{_join(names, 'and')} {'gives' if len(names) == 1 else 'give'} no buyer id"
            note = f"{_join([LABELS[m] for m in b['covered']], 'and')} only ({share}): {who}."
        else:
            note = f"Only {share} have a buyer id."
        res.problem("partial", "no_buyer_ids", note)
    return res


CALC = {
    "fin.revenue": _revenue,
    "fin.revenue_growth": _revenue_growth,
    "fin.net_margin": _net_margin,
    "prod.listings_created": _listings_created,
    "prod.revenue_per_labor_hour": _revenue_per_labor_hour,
    "prod.listings_per_employee": _listings_per_employee,
    "inv.days_donation_to_listing": _days_donation_to_listing,
    "inv.unlisted_backlog": _unlisted_backlog,
    "inv.unsold_pct": _unsold_pct,
    "sales.asp": _asp,
    "sales.sell_through": _sell_through,
    "sales.sales_per_employee": _sales_per_employee,
    "cat.top_revenue": _top_revenue,
    "cat.top_margin": _top_margin,
    "cust.repeat_buyer_rate": _repeat_buyer_rate,
}
