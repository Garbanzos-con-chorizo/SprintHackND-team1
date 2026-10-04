"""V3.6: the close email to accounting: the page and the four CSVs attached, generated, never sent."""
import csv
from datetime import date
from email import message_from_bytes, policy
from pathlib import Path

from reports import email_gen

MONTH = "2026-09"
CONTROL = ("Source,Path,Revenue In,Revenue Posted,Difference,Receivable Posted,Deposits,Open Balance,Explained,Unexplained,Status\n"
           "eBay,Journal,19957.35,19957.35,0.00,18488.89,17023.33,1465.56,1465.56,0.00,OPEN\n"
           "Amazon,Journal,9434.51,9434.51,0.00,8721.06,4054.00,4667.06,4667.06,0.00,INCOMPLETE\n")
EXCEPTIONS = ("Kind,Source,Amount,Effect,Detail,Owner,Action\n"
              "payout_data_gap,Amazon,-743.10,open_balance,paid more than the files hold,E-commerce,Download the report\n"
              "in_transit,eBay,511.62,open_balance,paid not yet in the bank,Accounting,None\n"
              "in_transit,Amazon,4893.84,open_balance,paid not yet in the bank,Accounting,None\n")
PAGE = ('<html><body><p class="summary alert">25 journal documents, all balanced to 0.00; '
        'eBay OPEN, Amazon INCOMPLETE; 3 exceptions.</p></body></html>')


def build_close(root: Path) -> None:
    folder = root / "close" / MONTH
    folder.mkdir(parents=True)
    (root / "close" / f"{MONTH}.html").write_text(PAGE, encoding="utf-8")
    for name, text in (("general_journal", "Posting Date\n"), ("ar_invoice", "Document No.\n"),
                       ("control_totals", CONTROL), ("exceptions", EXCEPTIONS)):
        (folder / f"{name}_{MONTH}.csv").write_text(text, encoding="utf-8")


def subscribers(tmp_path: Path) -> Path:
    path = tmp_path / "subscribers.csv"
    path.write_text("Name,Email,Report_Type,Status\n"
                    "Accounting (sample),accounting@example.org,Close,Active\n"
                    "Controller (sample),controller@example.org,close,Active\n"
                    "Old address,old@example.org,Close,Inactive\n"
                    "COO (sample),coo@example.org,Monthly,Active\n", encoding="utf-8")
    return path


def test_one_close_email_per_active_subscriber_with_the_page_and_the_four_csvs(tmp_path):
    build_close(tmp_path / "reports")
    written, problems = email_gen.distribute(date(2026, 10, 1), close=MONTH, subscribers=subscribers(tmp_path),
                                             outbox=tmp_path / "outbox", root=tmp_path / "reports")
    assert problems == []
    assert [(w["Report_Type"], w["Email"]) for w in written] == [
        ("Close", "accounting@example.org"), ("Close", "controller@example.org")]
    assert written[0]["Attachments"] == ("2026-09.html; general_journal_2026-09.csv; ar_invoice_2026-09.csv; "
                                         "control_totals_2026-09.csv; exceptions_2026-09.csv")
    path = tmp_path / "outbox" / "2026-10-01" / "close-accounting-example-org.eml"
    msg = message_from_bytes(path.read_bytes(), policy=policy.default)
    assert msg["X-Unsent"] == "1" and "accounting@example.org" in msg["To"]  # a draft: nothing is sent
    assert msg["Subject"] == "Month-end close - September 2026 - not posted - eBay OPEN, Amazon INCOMPLETE"
    assert [p.get_content_type() for p in msg.iter_attachments()] == ["text/html"] + ["text/csv"] * 4
    html = msg.get_body(preferencelist=("html",)).get_content()
    # It says what it is, and the numbers are the close's own.
    assert "Not posted." in html and "Synthetic sample data" in html and "placeholder account numbers" in html
    assert "INCOMPLETE" in html and "$4,667.06" in html and "$0.00" in html
    assert "3 exceptions to review: 2 in transit, 1 payout data gap" in html
    plain = msg.get_body(preferencelist=("plain",)).get_content()
    assert "Not posted" in plain and "Synthetic sample data" in plain
    with open(tmp_path / "outbox" / "2026-10-01" / "manifest.csv", encoding="utf-8", newline="") as f:
        assert [r["Report_Type"] for r in csv.DictReader(f)] == ["Close", "Close"]


def test_a_close_that_was_not_built_sends_nothing_and_says_so(tmp_path):
    written, problems = email_gen.distribute(date(2026, 10, 1), close=MONTH, subscribers=subscribers(tmp_path),
                                             outbox=tmp_path / "outbox", root=tmp_path / "reports")
    assert written == [] and problems == ["Close report 2026-09 not found; its subscribers get nothing"]


def test_the_shipped_subscriber_list_has_an_active_close_subscriber():
    active, problems = email_gen.load_subscribers()
    assert problems == []
    assert [s["email"] for s in active if s["type"] == "Close"] == ["accounting@example.org"]
