"""Thin web server for the static report suite (decision 008): serves reports/, plus one action (decision 010).

It has no pages of its own: every page, CSV and PDF under reports/ was written by the generators
(python -m reports.run_scheduled, run_nightly, engine.export). It exists so the suite can ship as one
Docker image, and so pages that use fetch() (reports/monthly/index.html) work, which they can't from
file://. The one action: take the reports that were missing at month end and run the close again
(/api/close/<month>/...), which is reports.close_upload and the close itself; the server computes nothing.
No authentication (decision 006): it listens on 127.0.0.1 unless told otherwise.

    uvicorn server:app --host 127.0.0.1 --port 8000      # or: python server.py
    http://127.0.0.1:8000/                               # the portal, reports/index.html

Fallback with no dependency: python -m http.server 8000 -d reports
"""
import mimetypes
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from reports import close_upload

REPORTS = Path(os.environ.get("REPORTS_DIR") or Path(__file__).resolve().parent / "reports")
# reports/ also holds the generators' Python code and config/subscribers.csv (people's email addresses),
# so only what the generators write is served: pages, their data and the downloads.
SERVED = {".html", ".css", ".js", ".json", ".csv", ".pdf", ".png", ".svg", ".ico", ".xlsx"}
# Same content types on every machine (the Windows registry may say .csv is application/vnd.ms-excel).
for _suffix, _type in {".csv": "text/csv", ".pdf": "application/pdf", ".json": "application/json",
                       ".js": "text/javascript", ".svg": "image/svg+xml",
                       ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}.items():
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


# Decision 010: the one thing the server does besides serving files. Staff add the reports that were missing at
# month end and run the close again, from reports/close/index.html. The work is reports.close_upload's and the
# close's own; nothing is posted. No authentication (decision 006), so: on by default only because the server
# listens on 127.0.0.1; CLOSE_UPLOADS=0 turns it off; and every change must carry the X-Reports header, which a
# page on another site cannot send without this server's consent.
UPLOADS_ON = os.environ.get("CLOSE_UPLOADS", "1") != "0"


def _guard(request: Request):
    if not UPLOADS_ON:
        raise HTTPException(status_code=403, detail="adding files is switched off on this server (CLOSE_UPLOADS=0)")
    if request.headers.get("x-reports") != "1":
        raise HTTPException(status_code=403, detail="missing X-Reports header")


def _refuse(e):
    return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/close/{month}/uploads", include_in_schema=False)
def uploads_list(month: str):
    """The files added for the month so far, and whether adding is switched on."""
    try:
        return {"enabled": UPLOADS_ON, "month": month, "files": close_upload.added(month)}
    except close_upload.Rejected as e:
        return _refuse(e)


@app.put("/api/close/{month}/uploads/{name}", include_in_schema=False)
async def uploads_add(month: str, name: str, request: Request):
    """Keep one report file (the request body is the file). Only .csv and .xlsx, 10 MB at most."""
    _guard(request)
    if int(request.headers.get("content-length") or 0) > close_upload.MAX_BYTES:
        return _refuse(f"{name} is larger than {close_upload.MAX_BYTES // (1024 * 1024)} MB")
    try:
        close_upload.save(month, name, await request.body())
        return {"ok": True, "files": close_upload.added(month)}
    except close_upload.Rejected as e:
        return _refuse(e)


@app.delete("/api/close/{month}/uploads", include_in_schema=False)
def uploads_clear(month: str, request: Request):
    """Take the added files away again, to start the month over."""
    _guard(request)
    try:
        close_upload.clear(month)
        return {"ok": True, "files": []}
    except close_upload.Rejected as e:
        return _refuse(e)


@app.post("/api/close/{month}/run", include_in_schema=False)
def close_run(month: str, request: Request):
    """Run the month's close again on its last inboxes plus the added files; the pages are rebuilt."""
    _guard(request)
    try:
        ok, log = close_upload.rerun(month)
    except close_upload.Rejected as e:
        return _refuse(e)
    return JSONResponse({"ok": ok, "log": log.strip().splitlines()[-12:]}, status_code=200 if ok else 422)


# Mounted last so /healthz and /api win; html=True serves index.html for a folder (/, /scorecard/, /pulse/).
app.mount("/", ReportFiles(directory=REPORTS, html=True, check_dir=False), name="reports")

if __name__ == "__main__":
    import uvicorn

    if not (REPORTS / "index.html").exists():
        print(f"server: {REPORTS / 'index.html'} doesn't exist yet; run `python -m reports.run_scheduled "
              "--from 2026-09-30 --to 2026-10-04` (or run_nightly) first")
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")))
