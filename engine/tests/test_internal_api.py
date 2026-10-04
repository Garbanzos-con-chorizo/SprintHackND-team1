"""V2.5: the internal API mock and client against docs/contracts/internal-api.md."""
import json
import statistics
import threading
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from engine.internal_api import (CATEGORIES, ENDPOINTS, LABEL, METRICS, HttpInternalApi, InternalApiError,
                                 MockInternalApi, make_client, snapshot_rows)
from engine.internal_api.mock import AGE_BUCKETS, split

DAY = "2026-09-14"  # a Monday
REVENUE = {"shopgoodwill": 87200, "ebay": 57676, "amazon": 30982}  # clean_month, 2026-09-14


UNITS = 75  # units sold that day, as the store would give them


def api(revenue=REVENUE, units=UNITS):
    return MockInternalApi(lambda day: revenue, lambda day: units)


def september():
    return [(date(2026, 9, 1) + timedelta(days=i)).isoformat() for i in range(30)]


def test_every_response_is_labelled_simulated_and_dated():
    for endpoint in ENDPOINTS:
        r = api().get(endpoint, DAY)
        assert (r["source"], r["label"], r["endpoint"], r["date"]) == ("mock", LABEL, endpoint, DAY)
    with pytest.raises(KeyError, match="unknown endpoint"):
        api().get("payroll", DAY)


def test_same_date_same_numbers_other_date_other_numbers():
    assert snapshot_rows(api(), DAY) == snapshot_rows(api(), DAY)
    assert snapshot_rows(api(), DAY) != snapshot_rows(api(), "2026-09-15")


def test_snapshot_has_the_eleven_metrics_with_their_units_and_dimensions():
    rows = snapshot_rows(api(), DAY)
    by_metric = {}
    for r in rows:
        by_metric.setdefault(r["metric"], []).append(r)
        assert r["source"] == "mock" and r["business_date"] == DAY
    assert list(by_metric) == [m for m, _, _ in METRICS]
    units = {m: u for m, _, u in METRICS}
    assert all(r["unit"] == units[r["metric"]] for r in rows)
    for metric in ("labor_hours", "labor_cost_cents", "employees", "unlisted_backlog", "shipping_net_cost_cents"):
        assert [r["dimension"] for r in by_metric[metric]] == ["total"], metric
    assert {r["dimension"] for r in by_metric["listings_created"]} == {"shopgoodwill", "ebay", "amazon"}
    assert [r["dimension"] for r in by_metric["active_listings_by_age"]] == AGE_BUCKETS
    assert {r["dimension"] for r in by_metric["category_sales_cents"]} == set(CATEGORIES)
    # no metric mixes a 'total' row with detail rows, so sums never double-count
    for metric, rs in by_metric.items():
        dims = [r["dimension"] for r in rs]
        assert dims == ["total"] or "total" not in dims, metric


def test_category_sales_add_up_to_the_revenue_to_the_cent():
    for revenue in (REVENUE, {"ebay": 101}, {"ebay": -2599, "amazon": 1000}, {"ebay": 0, "amazon": None}):
        sales = api(revenue).get("categories", DAY)["data"]["category_sales_cents"]
        assert sum(sales.values()) == sum(v for v in revenue.values() if v), revenue
    # most categories sell something on a normal day, so a top 10 means something
    sales = api().get("categories", DAY)["data"]["category_sales_cents"]
    assert sum(v > 0 for v in sales.values()) >= 12


def test_no_revenue_means_no_category_rows_not_zero():
    rows = snapshot_rows(api({"ebay": None}), DAY)
    assert not [r for r in rows if r["metric"].startswith("category_")]
    assert not [r for r in snapshot_rows(MockInternalApi(), DAY) if r["metric"].startswith("category_")]


def test_cogs_follow_category_sales():
    data = api().get("costs", DAY)["data"]["category_cogs_cents"]
    sales = api().get("categories", DAY)["data"]["category_sales_cents"]
    assert set(data) == set(sales)
    assert 0.15 < sum(data.values()) / sum(sales.values()) < 0.45


