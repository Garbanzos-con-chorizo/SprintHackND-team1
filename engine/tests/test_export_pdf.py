"""V2.9: the scorecard page printed to a one-page PDF with a browser already on the machine."""
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
