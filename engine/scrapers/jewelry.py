"""Jewelry Report with its supplier lookup (deck slide 38: "Request report; Co-Pivot populates Supplier").
The real API is a STUB; `--simulate` is the demo.

ASSUMPTION (docs/ASSUMPTIONS.md 2c.1, 2c.3): the month's jewelry sales can be requested through an API,
"Supplier" is the Goodwill store that supplied the item, and "Co-Pivot populates Supplier" is a lookup that
knows which store supplied each item. Nobody has shown us the report or the lookup, so both layouts are
ours. The simulator writes the report without a supplier and the lookup as a second file, with one item
the lookup does not know. Environment for the real API, once documented: JEWELRY_URL, JEWELRY_TOKEN.
"""
from pathlib import Path

from . import close_simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class Jewelry(Scraper):
    source = "jewelry"
    cadence = "month_end"
    env_keys = ("JEWELRY_URL", "JEWELRY_TOKEN")

    def fetch_month(self, month: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("Jewelry Report API is assumed but not documented: endpoint and fields unknown")

    def simulate_month(self, month: str, dest_dir: Path) -> tuple[list[Path], dict]:
        return close_simulation.simulate_jewelry(month, dest_dir)
