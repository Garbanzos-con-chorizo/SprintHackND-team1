"""Runs scrapers and records what happened. A failing scraper never stops the others or the pipeline."""
import json
from pathlib import Path

from ..coverage import update_manifest
from .base import NotConfigured, Scraper


def run_scrapers(scrapers: list[Scraper], business_date: str, inbox: Path, env: dict[str, str],
                 only: str | None = None, simulate: bool = False) -> dict:
    """Fetch each scraper's report into inbox/. Returns the log dict (also what fetch_log.json holds).

    With `simulate=True` each provider's simulator writes synthetic reports instead of calling a real API;
    the log marks those entries `"simulated": true` so a run can never pass synthetic data off as real."""
    log = {"business_date": business_date, "sources": {}}
    inbox.mkdir(parents=True, exist_ok=True)
    for scraper in scrapers:
        if scraper.cadence != "daily" or (only and scraper.source not in only.split(",")):
            continue
        if simulate:
            try:
                files = scraper.simulate(business_date, inbox)
                update_manifest(inbox, {p.name: {"source": scraper.source, "business_date": business_date}
                                        for p in files})
                log["sources"][scraper.source] = {"status": "ok", "files": [p.name for p in files],
                                                  "detail": "simulated: synthetic data, no real API", "simulated": True}
            except NotConfigured as exc:
                log["sources"][scraper.source] = {"status": "not_configured", "files": [], "detail": str(exc)}
            except Exception as exc:
                log["sources"][scraper.source] = {"status": "failed", "files": [],
                                                  "detail": f"{type(exc).__name__}: {exc}"}
            continue
        missing = [k for k in scraper.env_keys if not env.get(k)]
        if missing:
            log["sources"][scraper.source] = {
                "status": "not_configured", "files": [],
                "detail": f"missing environment variables: {', '.join(missing)}",
            }
            continue
        try:
            files = scraper.fetch(business_date, inbox, env)
            update_manifest(inbox, {}, real=[p.name for p in files])
            log["sources"][scraper.source] = {"status": "ok", "files": [p.name for p in files], "detail": ""}
        except NotConfigured as exc:
            log["sources"][scraper.source] = {"status": "not_configured", "files": [], "detail": str(exc)}
        except Exception as exc:  # network, login, layout change: record it, keep going
            log["sources"][scraper.source] = {
                "status": "failed", "files": [], "detail": f"{type(exc).__name__}: {exc}",
            }
    return log


def run_close_scrapers(scrapers: list[Scraper], month: str, inbox: Path, env: dict[str, str],
                       only: str | None = None, simulate: bool = False) -> tuple[dict, dict]:
    """Fetch the month-end sources of `month` (YYYY-MM) into inbox/. Returns (the log, the answer key of the
    simulated files). Same rules as run_scrapers: a failure never stops the others, and simulated files are
    marked `"simulated": true` in the log and recorded in the inbox's manifest."""
    log = {"close_month": month, "sources": {}}
    expected: dict = {}
    wanted = set(only.split(",")) if only else None
    inbox.mkdir(parents=True, exist_ok=True)
    for scraper in scrapers:
        if scraper.cadence != "month_end":
            continue
        if scraper.source not in wanted if wanted is not None else scraper.on_request_only:
            continue
        try:
            if simulate:
                files, key = scraper.simulate_month(month, inbox)
                update_manifest(inbox, {p.name: {"source": scraper.source, "close_month": month} for p in files})
                expected.update(key)
                entry = {"status": "ok", "files": [p.name for p in files],
                         "detail": "simulated: synthetic data, no real API", "simulated": True}
            else:
                missing = [k for k in scraper.env_keys if not env.get(k)]
                if missing:
                    raise NotConfigured(f"missing environment variables: {', '.join(missing)}")
                files = scraper.fetch_month(month, inbox, env)
                update_manifest(inbox, {}, real=[p.name for p in files])
                entry = {"status": "ok", "files": [p.name for p in files], "detail": ""}
        except NotConfigured as exc:
            entry = {"status": "not_configured", "files": [], "detail": str(exc)}
        except Exception as exc:
            entry = {"status": "failed", "files": [], "detail": f"{type(exc).__name__}: {exc}"}
        log["sources"][scraper.source] = entry
    return log, expected


def write_log(out_dir: Path, log: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "fetch_log.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(log, f, indent=2)
        f.write("\n")
