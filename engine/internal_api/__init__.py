"""Goodwill internal API, mocked today: docs/contracts/internal-api.md. KPIs read the store, not this."""
from .client import HttpInternalApi, InternalApiError, make_client
from .mock import CATEGORIES, ENDPOINTS, LABEL, MockInternalApi
from .snapshot import METRICS, snapshot_rows

__all__ = ["CATEGORIES", "ENDPOINTS", "HttpInternalApi", "InternalApiError", "LABEL", "METRICS",
           "MockInternalApi", "make_client", "snapshot_rows"]
