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

## Implemented (2026-10-04, Victor)
- `server.py`, `requirements-server.txt` (`fastapi`, `uvicorn`), `Dockerfile` (`python:3.13-slim`), `.dockerignore`. Run: `uvicorn server:app --host 127.0.0.1 --port 8000` (or `python server.py`); `GET /healthz` reports whether the portal exists, for Docker's health check.
- **One change to point 1: the server doesn't serve all of `reports/`.** That folder also holds the generators' Python code and `config/subscribers.csv` (people's email addresses). It serves only what the generators write (`.html .css .js .json .csv .pdf .png .svg .ico`), never `config/`, `tests/` or dotfiles, and FastAPI's `/docs` and `/openapi.json` are off.
- **The image builds its own pages:** `reports/` is git-ignored output, so a clean checkout has nothing to serve. The Dockerfile runs `python -m reports.run_scheduled --from 2026-09-30 --to 2026-10-04` at build time (September in the store, five nights, the September scorecard with its CSV, the close) and checks the portal exists. The slim image has no browser, so its PDF step says "print from the page" and the build goes on. It runs as a non-root user.
- Checked without Docker (the daemon wasn't running): the same build steps on a clean copy with a fresh 3.13 environment and no browser took 37 s, exit 0. Then the server, started as the image's `CMD`: every link on the portal returns 200 (16 of 16, including the Business Central files), the monthly page's `fetch()` table renders September, and config, code and `/docs` return 404. **Docker verified (2026-10-04, Docker 29.2.0):** `docker build -t goodwill-reports .` from a clean export of `main` (cea0c16) took 42 s, exit 0, image 253 MB (Python 3.13.16). `docker run -d -p 127.0.0.1:8000:8000 goodwill-reports`: Docker's health check says healthy, all 16 portal links return 200, the September scorecard reads $70,753.96 and its CSV downloads, and `/config/subscribers.csv`, `/run_nightly.py`, `/docs`, `/openapi.json` and `/../etc/passwd` return 404. It runs as user `app`.
