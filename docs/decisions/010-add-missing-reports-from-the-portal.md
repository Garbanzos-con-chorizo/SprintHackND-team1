# 010 — Add the missing reports from the portal and run the close again

- **Date / author:** 2026-10-04, Victor
- **Status:** accepted by Victor and merged on his call (2026-10-04, #77), before Dani and Orlando answered; their notes are in their inboxes and their response lines are open below
- **Changes:** decision 008 on one point. The server "computes nothing and has no pages of its own" becomes: it still has no pages and still computes nothing itself, but it takes one action on request. Everything else in 008 and 006 stands.

## Context
A month-end close that says `INCOMPLETE` is missing a report for some days (the messy month: Amazon for September 21 and 22, ShopGoodwill for September 7). Today the fix is a terminal command with one more `--inbox`. The people who close the month do not use a terminal, and the fewest-steps criterion counts those steps. Goodwill's own process already has this moment: someone downloads the report that was missing and hands it over.

## Decision
1. **The Month-end Close list page (`reports/close/index.html`) gets a panel for the latest month**: the reports the close says are missing (from its exceptions file), a file picker and one button. It is plain HTML with an inline script; opened from disk it says it needs the server.
2. **`server.py` gets four routes under `/api/close/<month>/`**: list the added files, add one (`PUT`, the request body is the file), remove them all (`DELETE`), and run the close again (`POST run`). The work is in the new `reports/close_upload.py`, which calls the same `python -m reports.close` on the inboxes of the last run plus the folder of added files, logs the run in the store and rebuilds the portal. The server and the page compute nothing.
3. **Added files live in `out/uploads/<month>/`**, never in `data/sample/` and never under `reports/` (so they are not served back). Removing them and running again restores the month as it was.
4. **Limits, because there is no authentication (006):**
   - Only `.csv` and `.xlsx`, 10 MB a file, 40 files a month, a plain file name with any folder part dropped; the month must look like `2026-09`.
   - Every change must carry an `X-Reports` header. A page on another site cannot send it without this server's consent, so a browser that has the portal open cannot be made to add files by a link.
   - `CLOSE_UPLOADS=0` turns the four routes off. **The Docker image sets it**, because the container listens on `0.0.0.0`; the default (on) is for `python server.py`, which listens on `127.0.0.1`.
5. **No new dependency.** The file is the request body, read with Starlette's `request.body()`, so `python-multipart` is not needed.
6. **Nothing is posted, and the page says so.** The panel also says that the late reports used in the demo are the synthetic samples in `data/sample/messy_month/late/`.

## Consequences
- The demo's third step ("the late reports arrive") can be shown in the browser: choose the two files, press the button, and Amazon and ShopGoodwill go from `INCOMPLETE` to `OPEN`. Dani's command-line demo is unchanged and gives the same result.
- `reports/close.py` refuses two inboxes that hold a file of the same name. Adding a file that is already in the month's inbox is therefore refused by the close, and the panel shows its message.
- The server is no longer read-only when uploads are on. Anyone who can reach the port can add files and run the close, so it must stay on localhost or behind `CLOSE_UPLOADS=0` until there is authentication.
- `reports/run_scheduled.py` exposes `close_from(month, inboxes)`, the part of its close that the panel shares.
- Not built: choosing which earlier month to add files to (the panel is for the latest), a progress bar, and a check of the file's contents before the close reads it (the engine reports a file no source recognizes, as for any inbox).

## Responses
- Dani:
- Orlando:
