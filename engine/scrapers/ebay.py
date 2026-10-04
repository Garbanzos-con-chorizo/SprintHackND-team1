"""eBay orders provider. The real API is a STUB (not documented); `--simulate` is the demo.

ASSUMPTION (see docs/ASSUMPTIONS.md): eBay delivers in the Cash Monkey report layout (channel `eBay`),
so the engine reads it with the Cash Monkey parser. Environment for the real API, once documented:
EBAY_URL, EBAY_TOKEN.
"""
from pathlib import Path

from . import simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class Ebay(Scraper):
    source = "ebay"
    env_keys = ("EBAY_URL", "EBAY_TOKEN")

    def fetch(self, business_date: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("eBay API is assumed but not documented: endpoint and fields unknown")

    def simulate(self, business_date: str, dest_dir: Path) -> list[Path]:
        return simulation.simulate_ebay(business_date, dest_dir)
