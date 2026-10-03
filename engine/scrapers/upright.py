"""Upright: Paid Orders report. SKELETON, not runnable yet.

Source: the SprintHack deck, slides 21-26 (Goodwill Michiana, Upright report steps):
  1. Open Reports (the Reports icon in the top bar)
  2. Click "Paid orders" (left menu, under the report list)
  3. Set the date range (start date field, e.g. 9/30/2026)
  4. Generate the report
  5. Download it
  6. Staff then count customers as rows minus the title row.

What is unknown, and must be filled in by someone who can log in (see docs/decisions/003):
  - the portal URL and login flow (form? SSO? MFA?)
  - whether step 4-5 is one replayable request (use HttpSession) or needs clicks (use browser_session)
  - the report's file format (csv/xlsx) and whether delivery is a link, a download, or an email

Environment: UPRIGHT_URL, UPRIGHT_USER, UPRIGHT_PASSWORD.

To finish this scraper: open the portal with browser devtools on the Network tab, run steps 1-5, and
either copy the report request as cURL into the HTTP version below, or run
`python -m playwright codegen $UPRIGHT_URL` to record the clicks for the browser version.
"""
from pathlib import Path

from .base import NotConfigured, Scraper, register_scraper


@register_scraper
class Upright(Scraper):
    source = "upright"
    env_keys = ("UPRIGHT_URL", "UPRIGHT_USER", "UPRIGHT_PASSWORD")

    def fetch(self, business_date: str, dest_dir: Path, env: dict[str, str]) -> list[Path]:
        # The deck shows dates as M/D/YYYY (e.g. 9/30/2026); confirm the format and whether the
        # end date is inclusive on the real form, then derive `start`/`end` from business_date.

        # --- HTTP version (fill in after reading the network tab) --------------------------------
        #   http = HttpSession(base_url=env["UPRIGHT_URL"])
        #   http.post("<login path>", {"<user field>": env["UPRIGHT_USER"], "<pass field>": env["UPRIGHT_PASSWORD"]})
        #   return [http.download("<report path>?start=...&end=...", self.target(dest_dir, business_date, ".csv"))]
        #
        # --- Browser version (selectors come from `playwright codegen`) --------------------------
        #   with browser_session(dest_dir) as page:
        #       page.goto(env["UPRIGHT_URL"]); <login>; page.click("<Reports icon>"); page.click("text=Paid orders")
        #       page.fill("<start date>", start); page.fill("<end date>", end); page.click("text=Generate report")
        #       with page.expect_download() as d: page.click("<download link>")
        #       return [save_download(d.value, self.target(dest_dir, business_date, ".xlsx"))]
        raise NotConfigured("Upright scraper is a skeleton: portal URLs/selectors are not recorded yet")
