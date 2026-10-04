"""Client for the Goodwill internal API (docs/contracts/internal-api.md).

Two implementations of one interface, get(endpoint, day) -> response envelope:
MockInternalApi (default, synthetic) and HttpInternalApi (a real API at INTERNAL_API_URL; we have
never seen one, so its paths are the contract's guess). INTERNAL_API=mock|http picks one.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .mock import MockInternalApi, RevenueLookup, UnitsLookup


class InternalApiError(Exception):
    pass


class HttpInternalApi:
    source = "api"

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, endpoint: str, day: str) -> dict:
        url = f"{self.base_url}/api/internal/{urllib.parse.quote(endpoint)}?date={urllib.parse.quote(day)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise InternalApiError(f"GET {url} failed: {e}") from e
        if not isinstance(body, dict) or not isinstance(body.get("data"), dict) or body.get("date") != day:
            raise InternalApiError(f"GET {url}: response does not follow docs/contracts/internal-api.md")
        return body


def make_client(revenue_by_marketplace: RevenueLookup | None = None, units_sold: UnitsLookup | None = None,
                env: dict | None = None):
    """The client the INTERNAL_API setting asks for (default: mock)."""
    env = os.environ if env is None else env
    kind = env.get("INTERNAL_API", "mock")
    if kind == "mock":
        return MockInternalApi(revenue_by_marketplace, units_sold)
    if kind == "http":
        if not env.get("INTERNAL_API_URL"):
            raise InternalApiError("INTERNAL_API=http needs INTERNAL_API_URL")
        return HttpInternalApi(env["INTERNAL_API_URL"])
    raise InternalApiError(f"INTERNAL_API must be mock or http, not {kind!r}")
