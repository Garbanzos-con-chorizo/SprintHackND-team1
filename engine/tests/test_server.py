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
