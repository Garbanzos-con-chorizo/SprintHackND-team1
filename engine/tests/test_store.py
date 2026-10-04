"""V2.1 / V2.2: the store (engine/store/) against the rules in docs/contracts/store.md."""
import csv
import json
from pathlib import Path

import pytest

from engine.contract import COLUMNS
from engine.store import LoadError, connect, db_path, load_day
from engine.store.cli import main as store_main

ROOT = Path(__file__).resolve().parents[2]
DAY = "2026-09-14"
MARKETPLACES = ["shopgoodwill", "amazon", "ebay", "other"]


def txn(order, day=DAY, marketplace="ebay", gross=1000, fee=100, kind="sale", customer="b1"):
    return {"txn_id": f"{marketplace}:{order}:{kind}", "source": marketplace, "marketplace": marketplace,
            "type": kind, "business_date": day, "order_id": order, "customer_id": customer,
            "customer_basis": "buyer" if customer else "order", "gross_cents": gross, "fee_cents": fee,
            "source_file": f"{marketplace}.csv", "source_row": 1}


def pulse(day=DAY, ebay_revenue=1000):
    no_data = {"status": "missing", **{k: None for k in ("gross_cents", "refunds_cents", "revenue_cents",
                                                          "fees_cents", "orders", "customers", "customer_basis")}}
    ebay = {"status": "ok", "gross_cents": ebay_revenue, "refunds_cents": 0, "revenue_cents": ebay_revenue,
            "fees_cents": 100, "orders": 1, "customers": 1, "customer_basis": "buyer"}
    return {"schema_version": 1, "business_date": day,
            "marketplaces": {m: (ebay if m == "ebay" else dict(no_data)) for m in MARKETPLACES},
            "enterprise": {"revenue_cents": ebay_revenue, "included": ["ebay"]}}


def write_day(out: Path, rows, day=DAY, warnings=(), pulse_doc=None):
    """What `engine run` + `recon.pulse` leave in out/ for one night."""
    (out / "pulse").mkdir(parents=True, exist_ok=True)
    with open(out / "transactions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    (out / "warnings.json").write_text(json.dumps(list(warnings)), encoding="utf-8")
    (out / "source_status.json").write_text(json.dumps(
        {"business_date": day, "sources": {"ebay": {"status": "ok", "files": ["ebay.csv"], "rows": len(rows)}}}),
        encoding="utf-8")
    (out / "pulse" / f"{day}.json").write_text(json.dumps(pulse_doc or pulse(day)), encoding="utf-8")


def snapshot(conn):
    """Everything the readers see, without the bookkeeping (run_id, runs) that a re-run changes."""
    return {
        "transactions": conn.execute("SELECT txn_id, marketplace, type, business_date, order_id, customer_id, "
                                     "gross_cents, fee_cents, units FROM transactions ORDER BY txn_id").fetchall(),
        "pulse_daily": conn.execute("SELECT business_date, marketplace, status, revenue_cents, orders "
                                    "FROM pulse_daily ORDER BY 1, 2").fetchall(),
        "warnings": conn.execute("SELECT business_date, seq, kind, reason FROM warnings ORDER BY 1, 2").fetchall(),
    }


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "store" / "ecom.db")
    yield c
    c.close()


# --- V2.1: path and init ---------------------------------------------------------------------

def test_init_creates_every_table_and_view_and_is_safe_to_repeat(tmp_path):
    path = tmp_path / "nested" / "ecom.db"
    connect(path).close()
    c = connect(path)  # second init on an existing database
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    assert names == {"transactions", "pulse_daily", "internal_daily", "runs", "warnings", "kpi_values",
                     "v_daily", "v_weekly", "v_monthly"}
    assert c.execute("PRAGMA user_version").fetchone()[0] == 1
    c.close()


def test_db_path_explicit_then_setting_then_default(monkeypatch, tmp_path):
    monkeypatch.delenv("ECOM_DB", raising=False)
    assert db_path() == Path("out/store/ecom.db")
    monkeypatch.setenv("ECOM_DB", str(tmp_path / "x.db"))
    assert db_path() == tmp_path / "x.db"
    assert db_path(tmp_path / "y.db") == tmp_path / "y.db"


