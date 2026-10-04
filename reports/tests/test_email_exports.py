"""V2.10: the monthly email carries the one-page PDF and the KPI CSV when they were built."""
from pathlib import Path

from reports import email_gen, scorecard

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs" / "contracts" / "examples" / "kpi.sample.month.json"


def test_monthly_email_attaches_the_pdf_and_csv_first(tmp_path):
    scorecard.build(EXAMPLE, tmp_path / "scorecard")
    page = tmp_path / "scorecard" / "month-2026-09.html"
    before = email_gen.payload("Monthly", "2026-09", root=tmp_path)
    assert [p.name for p in before["attachments"]] == ["month-2026-09.html", "month-2026-09.json"]

    page.with_suffix(".pdf").write_bytes(b"%PDF-1.4")
    page.with_suffix(".csv").write_text("Period type\n", encoding="utf-8")
    after = email_gen.payload("Monthly", "2026-09", root=tmp_path)
    assert [p.name for p in after["attachments"]] == ["month-2026-09.pdf", "month-2026-09.csv",
                                                      "month-2026-09.html", "month-2026-09.json"]
    assert "one-page PDF" in after["html"] and "CSV for Excel" in after["html"]
    msg = email_gen.message({"name": "COO", "email": "coo@example.org", "type": "Monthly"}, after,
                            __import__("datetime").datetime(2026, 10, 1, 6, 0).astimezone())
    assert [p.get_content_type() for p in msg.iter_attachments()][:2] == ["application/pdf", "text/csv"]
