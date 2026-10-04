"""Amazon orders provider. The real API is a STUB (not documented); `--simulate` is the demo.

ASSUMPTION (see docs/ASSUMPTIONS.md): Amazon delivers in the Cash Monkey report layout (channel `Amazon-MF`),
so the engine reads it with the Cash Monkey parser. Environment for the real API, once documented:
AMAZON_URL, AMAZON_TOKEN.
"""
from pathlib import Path

from . import simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class Amazon(Scraper):
    source = "amazon"
    env_keys = ("AMAZON_URL", "AMAZON_TOKEN")

    def fetch(self, business_date: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("Amazon API is assumed but not documented: endpoint and fields unknown")

    def simulate(self, business_date: str, dest_dir: Path) -> list[Path]:
        return simulation.simulate_amazon(business_date, dest_dir)
