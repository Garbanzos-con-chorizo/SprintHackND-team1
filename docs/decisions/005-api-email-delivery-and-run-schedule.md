# 005 — Assume an Upright API with email delivery; run once a day

- **Date / author:** 2026-10-03, Victor, after the office-hours meeting with Amanda
- **Status:** accepted by the team in the meeting; schedule time still to confirm
- **Supersedes in part:** `003-portal-acquisition.md` (the browser and discovery parts)
- **Complements:** `004-data-acquisition-and-timing.md` (Orlando, Amanda's answers). Where the two differ on run time, 004's "after midnight Eastern" is the accepted default (option C below).

## Context
Amanda told us to **assume an API exists for Upright**, that the report can be **emailed** from it, and that it arrives as **Excel** (we can turn it into CSV if CSV isn't offered). Our earlier plan (003) allowed for browser automation because we couldn't tell whether a download could be replayed over HTTP. With an API assumed, that is no longer needed.

## Decision
1. **Acquisition is: ask the API for the report, receive it by email, read the attachment.** The email lands in the inbox folder (by a mail rule today, a mailbox reader later) and `engine/ingest/email_adapter.py` reads it. The Upright scraper in `engine/scrapers/upright.py` is a stub that will only make the request once the API is documented; until then it reports "not configured".
2. **Browser automation is removed**: `engine/scrapers/browser.py`, `engine/requirements-browser.txt` and the Playwright test are deleted. No dependency was lost; it was only ever optional.
3. **Kept:** the scraper interface and registry, the `fetch` command, the standard-library HTTP client (it will call the API), and `MockScraperAdapter` (the demo of a pluggable source).
4. **No Excel-to-CSV converter.** The engine reads `.xlsx` directly (`engine/table.py`) and writes the three files Dani consumes (`out/transactions.csv`, `out/source_status.json`, `out/warnings.json`). A converter would add a step with no benefit.
5. **Scope is e-commerce only.** Brick-and-mortar reports are independent of this work and are not ingested. The enterprise total is the e-commerce total.
6. **The engine runs once a day, at a fixed time**, so the e-commerce pulse is produced at the same moment the brick-and-mortar report goes out (B&M sends at 1:00 PM and 10:00 PM ET). Today `python -m reports.run_nightly` stands in for the scheduler and must be disclosed as a stand-in; in production Windows Task Scheduler or cron would call it. See "Schedule" below.

## Schedule
E-commerce reports **finalize at 9:00 PM PT, which is 12:00 AM ET**, every day of the year (PT and ET change clocks together). So a business day is complete only after midnight ET. Brick-and-mortar sends at 1:00 PM and 10:00 PM ET but is out of scope; its 10 PM report lands before a run after midnight, so one nightly run could cover it later.

| Option | Run time | Reports | Day complete | Notes |
|---|---|---|---|---|
| A | 1:00 PM ET | the **previous** Eastern day | yes | coincides with B&M's 1 PM send, but it is a next-day report, not "nightly" |
| B | 10:00 PM ET | the **current** day so far | **no, 2 hours short** | coincides with B&M's 10 PM send |
| **C (default)** | **just after 12:00 AM ET** (for example 12:30 AM) | the **day that just ended** | **yes** | nightly; B&M's 10 PM report is already in; matches decision 004 |

**Default: option C**, because it is the accepted decision 004 ("the nightly run happens after midnight Eastern") and it always reports a finished day. The exact time is configuration, not engine code; the engine takes the business date as `--date` and doesn't care when it runs. **To confirm with Amanda:** the run time she wants, and whether she reads the report the next morning or needs it earlier.

`python -m reports.run_nightly` (Orlando) stands in for the scheduler. In production Windows Task Scheduler or cron would call it, or the API delivery would trigger it. Disclose it as a stand-in.

## Consequences
- We no longer prepare for a login screen, so no discovery step is needed; documenting the API is what's missing.
- A missing report is shown as "no data" (already built), not retried forever. We do not add a separate "late" state: with one run a day, a report that hasn't arrived by then is simply missing, and the next run picks it up.
- The Upright stub, the mock scraper and the file inbox are all disclosed in built-versus-used as stand-ins for an API we have not seen.
