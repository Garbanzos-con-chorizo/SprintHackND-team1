"""Upright "Paid orders" report, requested through an assumed API. STUB, not runnable yet.

ASSUMPTION (Amanda, office hours 2026-10-03): an API exists for Upright. We assume it can generate the
Paid orders report for a date range (and timezone) and that Upright then EMAILS the report as an Excel
attachment, as the deck shows (slides 7-9, 38: "generate; email delivery"). So this scraper only has to
ask for the report. The file itself arrives in the inbox folder by email, where
engine/ingest/email_adapter.py reads it; nothing here parses or downloads it.

The endpoint, authentication and field names are NOT known, so `fetch` raises NotConfigured instead of
pretending. When the API is documented, replace the body with one call:

    api = HttpSession(base_url=env["UPRIGHT_URL"], headers={"Authorization": "Bearer " + env["UPRIGHT_TOKEN"]})
    api.post("<reports path>", {"report": "paid_orders", "from": business_date, "to": business_date,
                                "timezone": "America/New_York", "channel": "all", "payment_status": "paid"})
    return []   # nothing to download: the report arrives by email

If Upright can instead return the file directly, use `api.download(...)` and return that path.

Environment: UPRIGHT_URL, UPRIGHT_TOKEN.
"""
from pathlib import Path

from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class Upright(Scraper):
    source = "upright"
    env_keys = ("UPRIGHT_URL", "UPRIGHT_TOKEN")

    def fetch(self, business_date: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("Upright API is assumed but not documented: endpoint and fields unknown")
