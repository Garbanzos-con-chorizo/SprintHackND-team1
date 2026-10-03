"""End to end: CSV, Excel and a mock scraper payload all become the same canonical records."""
import json
from pathlib import Path

from engine.contract import COLUMNS
from engine.ingest import (DataIngestAdapter, EmailAttachmentAdapter, MockScraperAdapter,
                           NormalizedBatch, ingest)

FIXTURES = Path(__file__).parent / "fixtures"

EBAY_CSV = (
    '"Transaction report"\n\n'
    '"Transaction creation date","Type","Order number","Buyer username","Item subtotal",'
    '"Final Value Fee - fixed","Final Value Fee - variable"\n'
    '"Oct 2, 2026","Order","25-1","csvbuyer","33.99","-0.30","-5.30"\n'
)

AMAZON_CSV = (
    '"date/time","type","order id","sku","product sales","selling fees"\n'
    '"Oct 2, 2026 9:33:00 AM PDT","Order","111-1","BK-1","14.49","-4.57"\n'
)


def make_inbox(tmp_path) -> Path:
    from openpyxl import Workbook

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "ebay_transactions_2026-10-02.csv").write_text(EBAY_CSV, encoding="utf-8")
    (inbox / "amazon_daterange_2026-10-02.csv").write_text(AMAZON_CSV, encoding="utf-8")
    wb = Workbook()
    ws = wb.active
    ws.append(["ShopGoodwill.com - Seller Order Export"])
    ws.append(["Order #", "Buyer", "Close Date", "Winning Bid"])
    ws.append(["SG-1", "rustyhound", "10/2/26 8:02 AM", 39])
    wb.save(inbox / "ShopGoodwill_Orders_2026-10-02.xlsx")
    return inbox


def test_csv_files_normalize(tmp_path):
    batch = EmailAttachmentAdapter(make_inbox(tmp_path)).fetch_and_normalize()
    by_source = {r["source"]: r for r in batch.rows}
    assert by_source["ebay"]["gross_cents"] == 3399 and by_source["ebay"]["fee_cents"] == 560
    assert by_source["amazon"]["gross_cents"] == 1449 and by_source["amazon"]["customer_basis"] == "order"


def test_excel_file_normalizes(tmp_path):
    batch = EmailAttachmentAdapter(make_inbox(tmp_path)).fetch_and_normalize()
    sg = next(r for r in batch.rows if r["source"] == "shopgoodwill")
    assert (sg["order_id"], sg["gross_cents"], sg["business_date"], sg["customer_id"]) == ("SG-1", 3900, "2026-10-02", "rustyhound")
    assert batch.warnings == []


def test_mock_scraper_payload_from_fixture_file_normalizes():
    batch = MockScraperAdapter("ebay", FIXTURES / "mock_scraper_ebay.json").fetch_and_normalize("2026-10-02")
    assert [r["txn_id"] for r in batch.rows] == ["ebay:88-0001:sale", "ebay:88-0002:sale", "ebay:88-0002:refund"]
    assert [r["gross_cents"] for r in batch.rows] == [1999, 4500, -4500]
    assert batch.rows[0]["source_file"] == "mock_scraper_ebay.json"
    assert batch.warnings == []


def test_mock_scraper_accepts_records_passed_directly():
    records = json.loads((FIXTURES / "mock_scraper_ebay.json").read_text(encoding="utf-8"))[:1]
    assert len(MockScraperAdapter("ebay", records).fetch_and_normalize().rows) == 1


def test_all_adapters_produce_one_unified_record_format(tmp_path):
    adapters = [EmailAttachmentAdapter(make_inbox(tmp_path)),
                MockScraperAdapter("ebay", FIXTURES / "mock_scraper_ebay.json")]
    batch = ingest(adapters)
    assert {r["source"] for r in batch.rows} == {"ebay", "amazon", "shopgoodwill"}
    assert len(batch.rows) == 3 + 3          # inbox: 3 files, 1 row each; scraper: 3 records
    assert all(list(r) == COLUMNS for r in batch.rows)                      # identical shape from every source
    assert all(isinstance(r["gross_cents"], int) and isinstance(r["fee_cents"], int) for r in batch.rows)
    assert all(r["business_date"] == "2026-10-02" for r in batch.rows)


def test_same_transaction_from_file_and_scraper_counts_once(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "ebay_transactions_2026-10-02.csv").write_text(
        '"Transaction creation date","Type","Order number","Buyer username","Item subtotal",'
        '"Final Value Fee - fixed","Final Value Fee - variable"\n'
        '"Oct 2, 2026","Order","88-0001","scrapebuyer1","19.99","-0.30","-2.60"\n', encoding="utf-8")
    batch = ingest([EmailAttachmentAdapter(inbox), MockScraperAdapter("ebay", FIXTURES / "mock_scraper_ebay.json")])
    assert sorted(r["txn_id"] for r in batch.rows) == ["ebay:88-0001:sale", "ebay:88-0002:refund", "ebay:88-0002:sale"]
    assert sum(w["kind"] == "duplicate" for w in batch.warnings) == 1


def test_bad_inputs_become_warnings_not_crashes(tmp_path):
    inbox = make_inbox(tmp_path)
    (inbox / "old_report.xls").write_bytes(b"\xd0\xcf\x11\xe0")          # legacy Excel: unsupported, but reported
    (inbox / "mystery.csv").write_text("foo,bar\n1,2\n", encoding="utf-8")
    batch = ingest([EmailAttachmentAdapter(inbox), MockScraperAdapter("nosuchsource", [{"a": 1}])])
    files = {w["source_file"] for w in batch.warnings}
    assert {"old_report.xls", "mystery.csv"} <= files and "nosuchsource_scrape.json" in files
    assert len(batch.rows) == 3                                           # the good files still came through


def test_a_new_adapter_plugs_in_with_one_method():
    class ErpDrop(DataIngestAdapter):
        name = "erp"

        def fetch_and_normalize(self, business_date=None):
            row = dict.fromkeys(COLUMNS, "")
            row.update(txn_id="erp:1:sale", source="erp", marketplace="other", type="sale", order_id="1",
                       business_date="2026-10-02", customer_basis="order", gross_cents=500, fee_cents=0,
                       source_file="erp.json", source_row=1)
            return NormalizedBatch(rows=[row])

    batch = ingest([ErpDrop(), MockScraperAdapter("ebay", FIXTURES / "mock_scraper_ebay.json")])
    assert {r["source"] for r in batch.rows} == {"erp", "ebay"}
