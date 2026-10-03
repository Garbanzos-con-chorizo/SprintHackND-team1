"""P-V4: source_status.json says, per marketplace, whether the day's data arrived."""
import json

import pytest

from engine.cli import run

UPRIGHT_HEADER = "Upright Order ID,Channel,Channel Order ID,Channel Buyer,Subtotal,Currency\n"
CM_HEADER = "Order ID,Line ID,Order Date (UTC),Channel,Item Price,Marketplace Fees,Currency\n"


def status_of(tmp_path, files, date="2026-10-02"):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, text in files.items():
        (inbox / name).write_text(text, encoding="utf-8")
    run(inbox, tmp_path / "out", date)
    return json.loads((tmp_path / "out" / "source_status.json").read_text(encoding="utf-8"))["sources"]


def test_empty_inbox_everything_missing(tmp_path):
    s = status_of(tmp_path, {})
    assert {k: v["status"] for k, v in s.items()} == {"shopgoodwill": "missing", "amazon": "missing", "ebay": "missing"}
    assert all(v["files"] == [] and v["rows"] == 0 for v in s.values())


def test_one_cash_monkey_file_feeds_three_marketplaces_independently(tmp_path):
    s = status_of(tmp_path, {
        "orders2023-20261002-1-1.csv": CM_HEADER + "E-1,a,2026-10-02 15:00:00,eBay,10.00,1.00,USD\n",
    })
    assert s["ebay"] == {"status": "ok", "files": ["orders2023-20261002-1-1.csv"], "rows": 1}
    # the same file could have fed Amazon, but had nothing for it today: stale, not missing
    assert s["amazon"]["status"] == "stale" and s["amazon"]["files"] == ["orders2023-20261002-1-1.csv"]
    assert s["shopgoodwill"]["status"] == "missing"          # no Upright file at all


def test_file_for_another_day_is_stale_not_missing(tmp_path):
    s = status_of(tmp_path, {
        "paid_orders_10-01-2026_10-01-2026.csv": UPRIGHT_HEADER + "1,Shopgoodwill,6001,buyer1,20.00,USD\n",
    })
    assert s["shopgoodwill"]["status"] == "stale" and s["shopgoodwill"]["rows"] == 0


def test_ok_lists_only_the_files_that_have_rows_for_the_day(tmp_path):
    s = status_of(tmp_path, {
        "paid_orders_10-01-2026_10-01-2026.csv": UPRIGHT_HEADER + "1,Shopgoodwill,6001,buyer1,20.00,USD\n",
        "paid_orders_10-02-2026_10-02-2026.csv": UPRIGHT_HEADER + "2,Shopgoodwill,6002,buyer2,30.00,USD\n",
    })
    assert s["shopgoodwill"] == {"status": "ok", "files": ["paid_orders_10-02-2026_10-02-2026.csv"], "rows": 1}


def test_unreadable_file_leaves_the_marketplace_missing_and_is_warned(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "paid_orders_10-02-2026_10-02-2026.csv").write_text("", encoding="utf-8")   # empty download
    run(inbox, tmp_path / "out", "2026-10-02")
    status = json.loads((tmp_path / "out" / "source_status.json").read_text(encoding="utf-8"))["sources"]
    warnings = json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8"))
    assert status["shopgoodwill"]["status"] == "missing"
    assert warnings and warnings[0]["kind"] == "unparseable"


def test_other_marketplace_appears_only_when_it_has_rows(tmp_path):
    without = status_of(tmp_path, {})
    assert "other" not in without


def test_other_marketplace_reported_when_goodwillbooks_sells(tmp_path):
    s = status_of(tmp_path, {
        "orders2023-20261002-1-1.csv": CM_HEADER + "G-1,a,2026-10-02 15:00:00,Goodwillbooks,5.00,0.50,USD\n",
    })
    assert s["other"] == {"status": "ok", "files": ["orders2023-20261002-1-1.csv"], "rows": 1}


def test_status_uses_the_eastern_day_not_the_utc_day(tmp_path):
    # 01:30 UTC on Oct 3 is 9:30 PM Eastern on Oct 2
    s = status_of(tmp_path, {
        "orders2023-20261003-1-1.csv": CM_HEADER + "E-1,a,2026-10-03 01:30:00,eBay,10.00,1.00,USD\n",
    }, date="2026-10-02")
    assert s["ebay"]["status"] == "ok"
