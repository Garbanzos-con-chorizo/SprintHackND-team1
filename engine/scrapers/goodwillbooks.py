"""Goodwill Books prior-month payment statement (deck slide 38: "monthly email attachment"). The real
delivery is a STUB; `--simulate` is the demo.

ASSUMPTION (docs/ASSUMPTIONS.md 2c.1, 2c.6): the statement lists the prior month's sales, the fees and the
net payment, with the date paid and a reference. The slide says it arrives by email, which the inbox
already stands for; we assume it could equally be fetched. Nobody has shown us a statement, so the layout
is ours. Environment for a real client, once there is one: GOODWILLBOOKS_URL, GOODWILLBOOKS_TOKEN.
"""
from pathlib import Path

from . import close_simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class GoodwillBooks(Scraper):
    source = "goodwillbooks"
    cadence = "month_end"
    env_keys = ("GOODWILLBOOKS_URL", "GOODWILLBOOKS_TOKEN")

    def fetch_month(self, month: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("Goodwill Books statement API is assumed but not documented: endpoint and fields unknown")

    def simulate_month(self, month: str, dest_dir: Path) -> tuple[list[Path], dict]:
        return close_simulation.simulate_books_statement(month, dest_dir)
