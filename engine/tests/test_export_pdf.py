"""V2.9: the scorecard page printed to a one-page PDF with a browser already on the machine."""
import sys
from pathlib import Path

import pytest

from engine.export.cli import main as export_main
from engine.export.pdf import NO_BROWSER, BROWSER_PATHS, PdfError, find_browser, page_count, write_pdf

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs" / "contracts" / "examples"
BROWSER = find_browser()
needs_browser = pytest.mark.skipif(BROWSER is None, reason="no Edge, Chrome or Chromium on this machine")


def test_browser_lookup_order():
    present = {BROWSER_PATHS[2], "C:/custom/msedge.exe"}
    exists = lambda p: p in present
    assert find_browser(env={}, exists=exists, which=lambda n: None) == BROWSER_PATHS[2]
    assert find_browser(env={"PDF_BROWSER": "C:/custom/msedge.exe"}, exists=exists) == "C:/custom/msedge.exe"
    assert find_browser(env={"PDF_BROWSER": "C:/missing.exe"}, exists=exists) is None  # an explicit path is not second-guessed
    linux = find_browser(env={}, exists=lambda p: False, which=lambda n: f"/usr/bin/{n}" if n == "chromium" else None)
    assert linux == "/usr/bin/chromium"
    assert find_browser(env={}, exists=lambda p: False, which=lambda n: None) is None


def test_no_browser_says_how_to_print_by_hand(tmp_path, monkeypatch):
    monkeypatch.setattr("engine.export.pdf.find_browser", lambda: None)
    with pytest.raises(PdfError, match="Save as PDF"):
        write_pdf(EXAMPLES / "kpi.sample.month.json", tmp_path)
    assert "PDF_BROWSER" in NO_BROWSER


def test_page_count(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4 1 0 obj << /Type /Pages /Count 2 >> 2 0 obj << /Type /Page >> 3 0 obj <</Type/Page>>")
    assert page_count(pdf) == 2


@needs_browser
@pytest.mark.parametrize("name", ["kpi.sample.month.json", "kpi.sample.month.partial.json",
                                  "kpi.sample.week.json", "kpi.sample.day.json"])
def test_every_scorecard_prints_on_one_page(tmp_path, name):
    pdf, pages = write_pdf(EXAMPLES / name, tmp_path)
    assert pdf.exists() and pdf.read_bytes().startswith(b"%PDF")
    assert pages == 1
    assert pdf.with_suffix(".html").exists()  # the page it printed sits next to it


@needs_browser
def test_cli_pdf(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert export_main(["pdf", "--kpi-file", str(EXAMPLES / "kpi.sample.day.json"), "--dest", "out"]) == 0
    assert "(1 page)" in capsys.readouterr().out


# --- robustness (Dani's report: "the browser wrote no PDF (exit 0)") with a fake browser -------------

FAKE_BROWSER = '''
import os, subprocess, sys, time
args = sys.argv[1:]
target = next(a.split("=", 1)[1] for a in args if a.startswith("--print-to-pdf="))
mode = os.environ["FAKE_BROWSER"]
pdf = b"%PDF-1.4 fake page /Type /Page %%EOF"
if mode == "late":       # exits 0 at once while a child process writes the file a second later (Windows Edge)
    subprocess.Popen([sys.executable, "-c", "import sys, time; time.sleep(1); open(sys.argv[1], 'wb').write(sys.argv[2].encode())",
                      target, pdf.decode()])
elif mode == "old_only" and "--headless" in args:  # only the old headless mode prints
    open(target, "wb").write(pdf)
elif mode == "never":
    print("[1004:ERROR] printing blocked by policy", file=sys.stderr)
'''


@pytest.fixture
def fake_browser(tmp_path, monkeypatch):
    script = tmp_path / "fake_browser.py"
    script.write_text(FAKE_BROWSER, encoding="utf-8")
    page = tmp_path / "page.html"
    page.write_text("<p>scorecard</p>", encoding="utf-8")

    def run(mode, settle=5):
        monkeypatch.setenv("FAKE_BROWSER", mode)
        from engine.export.pdf import print_pdf
        return print_pdf(page, tmp_path / "out.pdf", [sys.executable, str(script)], timeout=30, settle=settle)
    return run


def test_waits_for_a_pdf_written_after_the_browser_exits(fake_browser):
    assert fake_browser("late").read_bytes().startswith(b"%PDF")


def test_falls_back_to_the_old_headless_mode(fake_browser):
    assert fake_browser("old_only").exists()


def test_says_which_browser_and_what_each_try_did(fake_browser):
    with pytest.raises(PdfError) as e:
        fake_browser("never", settle=0.5)
    text = str(e.value)
    assert "fake_browser.py wrote no PDF" in text
    assert "--headless=new: exit 0, no file" in text and "--headless: exit 0" in text
    assert "printing blocked by policy" in text and "Save as PDF" in text
