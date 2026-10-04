# 008 — A thin server for the static suite, for Docker

- **Date / author:** 2026-10-03, Orlando
- **Status:** accepted by Orlando; Victor implements (owner of plumbing per 007)
- **Changes:** the "static first" update of `006-web-app-scope-and-internal-api.md`, on one point: a server comes back, but only to serve the static files. Everything else in 006 and 007 stands.

## Decision
1. **`server.py` (FastAPI + `fastapi.staticfiles`, run by Uvicorn) serves the `reports/` folder on port 8000**, so the suite can ship as one Docker image for AWS or Azure later. It serves what the generators already wrote; it computes nothing and has no pages of its own.
2. **New dependencies, accepted here (rule 10):** `fastapi` and `uvicorn`, in a separate `requirements-server.txt`, so the engine, pulse and reports keep running on the standard library plus `openpyxl`/`tzdata`.
3. **No authentication** (006 point 3): it binds to `127.0.0.1` by default; inside the container it listens on `0.0.0.0` and the run command publishes it to localhost only. Said in the demo and the submission.
4. **The pages stay static and keep opening from disk.** The server is a deployment wrapper, not a requirement: if it slips, `python -m http.server 8000 -d reports` does the same job with no dependency.

## Consequences
- The monthly daily table (`reports/monthly/index.html`, which uses `fetch()`) works when served, which it can't from `file://`.
- Root files (`server.py`, `Dockerfile`, `requirements-server.txt`) are shared ground: claim them in `docs/CLAIMS.md`.
- Cut order: after the store backfill (Victor's 10:00 Sunday tripwire) and the PDF export; first thing to drop if Sunday is tight.