# --- V2.2: load ------------------------------------------------------------------------------

def test_load_keeps_only_the_date_and_all_four_marketplaces(conn, tmp_path):
    out = tmp_path / "out"
    write_day(out, [txn("A"), txn("B", day="2026-09-13"), txn("C", customer="")],
              warnings=[{"source_file": "ebay.csv", "source_row": 3, "kind": "duplicate", "reason": "same id"}])
    s = load_day(conn, out, DAY)
    assert (s["transactions"], s["pulse_rows"], s["warnings"], s["revenue_cents"]) == (2, 4, 1, 1000)
    assert [r[0] for r in conn.execute("SELECT txn_id FROM transactions ORDER BY 1")] == ["ebay:A:sale", "ebay:C:sale"]
    assert conn.execute("SELECT customer_id, customer_basis FROM transactions WHERE order_id = 'C'").fetchone() == ("", "order")
    # a marketplace with no data is a row with NULL measures, never 0
    assert conn.execute("SELECT status, revenue_cents FROM pulse_daily WHERE marketplace = 'amazon'").fetchone() == ("missing", None)
    run = conn.execute("SELECT command, business_date, files_read, rows_written, warnings_total, result FROM runs").fetchone()
    assert run == ("load", DAY, '["ebay.csv"]', 2, 1, "ok")


def test_rerunning_a_date_changes_nothing(conn, tmp_path):
    out = tmp_path / "out"
    write_day(out, [txn("A"), txn("B")], warnings=[{"kind": "bad_date", "reason": "x"}])
    load_day(conn, out, DAY)
    first = snapshot(conn)
    load_day(conn, out, DAY)
    assert snapshot(conn) == first
    assert conn.execute("SELECT COUNT(*) FROM runs WHERE result = 'ok'").fetchone()[0] == 2


def test_rows_the_engine_no_longer_produces_disappear(conn, tmp_path):
    out = tmp_path / "out"
    write_day(out, [txn("A"), txn("B")])
    load_day(conn, out, DAY)
    write_day(out, [txn("A")], pulse_doc=pulse(ebay_revenue=500))  # e.g. a dedupe fix dropped B
    load_day(conn, out, DAY)
    assert [r[0] for r in conn.execute("SELECT order_id FROM transactions")] == ["A"]
    assert conn.execute("SELECT revenue_cents FROM pulse_daily WHERE marketplace = 'ebay'").fetchone()[0] == 500


def test_a_row_whose_date_moved_moves_with_it(conn, tmp_path):
    out = tmp_path / "out"
    write_day(out, [txn("A", day="2026-09-13")], day="2026-09-13")
    load_day(conn, out, "2026-09-13")
    write_day(out, [txn("A", day=DAY)])  # a timezone fix moved it to the next day
    load_day(conn, out, DAY)
    assert conn.execute("SELECT business_date FROM transactions").fetchall() == [(DAY,)]


def test_other_dates_are_untouched(conn, tmp_path):
    out = tmp_path / "out"
    write_day(out, [txn("A", day="2026-09-13")], day="2026-09-13")
    load_day(conn, out, "2026-09-13")
    write_day(out, [txn("B")])
    load_day(conn, out, DAY)
    assert conn.execute("SELECT COUNT(DISTINCT business_date) FROM pulse_daily").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2


