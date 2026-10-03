"""Pulse numbers from clean rows. Pure functions, integer cents, no file access."""
from .io import MARKETPLACES

NUMBERS = ("gross_cents", "refunds_cents", "revenue_cents", "fees_cents", "orders", "customers")
# Statuses that leave a marketplace out of the total and are reported as excluded.
NO_DATA = ("missing", "stale", "unknown")

DEFINITIONS = {
    "revenue": "Sales minus refunds, before marketplace fees. Excludes shipping and tax.",
    "fees": "Marketplace fees are shown separately and are not subtracted from revenue.",
    "customers": "Unique buyers where the marketplace exposes a buyer id, otherwise orders. "
    "The enterprise count is the sum of the marketplaces.",
    "day": "Order date, Eastern time.",
}


def summarize(rows):
    """Revenue (P-D1) and counts (P-D2) for the rows of one marketplace on one day."""
    sales = [r for r in rows if r.type == "sale"]
    gross = sum(r.gross_cents for r in sales)
    refunds = sum(r.gross_cents for r in rows if r.type == "refund")
    buyers = {r.customer_id for r in sales if r.customer_basis == "buyer"}
    orders_as_customers = {r.order_id for r in sales if r.customer_basis == "order"}
    bases = {r.customer_basis for r in (sales or rows)}
    return {
        "gross_cents": gross,
        "refunds_cents": refunds,
        "revenue_cents": gross + refunds,
        "fees_cents": sum(r.fee_cents for r in rows),
        "orders": len({r.order_id for r in sales}),
        "customers": len(buyers) + len(orders_as_customers),
        "customer_basis": _basis(bases),
    }


def _basis(bases):
    if not bases:
        return None
    return bases.pop() if len(bases) == 1 else "mixed"


def marketplace_statuses(rows, source_status, business_date):
    """Status per marketplace, from the per-source statuses (see Status in pulse.md)."""
    has_rows = {r.marketplace for r in rows if r.business_date == business_date}
    source_to_marketplace = {r.source: r.marketplace for r in rows}

    def marketplace_of(source):
        return source_to_marketplace.get(source, source if source in MARKETPLACES else "other")

    sources = (source_status or {}).get("sources", {})
    by_marketplace = {}
    for source, info in sources.items():
        by_marketplace.setdefault(marketplace_of(source), []).append(info["status"])
    # Without a status file we still expect the three named marketplaces.
    configured = set(by_marketplace) if source_status else set(MARKETPLACES) - {"other"}
    status_is_for_this_day = bool(source_status) and source_status.get("business_date") == business_date

    statuses = {}
    for m in MARKETPLACES:
        if status_is_for_this_day and m in by_marketplace:
            found = by_marketplace[m]
            statuses[m] = "ok" if "ok" in found else "stale" if "stale" in found else "missing"
        elif m in has_rows:
            statuses[m] = "ok"
        elif m in configured:
            statuses[m] = "unknown"
        else:
            statuses[m] = "not_configured"
    return statuses


def day_summary(rows, source_status, business_date):
    """The `marketplaces` and `enterprise` objects for one day, without deltas."""
    statuses = marketplace_statuses(rows, source_status, business_date)
    marketplaces = {}
    for m in MARKETPLACES:
        if statuses[m] == "ok":
            day_rows = [r for r in rows if r.marketplace == m and r.business_date == business_date]
            marketplaces[m] = {"status": "ok", **summarize(day_rows)}
        else:
            # null, never 0: no data is not a zero
            marketplaces[m] = {"status": statuses[m], **dict.fromkeys(NUMBERS), "customer_basis": None}

    included = [m for m in MARKETPLACES if statuses[m] == "ok"]
    enterprise = {k: sum(marketplaces[m][k] for m in included) for k in NUMBERS}
    enterprise["customer_basis"] = _basis({marketplaces[m]["customer_basis"] for m in included} - {None})
    enterprise["included"] = included
    enterprise["excluded"] = [
        {"marketplace": m, "status": statuses[m]} for m in MARKETPLACES if statuses[m] in NO_DATA
    ]
    return marketplaces, enterprise


def data_quality(warnings):
    if warnings is None:
        return None
    by_kind = {}
    for w in warnings:
        by_kind[w["kind"]] = by_kind.get(w["kind"], 0) + 1
    return {"warnings_total": len(warnings), "by_kind": by_kind}


def build_pulse(rows, source_status, warnings, business_date, generated_at=None):
    """The pulse dict for one day, shaped as docs/contracts/pulse.md.

    Not yet to contract: the `delta` objects are missing until P-D3.
    """
    marketplaces, enterprise = day_summary(rows, source_status, business_date)
    return {
        "schema_version": 1,
        "business_date": business_date,
        "generated_at": generated_at,
        "currency": "USD",
        "marketplaces": marketplaces,
        "enterprise": enterprise,
        "data_quality": data_quality(warnings),
        "definitions": DEFINITIONS,
    }