def test_donation_to_listing_histogram_counts_every_listing_and_has_a_plausible_median():
    for day in september():
        data = api().get("listings", day)["data"]
        hist = data["donation_to_listing_days"]
        assert sum(hist.values()) == sum(data["listings_created"].values())
        ages = [int(a) for a, n in hist.items() for _ in range(n)]
        assert 2 <= statistics.median(ages) <= 12, day


def test_plausible_sizes_over_september():
    """Sized to the sample: revenue per labor hour about $40-50, sell-through below 100%."""
    days = september()
    hours = sum(api().get("labor", d)["data"]["labor_hours"] for d in days)
    listings = sum(sum(api().get("listings", d)["data"]["listings_created"].values()) for d in days)
    assert 30 * 2300_00 / hours / 100 == pytest.approx(45, abs=10)  # ~$2,300 revenue a day
    assert 30 * 75 < listings < 30 * 140                          # ~75 orders a day
    sundays = [d for d in days if date.fromisoformat(d).weekday() == 6]
    mondays = [d for d in days if date.fromisoformat(d).weekday() == 0]
    created = lambda ds: statistics.mean(sum(api().get("listings", d)["data"]["listings_created"].values()) for d in ds)
    assert created(sundays) < created(mondays)


def test_employees_change_by_week_not_by_day():
    week = ["2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18", "2026-09-19", "2026-09-20"]
    assert len({api().get("labor", d)["data"]["employees"] for d in week}) == 1


def test_split_is_exact_and_keeps_the_sign():
    assert split(10, [1, 1, 1]) == [4, 3, 3]
    assert split(-10, [1, 1, 1]) == [-4, -3, -3]
    assert split(0, [1, 2]) == [0, 0]


# --- HTTP client and settings ----------------------------------------------------------------

@pytest.fixture
def server():
    """A local stand-in for Goodwill's API that answers with the mock."""
    mock = api()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            u = urlparse(self.path)
            endpoint = u.path.rsplit("/", 1)[-1]
            if not u.path.startswith("/api/internal/") or endpoint not in ENDPOINTS:
                self.send_error(404)
                return
            body = json.dumps({**mock.get(endpoint, parse_qs(u.query)["date"][0]), "source": "api"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_http_client_reads_the_same_snapshot_from_a_server(server):
    rows = snapshot_rows(HttpInternalApi(server), DAY)
    mock_rows = snapshot_rows(api(), DAY)
    assert [{**r, "source": "mock"} for r in rows] == mock_rows
    assert {r["source"] for r in rows} == {"api"}


def test_http_client_errors_are_internal_api_errors(server):
    with pytest.raises(InternalApiError, match="failed"):
        HttpInternalApi(server).get("payroll", DAY)
    with pytest.raises(InternalApiError, match="failed"):
        HttpInternalApi("http://127.0.0.1:9", timeout=2).get("labor", DAY)


def test_make_client_from_settings():
    assert isinstance(make_client(env={}), MockInternalApi)
    assert isinstance(make_client(env={"INTERNAL_API": "http", "INTERNAL_API_URL": "http://x"}), HttpInternalApi)
    with pytest.raises(InternalApiError, match="INTERNAL_API_URL"):
        make_client(env={"INTERNAL_API": "http"})
    with pytest.raises(InternalApiError, match="mock or http"):
        make_client(env={"INTERNAL_API": "sap"})


# --- listing_to_sale_days (Dani's page, kpi.md "Sell-through in two boxes") -------------------

def test_listing_to_sale_spreads_the_days_units_over_ages():
    for day in september():
        ages = api().get("listings", day)["data"]["listing_to_sale_days"]
        assert sum(ages.values()) == UNITS, day
        assert all(a.isdigit() for a in ages)  # whole days as text, as Dani's calculator requires
    pooled = [int(a) for d in september() for a, n in api().get("listings", d)["data"]["listing_to_sale_days"].items()
              for _ in range(n)]
    assert 4 <= statistics.median(pooled) <= 9           # auctions run about a week
    assert sum(a == 0 for a in pooled) / len(pooled) < 0.1  # few sell on the day they're listed


def test_no_sales_means_no_listing_to_sale_rows():
    for units in (0, None):
        rows = snapshot_rows(api(units=units), DAY)
        assert not [r for r in rows if r["metric"] == "listing_to_sale_days"], units
