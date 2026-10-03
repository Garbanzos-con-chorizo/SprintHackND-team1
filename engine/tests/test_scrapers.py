import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from engine.cli import fetch
from engine.scrapers.base import NotConfigured, Scraper, load_scrapers
from engine.scrapers.env import load_env
from engine.scrapers.http import HttpError, HttpSession
from engine.scrapers.runner import run_scrapers


class Good(Scraper):
    source = "good"

    def fetch(self, business_date, dest_dir, env):
        p = self.target(dest_dir, business_date, ".csv")
        p.write_text("Order ID,Total\n1,5\n", encoding="utf-8")
        return [p]


class NeedsKeys(Scraper):
    source = "needs_keys"
    env_keys = ("PORTAL_USER",)


class Skeleton(Scraper):
    source = "skeleton"

    def fetch(self, business_date, dest_dir, env):
        raise NotConfigured("selectors not recorded")


class Boom(Scraper):
    source = "boom"

    def fetch(self, business_date, dest_dir, env):
        raise RuntimeError("layout changed")


def test_runner_records_each_outcome_and_continues(tmp_path):
    log = run_scrapers([Boom(), NeedsKeys(), Skeleton(), Good()], "2026-10-02", tmp_path, env={})
    s = log["sources"]
    assert s["good"] == {"status": "ok", "files": ["good_2026-10-02.csv"], "detail": ""}
    assert s["needs_keys"]["status"] == "not_configured" and "PORTAL_USER" in s["needs_keys"]["detail"]
    assert s["skeleton"]["status"] == "not_configured"
    assert s["boom"]["status"] == "failed" and "layout changed" in s["boom"]["detail"]
    assert (tmp_path / "good_2026-10-02.csv").exists()


def test_runner_only_filter(tmp_path):
    log = run_scrapers([Good(), Boom()], "2026-10-02", tmp_path, env={}, only="good")
    assert list(log["sources"]) == ["good"]


def test_fetch_command_writes_log_and_exit_code(tmp_path):
    out = tmp_path / "out"
    assert fetch(tmp_path / "inbox", out, "2026-10-02", scrapers=[Good(), Skeleton()], env={}) == 0
    assert json.loads((out / "fetch_log.json").read_text(encoding="utf-8"))["sources"]["good"]["status"] == "ok"
    assert fetch(tmp_path / "inbox", out, "2026-10-02", scrapers=[Boom()], env={}) == 1


def test_builtin_scrapers_load_and_upright_stub_is_not_configured(tmp_path):
    scrapers = load_scrapers()
    assert "upright" in {s.source for s in scrapers}
    env = {"UPRIGHT_URL": "x", "UPRIGHT_TOKEN": "t"}
    log = run_scrapers(scrapers, "2026-10-02", tmp_path, env, only="upright")
    assert log["sources"]["upright"]["status"] == "not_configured"


def test_load_env_reads_file_and_environment_wins(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("# c\nA=1\nB='two'\nC = \"3\"\n", encoding="utf-8")
    monkeypatch.setenv("B", "from-env")
    env = load_env(f)
    assert (env["A"], env["B"], env["C"]) == ("1", "from-env", "3")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))  # consume the body, or Windows resets the socket
        self.send_response(200)
        self.send_header("Set-Cookie", "sid=abc; Path=/")
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self):
        if self.path == "/report.csv" and "sid=abc" in (self.headers.get("Cookie") or ""):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Order ID,Total\n1,5\n")
        else:
            self.send_response(403)
            self.end_headers()


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_http_session_keeps_login_cookie_and_downloads(server, tmp_path):
    http = HttpSession(base_url=server)
    with pytest.raises(HttpError):
        http.download("/report.csv", tmp_path / "x.csv")  # not logged in yet
    http.post("/login", {"user": "u"})
    dest = http.download("/report.csv", tmp_path / "x.csv")
    assert dest.read_text() == "Order ID,Total\n1,5\n"
