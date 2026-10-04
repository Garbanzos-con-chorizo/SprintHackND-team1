"""V3.1: occurred_at in transactions.csv (transaction.md v0.5), the moment the close needs to rebuild
payout windows that run on Pacific days while business_date is Eastern."""
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.clean import parse_moment
from engine.cli import run
from engine.contract import COLUMNS

ROOT = Path(__file__).resolve().parents[2]
MESSY = ROOT / "data" / "sample" / "messy_month"
PACIFIC = ZoneInfo("America/Los_Angeles")


def engine_rows(tmp_path, files, date="2026-10-02"):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, text in files.items():
        (inbox / name).write_text(text, encoding="utf-8")
    run(inbox, tmp_path / "out", date)
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COLUMNS
        return {r["txn_id"]: r for r in reader}


def test_occurred_at_is_the_last_column():
    assert COLUMNS[-2:] == ["units", "occurred_at"]


def test_parse_moment_keeps_the_offset_it_was_written_in():
    assert parse_moment("Sep 1, 2026 1:28:05 AM PDT") == ("2026-09-01", "2026-09-01T01:28:05-07:00")
    # Late Pacific evening is the next Eastern business day; the moment keeps its own offset.
    assert parse_moment("Sep 14, 2026 10:30:00 PM PDT") == ("2026-09-15", "2026-09-14T22:30:00-07:00")
    assert parse_moment("2026-10-02T02:10:00Z") == ("2026-10-01", "2026-10-02T02:10:00+00:00")
    assert parse_moment("2026-09-01 08:18:06", assume_tz="America/Los_Angeles") == (
        "2026-09-01", "2026-09-01T08:18:06-07:00")
    assert parse_moment(datetime(2026, 9, 1, 8, 18, 6), assume_tz="America/Los_Angeles")[1] == "2026-09-01T08:18:06-07:00"
    assert parse_moment("2026-09-01 08:18:06") == ("2026-09-01", "2026-09-01T08:18:06-04:00")  # naive: Eastern
    assert parse_moment("Sep 1, 2026") == ("2026-09-01", "")   # a date alone has no moment
    assert parse_moment("2-Oct-26") == ("2026-10-02", "")


def test_date_only_export_leaves_it_empty_and_several_lines_take_the_first_time(tmp_path):
    rows = engine_rows(tmp_path, {
        "ebay_2026-10-02.csv": (
            '"Transaction creation date","Type","Order number","Buyer username","Item subtotal"\n'
            '"Oct 2, 2026","Order","20-1","ann","10.00"\n'),
        "amazon_2026-10-02.csv": (
            '"date/time","type","order id","product sales","quantity"\n'
            '"Oct 2, 2026 9:15:00 AM PDT","Order","111-1","5.00","1"\n'
            '"Oct 2, 2026 9:16:30 AM PDT","Order","111-1","7.00","1"\n'),
    })
    assert rows["ebay:20-1:sale"]["occurred_at"] == ""
    amazon = rows["amazon:111-1:sale"]
    assert amazon["gross_cents"] == "1200" and amazon["occurred_at"] == "2026-10-02T09:15:00-07:00"


def test_messy_month_rebuilds_every_pacific_payout_window(tmp_path):
    """gross + shipping + handling - fee over the rows whose occurred_at, read in Pacific time, falls in
    the window equals the answer key's net_in_files_cents (Amazon 2 payouts, ShopGoodwill 4)."""
    key = json.loads((MESSY / "expected.json").read_text(encoding="utf-8"))["close"]["payouts"]
    run(MESSY / "inbox", tmp_path, "2026-09-30")
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["marketplace"] in ("amazon", "shopgoodwill")]
    assert rows and all(r["occurred_at"] for r in rows)

    def net(r):
        return int(r["gross_cents"]) + int(r["shipping_cents"]) + int(r["handling_cents"]) - int(r["fee_cents"])

    windows = [p for p in key if p["source"] in ("amazon", "shopgoodwill")]
    got = {}
    for p in windows:
        got[(p["source"], p["activity_from"])] = sum(
            net(r) for r in rows if r["marketplace"] == p["source"]
            and p["activity_from"] <= datetime.fromisoformat(r["occurred_at"]).astimezone(PACIFIC).date().isoformat()
            <= p["activity_to"])
        assert got[(p["source"], p["activity_from"])] == p["net_in_files_cents"], p["id"]
    assert got == {  # the six sums in docs/PLAN_PHASE_3.md, V3.1
        ("amazon", "2026-09-01"): 405_400, ("amazon", "2026-09-15"): 415_074,
        ("shopgoodwill", "2026-09-01"): 1_088_878, ("shopgoodwill", "2026-09-07"): 1_344_329,
        ("shopgoodwill", "2026-09-14"): 1_329_924, ("shopgoodwill", "2026-09-21"): 1_370_702,
    }
