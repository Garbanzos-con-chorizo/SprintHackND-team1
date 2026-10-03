# 003 — Acquire reports by automating the portals, with HTTP or browser per portal

- **Date / author:** 2026-10-03, Victor
- **Status:** superseded in part by `004-api-email-delivery-and-daily-run.md`. The browser backend and the discovery step below were dropped after Amanda told us to assume an Upright API with emailed reports. The scraper interface, `fetch` command and HTTP client remain.
- **Changes:** the "file-drop, no scraping" line in `docs/roadmap.md` and `docs/PROBLEM.md`. File drop stays as the fallback.

## Context
The deck (slides 21-30, 41) shows staff downloading reports by clicking through logged-in portals (Upright: Reports, Paid orders, date range, Generate, Download; Cash Monkey / Books: Orders Report, dates, link). It gives no URLs, API or login details, and nothing for ShopGoodwill, eBay or Amazon. We cannot know yet whether each portal's report download can be replayed over plain HTTP or needs a real browser (login forms, CSRF tokens, MFA, JavaScript-built download links).

## Decision
1. **One scraper per portal** in `engine/scrapers/`, auto-discovered like the parsers. A scraper's job is: log in, run the report for a business date, save the downloaded file as `inbox/<source>_<YYYY-MM-DD>.<ext>`. It never parses; the existing detection and parsers (V2/V3) read the file. Scraped and hand-dropped files take the same path.
2. **Two interchangeable backends, chosen per portal:**
   - **HTTP** (`engine/scrapers/http.py`): cookie-keeping session on the standard library (`urllib`). Preferred when the report request can be replayed. Fast, no extra dependency.
   - **Browser** (`engine/scrapers/browser.py`): Playwright, imported only when a scraper asks for it. Used when HTTP can't work. Listed in `engine/requirements-browser.txt`, not in the base requirements, so nobody needs it unless they run a browser scraper.
3. **Discovery before code per portal:** log in once in a normal browser with devtools open, run the report, and look at the network tab. If the report is a single request that works with the session cookie ("Copy as cURL" replays it), write an HTTP scraper. If not, record the clicks (Playwright codegen) and write a browser scraper.
4. **Credentials:** read from environment variables or an ignored `.env` (each scraper lists the variable names it needs in its module docstring and `env_keys`; `.env.example` is a shared file, so it is added later by whoever claims it). Never committed, never logged. Whoever runs the scraper supplies Goodwill-approved credentials. Agents do not type credentials.
5. **Failure never crashes the run:** a scraper that fails or isn't configured is recorded in `out/fetch_log.json`; the pipeline continues with whatever is in `inbox/`, and that source shows as `missing` on the pulse.

## Consequences
- The demo can honestly say which portals are automated and which still rely on a file drop. Disclose it in built-versus-used.
- Scrapers are fragile to portal changes; the saved raw file in `inbox/` is the debugging record.
- Browser automation of a live account needs Goodwill's go-ahead (IT policy and portal terms, office-hours question 4). Until then the file-drop path must keep working.
- A new scraper is one file, like a new parser.
