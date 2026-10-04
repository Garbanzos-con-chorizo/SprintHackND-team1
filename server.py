"""Thin web server for the static report suite (decision 008): serves reports/ and nothing else.

It computes nothing and has no pages of its own: every page, CSV and PDF under reports/ was written by
the generators (python -m reports.run_scheduled, run_nightly, engine.export). It exists so the suite can
ship as one Docker image, and so pages that use fetch() (reports/monthly/index.html) work, which they
can't from file://. No authentication (decision 006): it listens on 127.0.0.1 unless told otherwise.

    uvicorn server:app --host 127.0.0.1 --port 8000      # or: python server.py
    http://127.0.0.1:8000/                               # the portal, reports/index.html

Fallback with no dependency: python -m http.server 8000 -d reports
"""
import mimetypes
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

REPORTS = Path(os.environ.get("REPORTS_DIR") or Path(__file__).resolve().parent / "reports")
# reports/ also holds the generators' Python code and config/subscribers.csv (people's email addresses),
# so only what the generators write is served: pages, their data and the downloads.
SERVED = {".html", ".css", ".js", ".json", ".csv", ".pdf", ".png", ".svg", ".ico"}
# Same content types on every machine (the Windows registry may say .csv is application/vnd.ms-excel).
for _suffix, _type in {".csv": "text/csv", ".pdf": "application/pdf", ".json": "application/json",
                       ".js": "text/javascript", ".svg": "image/svg+xml"}.items():
    mimetypes.add_type(_type, _suffix)
NEVER = {"config", "tests", "__pycache__"}


class ReportFiles(StaticFiles):
    """StaticFiles limited to SERVED suffixes, outside the NEVER folders."""

    async def get_response(self, path, scope):
        p = Path(path)
        hidden = any(part in NEVER or part.startswith(".") for part in p.parts)
        if hidden or (p.suffix and p.suffix.lower() not in SERVED):
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)


app = FastAPI(title="Goodwill Michiana e-commerce reports", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    """For Docker and a cloud load balancer: up, and whether the portal has been generated yet."""
    return {"ok": True, "portal": (REPORTS / "index.html").exists()}


# Mounted last so /healthz wins; html=True serves index.html for a folder (/, /scorecard/, /pulse/).
app.mount("/", ReportFiles(directory=REPORTS, html=True, check_dir=False), name="reports")

if __name__ == "__main__":
    import uvicorn

    if not (REPORTS / "index.html").exists():
        print(f"server: {REPORTS / 'index.html'} doesn't exist yet; run `python -m reports.run_scheduled "
              "--from 2026-09-30 --to 2026-10-04` (or run_nightly) first")
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")))
