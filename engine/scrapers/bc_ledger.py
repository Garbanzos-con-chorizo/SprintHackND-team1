"""Business Central general ledger entries, the month-end source for FedEx (deck slide 38). The real API
is a STUB; `--simulate` is the demo.

ASSUMPTION (docs/ASSUMPTIONS.md 2c.1, 2c.5): the month's G/L entries can be fetched from Business Central
through an API. Nobody has shown us one, there is no tenant to connect to, and the export layout is ours,
so `fetch_month` raises NotConfigured instead of pretending. Environment for the real API, once there is
one: BC_URL, BC_TOKEN.
"""
from pathlib import Path

from . import close_simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class BcLedger(Scraper):
    source = "bc_ledger"
    cadence = "month_end"
    env_keys = ("BC_URL", "BC_TOKEN")

    def fetch_month(self, month: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("Business Central API is assumed but not connected: endpoint and fields unknown")

    def simulate_month(self, month: str, dest_dir: Path) -> tuple[list[Path], dict]:
        return close_simulation.simulate_ledger(month, dest_dir)