@pytest.mark.parametrize("breakage, message", [
    (lambda out: (out / "pulse" / f"{DAY}.json").unlink(), "run `python -m recon.pulse"),
    (lambda out: (out / "pulse" / f"{DAY}.json").write_text(json.dumps(pulse(day="2026-09-13"))), "is for 2026-09-13"),
    (lambda out: (out / "transactions.csv").write_text("txn_id,source\nx,ebay\n"), "missing column"),
    (lambda out: (out / "transactions.csv").unlink(), "cannot read"),
])
def test_a_failed_load_changes_nothing_but_the_runs_log(conn, tmp_path, breakage, message):
    out = tmp_path / "out"
    write_day(out, [txn("A")])
    load_day(conn, out, DAY)
    before = snapshot(conn)
    write_day(out, [txn("A"), txn("B")])
    breakage(out)
    with pytest.raises(LoadError, match=message):
        load_day(conn, out, DAY)
    assert snapshot(conn) == before  # the previous load of the date stays
    assert conn.execute("SELECT result FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()[0] == "failed"


def test_a_malformed_pulse_is_a_load_error_not_a_crash(conn, tmp_path):
    out = tmp_path / "out"
    doc = pulse()
    del doc["marketplaces"]["ebay"]["status"]
    write_day(out, [txn("A")], pulse_doc=doc)
    with pytest.raises(LoadError, match="pulse.md"):
        load_day(conn, out, DAY)


def test_a_failure_halfway_through_the_writes_rolls_the_whole_date_back(conn, tmp_path, monkeypatch):
    import sqlite3
    from engine.store import load

    out = tmp_path / "out"
    write_day(out, [txn("A")])
    load_day(conn, out, DAY)
    before = snapshot(conn)
    write_day(out, [txn("B"), txn("C")], pulse_doc=pulse(ebay_revenue=2000))
    real_log_run = load.log_run

    def fail_on_ok(conn_, *args):
        if args[-1] == "ok":  # the run record is the last write of the transaction
            raise sqlite3.OperationalError("disk I/O error")
        real_log_run(conn_, *args)

    monkeypatch.setattr(load, "log_run", fail_on_ok)
    with pytest.raises(LoadError, match="disk I/O"):
        load_day(conn, out, DAY)
    assert snapshot(conn) == before  # deletes and inserts of the date were undone together
    assert conn.execute("SELECT result, message FROM runs ORDER BY rowid DESC LIMIT 1").fetchone() == \
        ("failed", "disk I/O error")


def test_cli_init_and_load(tmp_path, capsys):
    db, out = tmp_path / "ecom.db", tmp_path / "out"
    assert store_main(["--db", str(db), "init"]) == 0
    write_day(out, [txn("A")])
    assert store_main(["--db", str(db), "load", "--in-dir", str(out)]) == 0  # date from source_status.json
    assert f"loaded {DAY}: 1 transactions, 4 pulse rows" in capsys.readouterr().out
    (out / "pulse" / f"{DAY}.json").unlink()
    assert store_main(["--db", str(db), "load", "--in-dir", str(out), "--date", DAY]) == 1
    assert "nothing changed" in capsys.readouterr().err


def test_real_pipeline_one_september_day_matches_the_answer_key(conn, tmp_path):
    """engine run -> recon.pulse -> store load on clean_month, compared with expected.json."""
    from engine.cli import run as engine_run
    from recon.pulse.cli import main as pulse_main

    sample = ROOT / "data" / "sample" / "clean_month"
    key = json.loads((sample / "expected.json").read_text(encoding="utf-8"))["days"][DAY]
    out = tmp_path / "out"
    engine_run(sample / "inbox", out, DAY)
    assert pulse_main(["--date", DAY, "--in-dir", str(out)]) == 0
    load_day(conn, out, DAY)
    for mk in ("shopgoodwill", "ebay", "amazon"):
        status, revenue, orders = conn.execute(
            "SELECT status, revenue_cents, orders FROM pulse_daily WHERE business_date = ? AND marketplace = ?",
            (DAY, mk)).fetchone()
        assert (status, revenue, orders) == (key[mk]["status"], key[mk]["revenue_cents"], key[mk]["orders"]), mk
    # the stored transactions add up to the stored pulse
    assert conn.execute("SELECT SUM(gross_cents) FROM transactions WHERE business_date = ?", (DAY,)).fetchone()[0] \
        == key["enterprise"]["revenue_cents"]
    assert conn.execute("SELECT revenue_cents FROM v_daily WHERE business_date = ?", (DAY,)).fetchone()[0] \
        == key["enterprise"]["revenue_cents"]
