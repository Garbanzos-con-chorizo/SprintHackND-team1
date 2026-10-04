"""Simulated provider APIs: `engine fetch --simulate` delivers synthetic reports; the pipeline reads them."""
import csv
import json

import pytest
from openpyxl import Workbook

from engine.cli import fetch, run
from engine.scrapers import simulation
from engine.tools.make_sample import check, check_pulse


def deliver(tmp_path, date):
    """Run the simulators for one date into tmp_path/inbox; return the answer key for that day."""
    code = fetch(tmp_path / "inbox", tmp_path / "out", date, simulate=True)
    assert code == 0
    return simulation.expected_for(date)


@pytest.mark.parametrize("date", ["2026-10-02", "2026-10-03", "2026-11-15"])
def test_simulated_reports_match_the_answer_key(tmp_path, date):
    key = deliver(tmp_path, date)
    ok, lines = check(tmp_path, key)
    assert ok, "\n".join(lines)


def test_through_the_engine_and_the_real_pulse(tmp_path):
    key = deliver(tmp_path, "2026-10-02")
    ok, lines = check_pulse(tmp_path, key)
    assert ok, "\n".join(lines)
    assert not any("stale" in line or "missing" in line for line in lines)   # all four marketplaces have data


def test_all_four_marketplaces_ok_and_nothing_overlaps(tmp_path):
    deliver(tmp_path, "2026-10-02")
    run(tmp_path / "inbox", tmp_path / "out", "2026-10-02")
    status = json.loads((tmp_path / "out" / "source_status.json").read_text(encoding="utf-8"))["sources"]
    assert {k: v["status"] for k, v in status.items()} == {
        "shopgoodwill": "ok", "amazon": "ok", "ebay": "ok", "other": "ok"}
    # the four providers cover their own channels, so no transaction arrives twice
    assert json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8")) == []


def test_the_fetch_log_says_these_are_simulated(tmp_path):
    deliver(tmp_path, "2026-10-02")
    log = json.loads((tmp_path / "out" / "fetch_log.json").read_text(encoding="utf-8"))["sources"]
    assert set(log) == {"upright", "cashmonkey", "amazon", "ebay"}
    assert all(e["status"] == "ok" and e["simulated"] is True and "simulated" in e["detail"] for e in log.values())


def test_without_simulate_the_real_apis_are_still_not_configured(tmp_path):
    fetch(tmp_path / "inbox", tmp_path / "out", "2026-10-02", env={})
    log = json.loads((tmp_path / "out" / "fetch_log.json").read_text(encoding="utf-8"))["sources"]
    assert {e["status"] for e in log.values()} == {"not_configured"}
    assert not list((tmp_path / "inbox").glob("*.xlsx"))     # nothing synthetic slips into a real run


def test_the_same_date_gives_the_same_data(tmp_path):
    for name in ("a", "b"):
        d = tmp_path / name
        fetch(d / "inbox", d / "out", "2026-10-02", simulate=True)
        run(d / "inbox", d / "out", "2026-10-02")
    a = (tmp_path / "a" / "out" / "transactions.csv").read_text(encoding="utf-8")
    b = (tmp_path / "b" / "out" / "transactions.csv").read_text(encoding="utf-8")
    assert a == b and len(a.splitlines()) > 50


def test_files_have_the_names_and_shapes_the_deck_shows(tmp_path):
    deliver(tmp_path, "2026-10-02")
    names = sorted(p.name for p in (tmp_path / "inbox").iterdir())
    assert names == ["amazon_orders_2026-10-02.xlsx", "ebay_orders_2026-10-02.xlsx",
                     "orders2023-20261003-001500-96170.xlsx", "paid_orders_10-02-2026_10-02-2026.xlsx"]


def test_an_evening_sale_lands_on_the_right_eastern_day(tmp_path):
    """Upright stamps Pacific and Cash Monkey stamps UTC; a late evening sale must still count for its Eastern day."""
    deliver(tmp_path, "2026-10-02")
    run(tmp_path / "inbox", tmp_path / "out", "2026-10-02")
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        days = {r["business_date"] for r in csv.DictReader(f)}
    assert days == {"2026-10-02"}


def test_two_identical_units_of_one_order_are_both_counted(tmp_path):
    """Cash Monkey is one line per unit: 2 units of the same item at the same price is 2 identical lines."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    wb = Workbook()
    wb.active.append(["Order Date", "Channel", "Order ID", "SKU", "Quantity", "Item Price", "Market Fees", "Currency"])
    for _ in range(2):
        wb.active.append(["2026-10-02 15:00:00", "eBay", "E-1", "SKU-1", 1, 10.0, 1.5, "USD"])
    wb.save(inbox / "orders2023-20261003-001500-1.xlsx")
    run(inbox, tmp_path / "out", "2026-10-02")
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1 and rows[0]["gross_cents"] == "2000" and rows[0]["fee_cents"] == "300"
    assert json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8")) == []


def test_a_shopgoodwill_order_number_is_never_reused_on_another_day():
    """Two days in one inbox must not look like the same orders (the dedupe would drop the second day)."""
    ids = []
    for d in ("2026-08-01", "2026-08-02", "2026-09-01"):
        orders, _ = simulation.day_orders(d)
        ids += [o.order_id for o in orders if o.marketplace == "shopgoodwill"]
    assert len(ids) == len(set(ids))


def test_fetch_range_writes_every_day_and_loads_as_complete_days(tmp_path):
    from engine.cli import main
    inbox = tmp_path / "inbox"
    assert main(["fetch", "--simulate", "--from", "2026-08-01", "--to", "2026-08-03",
                 "--inbox", str(inbox), "--out", str(tmp_path / "o")]) == 0
    assert len(list(inbox.glob("paid_orders_*"))) == 3
    run(inbox, tmp_path / "out", "2026-08-03")
    status = json.loads((tmp_path / "out" / "source_status.json").read_text(encoding="utf-8"))
    assert status["sources"]["shopgoodwill"]["status"] == "ok"
