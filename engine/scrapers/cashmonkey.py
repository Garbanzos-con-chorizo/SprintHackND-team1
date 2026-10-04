"""Cash Monkey "Orders Report" provider. The real API is a STUB (not documented); `--simulate` is the demo.

ASSUMPTION (see docs/ASSUMPTIONS.md): Cash Monkey, Amazon and eBay all deliver in the Cash Monkey report
layout, so the engine reads them with one parser (engine/sources/cashmonkey.py). Each provider covers its own
channel; this one covers Cash Monkey's own store, Goodwillbooks (the `other` row of the pulse).
Environment for the real API, once documented: CASHMONKEY_URL, CASHMONKEY_TOKEN.
"""
from pathlib import Path

from . import simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class CashMonkey(Scraper):
    source = "cashmonkey"
    env_keys = ("CASHMONKEY_URL", "CASHMONKEY_TOKEN")

    def fetch(self, business_date: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("Cash Monkey API is assumed but not documented: endpoint and fields unknown")

    def simulate(self, business_date: str, dest_dir: Path) -> list[Path]:
        return simulation.simulate_cashmonkey(business_date, dest_dir)
