"""V2.6: internal_api pull into the store, and its place in store backfill and store status."""
from pathlib import Path

import pytest

from engine.internal_api import InternalApiError, MockInternalApi
from engine.internal_api.cli import main as pull_main
from engine.internal_api.pull import PullError, pull_day
from engine.store import connect
from engine.store.backfill import backfill
from engine.store.status import format_status, store_status

ROOT = Path(__file__).resolve().parents[2]
CLEAN_MONTH = ROOT / "data" / "sample" / "clean_month"
DAY = "2026-09-14"


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "ecom.db")
    yield c
    c.close()


def add_pulse(conn, day=DAY, revenue={"shopgoodwill": 87200, "ebay": 57676, "amazon": None}):
    with conn:
        conn.executemany("INSERT INTO pulse_daily (business_date, marketplace, status, revenue_cents, run_id) "
                         "VALUES (?, ?, ?, ?, 'r')",
                         [(day, mk, "ok" if c is not None else "missing", c) for mk, c in revenue.items()])


def internal(conn, day=DAY):
    return conn.execute("SELECT metric, dimension, value, unit, source FROM internal_daily "
                        "WHERE business_date = ? ORDER BY metric, dimension", (day,)).fetchall()


def test_pull_stores_the_snapshot_and_categories_add_up_to_the_stored_revenue(conn):
    add_pulse(conn)
    s = pull_day(conn, DAY)
    assert (s["metrics"], s["source"], s["note"]) == (10, "mock", "")
    assert s["rows"] == len(internal(conn))
    sales = conn.execute("SELECT SUM(value) FROM internal_daily WHERE business_date = ? "
                         "AND metric = 'category_sales_cents'", (DAY,)).fetchone()[0]
    assert sales == 87200 + 57676  # only the marketplaces with data (amazon is missing)
    assert conn.execute("SELECT command, result, rows_written FROM runs").fetchone() == ("pull", "ok", s["rows"])


def test_rerunning_a_pull_leaves_the_same_rows(conn):
    add_pulse(conn)
    pull_day(conn, DAY)
    first = internal(conn)
    pull_day(conn, DAY)
    assert internal(conn) == first


def test_pull_before_load_has_no_category_rows_and_says_so(conn):
    s = pull_day(conn, DAY)
    assert s["category_rows"] == 0 and "run store load first" in s["note"]
    assert not [r for r in internal(conn) if r[0].startswith("category_")]
    assert ("employees", "total") in [(r[0], r[1]) for r in internal(conn)]


def test_a_failed_pull_changes_nothing_but_the_runs_log(conn):
    add_pulse(conn)
    pull_day(conn, DAY)
    before = internal(conn)

    class Down:
        def get(self, endpoint, day):
            raise InternalApiError("GET http://api/labor failed: timed out")

    with pytest.raises(PullError, match="timed out"):
        pull_day(conn, DAY, api=Down())
    assert internal(conn) == before
    assert conn.execute("SELECT result FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()[0] == "failed"


def test_pull_spreads_the_stored_units_sold(conn):
    add_pulse(conn)
    with conn:
        conn.executemany("INSERT INTO transactions (txn_id, source, marketplace, type, business_date, order_id, "
                         "customer_basis, gross_cents, units, source_file, source_row, run_id) "
                         "VALUES (?, 'ebay', 'ebay', ?, ?, ?, 'order', 100, ?, 'f', 1, 'r')",
                         [("a", "sale", DAY, "1", 3), ("b", "sale", DAY, "2", None), ("c", "refund", DAY, "1", 0)])
    pull_day(conn, DAY)
    n = conn.execute("SELECT SUM(value) FROM internal_daily WHERE business_date = ? AND metric = 'listing_to_sale_days'",
                     (DAY,)).fetchone()[0]
    assert n == 4  # 3 units, plus 1 for the order with no unit count; refunds don't count


def test_other_dates_are_untouched(conn):
    add_pulse(conn, "2026-09-13")
    add_pulse(conn)
    pull_day(conn, "2026-09-13")
    pull_day(conn, DAY, api=MockInternalApi())
    assert internal(conn, "2026-09-13") and internal(conn)
    assert len({r[0] for r in internal(conn, "2026-09-13")}) == 10


def test_pull_cli_for_a_range(tmp_path, capsys):
    db = str(tmp_path / "p.db")
    assert pull_main(["--db", db, "pull", "--from", "2026-09-01", "--to", "2026-09-03"]) == 0
    out = capsys.readouterr().out
    assert "3 of 3 days pulled" in out and "run store load first" in out


def test_backfill_pulls_each_day_and_status_reports_it(conn, tmp_path):
    results = backfill(conn, CLEAN_MONTH / "inbox", tmp_path / "out", "2026-09-01", "2026-09-03")
    assert [r["result"] for r in results] == ["ok"] * 3
    assert all(r["internal_rows"] > 50 for r in results)
    for r in results:  # category sales add up to the day's revenue, as loaded from the files
        sales = conn.execute("SELECT SUM(value) FROM internal_daily WHERE business_date = ? "
                             "AND metric = 'category_sales_cents'", (r["date"],)).fetchone()[0]
        assert sales == r["revenue_cents"]
    # the day before the range has its snapshot too (stock count for sell-through), without a pulse
    assert conn.execute("SELECT COUNT(*) FROM internal_daily WHERE business_date = '2026-08-31' "
                        "AND metric = 'active_listings_by_age'").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM pulse_daily WHERE business_date = '2026-08-31'").fetchone()[0] == 0
    s = store_status(conn, "2026-09-01", "2026-09-05")
    assert s["internal"] == {"days": 3, "missing": ["2026-09-04", "2026-09-05"], "sources": ["mock"]}
    assert "internal API snapshot: 3 of 5 days (source mock: simulated); missing: 2026-09-04..2026-09-05" \
        in format_status(s)
