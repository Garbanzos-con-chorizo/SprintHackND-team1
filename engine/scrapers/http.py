"""HTTP client for portal APIs: a cookie-keeping session on the standard library, no extra dependency.

Used to call a portal's API (request or download a report). Pass an Authorization header for token APIs.
"""
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class HttpError(Exception):
    pass


class HttpSession:
    def __init__(self, base_url: str = "", headers: dict[str, str] | None = None, timeout: float = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookies = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.headers = {"User-Agent": "Mozilla/5.0 (engine/portal-fetch)", **(headers or {})}

    def _url(self, path: str) -> str:
        return path if path.startswith(("http://", "https://")) else f"{self.base_url}/{path.lstrip('/')}"

    def request(self, method: str, path: str, data: dict | bytes | None = None,
                headers: dict[str, str] | None = None) -> tuple[int, bytes, dict[str, str]]:
        body = None
        hdrs = {**self.headers, **(headers or {})}
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode()
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif data is not None:
            body = data
        req = urllib.request.Request(self._url(path), data=body, headers=hdrs, method=method)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            raise HttpError(f"{method} {path} -> HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise HttpError(f"{method} {path} failed: {exc.reason}") from exc

    def get(self, path: str, **kw):
        return self.request("GET", path, **kw)

    def post(self, path: str, data: dict | bytes | None = None, **kw):
        return self.request("POST", path, data=data, **kw)

    def download(self, path: str, dest: Path, method: str = "GET", data: dict | None = None) -> Path:
        _, body, _ = self.request(method, path, data=data)
        if not body:
            raise HttpError(f"{path} returned an empty body")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        return dest
