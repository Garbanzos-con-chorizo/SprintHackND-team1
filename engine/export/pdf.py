"""export pdf (V2.9): the scorecard page printed to a one-page PDF with a browser already on the machine.

No new dependency (decision 007 point 6): Edge ships with Windows, and Chrome or Chromium print the
same way. The page is Orlando's `reports/scorecard/<type>-<id>.html`, whose print stylesheet fits one
landscape letter page; if it isn't there yet, `python -m reports.scorecard` renders it first. Nothing
is computed here, so the PDF shows exactly the numbers of the page and the CSV.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Looked for in this order; PDF_BROWSER (a path) wins over all of them.
BROWSER_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
BROWSER_NAMES = ["msedge", "microsoft-edge", "google-chrome", "chrome", "chromium", "chromium-browser"]
NO_BROWSER = ("no Edge, Chrome or Chromium found (set PDF_BROWSER to its path). Fallback: open the page "
              "in any browser, Print, Save as PDF; the page is laid out for one landscape page.")


class PdfError(Exception):
    pass


def find_browser(env=None, exists=os.path.isfile, which=shutil.which) -> str | None:
    env = os.environ if env is None else env
    if env.get("PDF_BROWSER"):
        return env["PDF_BROWSER"] if exists(env["PDF_BROWSER"]) else None
    for path in BROWSER_PATHS:
        if exists(path):
            return path
    for name in BROWSER_NAMES:
        found = which(name)
        if found:
            return found
    return None


def scorecard_page(kpi_path: Path, dest: Path) -> Path:
    """The scorecard page for a KPI file, rendered again by Orlando's command every time, so the PDF
    always shows the KPI file it was asked for (never an older page left in the folder)."""
    import json
    period = json.loads(Path(kpi_path).read_text(encoding="utf-8"))["period"]
    page = Path(dest) / f"{period['type']}-{period['id']}.html"
    done = subprocess.run([sys.executable, "-m", "reports.scorecard", "--kpi-file", str(Path(kpi_path).resolve()),
                           "--dest", str(Path(dest).resolve())], cwd=ROOT, capture_output=True, text=True)
    if done.returncode or not page.exists():
        raise PdfError(f"could not render the scorecard page: {(done.stderr or done.stdout).strip()}")
    return page


# Tried in order: the current headless mode, then the old one (older Edge, some locked-down PCs).
HEADLESS_MODES = ["--headless=new", "--headless"]


def print_pdf(page: Path, target: Path, browser: str | list[str], timeout: float = 90, settle: float = 10) -> Path:
    """Print `page` to `target` with a headless Chromium-family browser; returns the PDF path.

    `browser` is the executable, or a command prefix (a list). On Windows the browser can exit while a
    child process is still writing, so the file is awaited for up to `settle` seconds; if none comes,
    the old headless mode gets one more try. The error names the browser and what each try did."""
    target = Path(target).resolve()
    prefix = [browser] if isinstance(browser, (str, Path)) else list(browser)
    tries = []
    for mode in HEADLESS_MODES:
        target.unlink(missing_ok=True)
        # own profile: works while the user's browser is open; cleanup can't fail on a lingering child
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            cmd = prefix + [mode, "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
                            f"--user-data-dir={profile}", f"--print-to-pdf={target}", Path(page).resolve().as_uri()]
            try:
                done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                tries.append(f"{mode}: no answer in {timeout:.0f} s")
                continue
            if wait_for_pdf(target, settle):
                return target
        detail = (done.stderr or done.stdout).strip().splitlines()
        tries.append(f"{mode}: exit {done.returncode}, no file" + (f" ({detail[-1][:160]})" if detail else ""))
    name = Path(prefix[-1]).name
    raise PdfError(f"{name} wrote no PDF ({'; '.join(tries)}). Inside a sandboxed session, run it from a normal "
                   "terminal; otherwise open the page and use Print, Save as PDF.")


def wait_for_pdf(path: Path, seconds: float) -> bool:
    """True once `path` is a complete PDF that has stopped growing, within `seconds`."""
    deadline, last = time.monotonic() + seconds, -1
    while True:
        size = path.stat().st_size if path.exists() else -1
        if size > 0 and size == last and complete_pdf(path):
            return True
        if time.monotonic() >= deadline:
            return size > 0 and complete_pdf(path)
        last = size
        time.sleep(0.2)


def complete_pdf(path: Path) -> bool:
    data = path.read_bytes()
    return data.startswith(b"%PDF") and b"%%EOF" in data[-1024:]


def page_count(pdf: Path) -> int:
    """Pages in a PDF, counted from its page objects (enough for the browser's own output)."""
    return len(re.findall(rb"/Type\s*/Page(?![a-z])", Path(pdf).read_bytes()))


def write_pdf(kpi_path: Path, dest: Path, browser: str | None = None) -> tuple[Path, int]:
    """<dest>/<type>-<id>.pdf next to the page and the CSV of the same name; returns (path, pages)."""
    browser = browser or find_browser()
    if not browser:
        raise PdfError(NO_BROWSER)
    page = scorecard_page(kpi_path, dest)
    pdf = print_pdf(page, page.with_suffix(".pdf"), browser)
    return pdf, page_count(pdf)
