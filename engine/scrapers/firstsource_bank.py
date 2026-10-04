"""Bank feed of 1st Source account 0101, the month-end source for the carriers OSM, PB and EasyPost (deck
slide 38: "1st Source acct 0101 • GL 10009"). The real feed is a STUB; `--simulate` is the demo.

ASSUMPTION (docs/ASSUMPTIONS.md 2c.1, 2c.4): 0101 is a second bank account, the carriers are paid from it,
and its activity can be fetched through an API. Nobody has shown us the account or a feed: the layout is
the one of our synthetic bank export plus an Account column, and the text the bank prints for each carrier
is ours. The simulated month also carries the Goodwill Books payment as a credit (the statement of
engine/scrapers/goodwillbooks.py). Environment for the real feed, once there is one: BANK_FEED_URL,
BANK_FEED_TOKEN.
"""
from pathlib import Path

from . import close_simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class FirstSourceBank(Scraper):
    source = "bank_0101"
    cadence = "month_end"
    env_keys = ("BANK_FEED_URL", "BANK_FEED_TOKEN")

    def fetch_month(self, month: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("bank feed API is assumed but not connected: endpoint and fields unknown")

    def simulate_month(self, month: str, dest_dir: Path) -> tuple[list[Path], dict]:
        return close_simulation.simulate_bank_0101(month, dest_dir)
