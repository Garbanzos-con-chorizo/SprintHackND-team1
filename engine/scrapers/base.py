"""Scraper interface and registry.

To automate a new portal, drop one module in engine/scrapers/ with a Scraper subclass
decorated with @register_scraper. Nothing else changes: the `fetch` command discovers it.

    @register_scraper
    class MyPortal(Scraper):
        source = "myportal"                       # becomes the file name prefix in inbox/
        env_keys = ("MYPORTAL_URL", "MYPORTAL_TOKEN")

        def fetch(self, business_date, dest_dir, env):
            api = HttpSession(base_url=env["MYPORTAL_URL"], headers={"Authorization": "Bearer " + env["MYPORTAL_TOKEN"]})
            return [api.download("/reports/paid?date=" + business_date,
                                 self.target(dest_dir, business_date, ".csv"))]

A scraper only gets the file into inbox/. Reading it is the job of a Parser in engine/sources/.
"""
import importlib
import pkgutil
from pathlib import Path


class NotConfigured(Exception):
    """The scraper exists but is not usable yet (missing credentials, URLs or selectors)."""


class Scraper:
    source: str = ""                 # file name prefix and key in out/fetch_log.json
    env_keys: tuple[str, ...] = ()   # environment variables this scraper needs (credentials, base URL)
    # "daily": a report per business date (`engine fetch --date`). "month_end": one delivery per month for the
    # close (`engine fetch --close-month`), through fetch_month / simulate_month below.
    cadence: str = "daily"
    on_request_only: bool = False    # month_end: runs only when named with --source (see its module for why)

    def fetch(self, business_date: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        """Download the report(s) for `business_date` (YYYY-MM-DD) into dest_dir; return the paths."""
        raise NotImplementedError

    def simulate(self, business_date: str, dest_dir: Path) -> list[Path]:
        """Demo stand-in for the provider's API: write the report it would have emailed (synthetic data)
        into dest_dir. Used by `engine fetch --simulate`. Providers without a simulator raise NotConfigured."""
        raise NotConfigured(f"{self.source} has no simulator")

    def fetch_month(self, month: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        """Download the month-end file(s) of `month` (YYYY-MM) into dest_dir; return the paths."""
        raise NotConfigured(f"{self.source} has no month-end client")

    def simulate_month(self, month: str, dest_dir: Path) -> tuple[list[Path], dict]:
        """Demo stand-in for a month-end API: write the file(s) it would have delivered (synthetic data) and
        return them with their answer key, computed from the generated records."""
        raise NotConfigured(f"{self.source} has no month-end simulator")

    def target(self, dest_dir: Path, business_date: str, suffix: str) -> Path:
        """Standard file name so parser detection by file name keeps working: <source>_<date><suffix>."""
        return dest_dir / f"{self.source}_{business_date}{suffix}"


_REGISTRY: list[type[Scraper]] = []


def register_scraper(cls: type[Scraper]) -> type[Scraper]:
    if not cls.source:
        raise ValueError(f"{cls.__name__} must set `source`")
    if any(c.source == cls.source for c in _REGISTRY):
        raise ValueError(f"scraper for {cls.source!r} is already registered")
    _REGISTRY.append(cls)
    return cls


_INFRASTRUCTURE = {"base", "http", "env", "runner", "simulation", "close_simulation"}  # modules that are not portals


def load_scrapers() -> list[Scraper]:
    """Import every portal module in engine/scrapers/ (which registers it) and instantiate all."""
    import engine.scrapers as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name not in _INFRASTRUCTURE:
            importlib.import_module(f"{pkg.__name__}.{mod.name}")
    return [cls() for cls in _REGISTRY]
