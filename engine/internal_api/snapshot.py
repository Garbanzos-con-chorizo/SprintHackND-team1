"""One night's internal API snapshot as internal_daily rows (docs/contracts/internal-api.md)."""
from .mock import ENDPOINTS

# metric, endpoint that returns it, unit. A number becomes one row with dimension 'total';
# a mapping becomes one row per key. A metric the API leaves out gets no row: no data, not 0.
METRICS = [
    ("labor_hours", "labor", "hours"),
    ("labor_cost_cents", "labor", "cents"),
    ("employees", "labor", "fte"),
    ("listings_created", "listings", "listings"),
    ("donation_to_listing_days", "listings", "items"),
    ("listing_to_sale_days", "listings", "items"),
    ("unlisted_backlog", "listings", "items"),
    ("active_listings_by_age", "listings", "listings"),
    ("shipping_net_cost_cents", "costs", "cents"),
    ("category_sales_cents", "categories", "cents"),
    ("category_cogs_cents", "costs", "cents"),
]


def snapshot_rows(api, day: str) -> list[dict]:
    """Call every endpoint for `day` and return rows shaped like the internal_daily table."""
    responses = {endpoint: api.get(endpoint, day) for endpoint in ENDPOINTS}
    rows = []
    for metric, endpoint, unit in METRICS:
        resp = responses[endpoint]
        value = resp["data"].get(metric)
        if value is None:
            continue
        items = value.items() if isinstance(value, dict) else [("total", value)]
        rows += [{"business_date": day, "metric": metric, "dimension": str(dim), "value": v, "unit": unit,
                  "source": resp.get("source", "api")} for dim, v in items]
    return rows
