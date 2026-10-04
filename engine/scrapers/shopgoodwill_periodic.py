"""ShopGoodwill periodic reports (deck slide 38: "filter year/month; Period 1 periodic only; Period 3 all
reports"). The real API is a STUB; `--simulate` is the demo.

ASSUMPTION (docs/ASSUMPTIONS.md 2c.1, 2c.6): the report lists ShopGoodwill's payouts with the period each
one covers, and can be fetched through an API. Nobody has shown us the report: the layout is the one of
Dani's sample generator, and "Period 1" / "Period 3" are not modeled.

ON REQUEST ONLY (`--source shopgoodwill_periodic`). The simulated report is built from the simulated
Upright orders of the month (`engine fetch --simulate --from ... --to ...`), so it agrees with an inbox
those simulators filled and with nothing else. The two sample months have their own report, written by
the sample generator to agree with their bank file (`data/sample/<month>/periodic/`): use that one with
them. Delivering this one by default would put a second, disagreeing report beside the sample's.
Environment for the real API, once documented: SHOPGOODWILL_URL, SHOPGOODWILL_TOKEN.
"""
from pathlib import Path

from . import close_simulation
from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class ShopGoodwillPeriodic(Scraper):
    source = "shopgoodwill_periodic"
    cadence = "month_end"
    on_request_only = True
    env_keys = ("SHOPGOODWILL_URL", "SHOPGOODWILL_TOKEN")

    def fetch_month(self, month: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        raise NotConfigured("ShopGoodwill periodic report API is assumed but not documented: endpoint and fields unknown")

    def simulate_month(self, month: str, dest_dir: Path) -> tuple[list[Path], dict]:
        return close_simulation.simulate_shopgoodwill_periodic(month, dest_dir)
