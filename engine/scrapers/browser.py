"""Browser backend: Playwright, imported only when a scraper uses it.

Use when HTTP can't work (login forms with tokens, MFA, JavaScript-built download links).
Setup (once, only for people who run browser scrapers):
    pip install -r engine/requirements-browser.txt
    python -m playwright install chromium
To record a flow instead of guessing selectors:  python -m playwright codegen <portal url>
"""
from contextlib import contextmanager
from pathlib import Path

from .base import NotConfigured


@contextmanager
def browser_session(download_dir: Path, headless: bool = True):
    """Yield a Playwright page whose downloads land in download_dir."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise NotConfigured(
            "browser scrapers need Playwright: pip install -r engine/requirements-browser.txt "
            "&& python -m playwright install chromium"
        ) from exc
    download_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        try:
            context = browser.new_context(accept_downloads=True)
            yield context.new_page()
        finally:
            browser.close()


def save_download(download, dest: Path) -> Path:
    """Persist a Playwright Download object (from `with page.expect_download() as d:`) to dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    download.save_as(dest)
    return dest
