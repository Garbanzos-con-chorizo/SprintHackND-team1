"""Decision 008: server.py serves reports/ as static files, computes nothing, and serves nothing else."""
import json
import socket
import threading
import time
import urllib.error
import urllib.request

import pytest

pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")


@pytest.fixture
def site(tmp_path, monkeypatch):
    """server.py over a temporary reports/ folder, on a free local port."""
    reports = tmp_path / "reports"
    (reports / "scorecard").mkdir(parents=True)
    (reports / "index.html").write_text("<h1>portal</h1>", encoding="utf-8")
    (reports / "scorecard" / "index.html").write_text("<h1>scorecards</h1>", encoding="utf-8")
    (reports / "scorecard" / "month-2026-09.csv").write_text("Period type\nmonth\n", encoding="utf-8")
    (reports / "scorecard" / "month-2026-09.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "secret.txt").write_text("outside reports/", encoding="utf-8")
    (reports / "config").mkdir()
    (reports / "config" / "subscribers.csv").write_text("Name,Email\nCOO,coo@example.org\n", encoding="utf-8")
    (reports / "run_nightly.py").write_text("print('code')", encoding="utf-8")
    (reports / "scorecard" / ".gitignore").write_text("*", encoding="utf-8")
    monkeypatch.setenv("REPORTS_DIR", str(reports))
    import importlib, server
    importlib.reload(server)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", reports
    srv.should_exit = True
    thread.join(5)


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""


def call(method, url, body=None, header=True):
    """A PUT, POST or DELETE as the portal's panel sends it; returns (status, parsed JSON)."""
    req = urllib.request.Request(url, data=body, method=method, headers={"X-Reports": "1"} if header else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def test_decision_010_files_can_be_added_and_the_close_run_again(site, tmp_path, monkeypatch):
    base, _ = site
    from reports import close_upload
    monkeypatch.setattr(close_upload, "UPLOADS", tmp_path / "uploads")
    ran = []
    monkeypatch.setattr(close_upload, "rerun", lambda month: ran.append(month) or (True, "close: ok\nposting: NOT POSTED"))
    api = base + "/api/close/2026-09"
    assert json.loads(get(api + "/uploads")[2]) == {"enabled": True, "month": "2026-09", "files": []}
    assert call("PUT", api + "/uploads/late%20report.csv", b"a,b\n1,2\n") == (200, {"ok": True, "files": ["late report.csv"]})
    assert (tmp_path / "uploads" / "2026-09" / "late report.csv").read_bytes() == b"a,b\n1,2\n"
    assert call("POST", api + "/run") == (200, {"ok": True, "log": ["close: ok", "posting: NOT POSTED"]}) and ran == ["2026-09"]
    assert call("DELETE", api + "/uploads") == (200, {"ok": True, "files": []})
    assert not (tmp_path / "uploads" / "2026-09").exists()


def test_decision_010_refuses_other_files_other_sites_and_bad_months(site, tmp_path, monkeypatch):
    base, reports = site
    from reports import close_upload
    monkeypatch.setattr(close_upload, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(close_upload, "rerun", lambda month: pytest.fail("the close must not run"))
    api = base + "/api/close/2026-09"
    for name in ("run.exe", "page.html", ".env.csv"):
        status, answer = call("PUT", api + "/uploads/" + name, b"x")
        assert status == 400 and answer["ok"] is False, name
    assert call("PUT", base + "/api/close/2026-99/uploads/a.csv", b"x")[0] == 400
    # Without the header (what a page on another site could send) nothing changes.
    assert call("PUT", api + "/uploads/a.csv", b"x", header=False)[0] == 403
    assert call("POST", api + "/run", header=False)[0] == 403
    assert call("DELETE", api + "/uploads", header=False)[0] == 403
    assert not (tmp_path / "uploads").exists()
    assert list(reports.rglob("a.csv")) == []     # nothing is ever written under reports/ by an upload


def test_serves_the_portal_folders_and_downloads(site):
    base, _ = site
    assert get(base + "/")[2] == b"<h1>portal</h1>"
    assert get(base + "/scorecard/")[2] == b"<h1>scorecards</h1>"
    status, ctype, body = get(base + "/scorecard/month-2026-09.pdf")
    assert (status, ctype, body) == (200, "application/pdf", b"%PDF-1.4")
    assert get(base + "/scorecard/month-2026-09.csv")[1].startswith("text/csv")


def test_nothing_outside_reports_and_no_api_pages(site):
    base, _ = site
    assert get(base + "/../secret.txt")[0] == 404
    assert get(base + "/%2e%2e/secret.txt")[0] == 404
    for path in ("/docs", "/openapi.json", "/missing.html"):
        assert get(base + path)[0] == 404, path


def test_healthz_says_whether_the_portal_exists(site):
    base, reports = site
    assert json.loads(get(base + "/healthz")[2]) == {"ok": True, "portal": True}
    (reports / "index.html").unlink()
    assert json.loads(get(base + "/healthz")[2]) == {"ok": True, "portal": False}


def test_the_generators_code_and_config_are_not_served(site):
    base, _ = site
    for path in ("/config/subscribers.csv", "/run_nightly.py", "/scorecard/.gitignore", "/config/"):
        assert get(base + path)[0] == 404, path
