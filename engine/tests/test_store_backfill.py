"""V2.3 / V2.4: store status and store backfill (engine/store/)."""
import json
from pathlib import Path

import pytest

from engine.cli import run as engine_run
from engine.store import backfill as backfill_mod
from engine.store import connect
from engine.store.backfill import PulseError, backfill
from engine.store.cli import main as store_main
from engine.store.status import compress, month_bounds, store_status

ROOT = Path(__file__).resolve().parents[2]
CLEAN_MONTH = ROOT / "data" / "sample" / "clean_month"


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "ecom.db")
    yield c
    c.close()


def add_day(conn, day, statuses, revenue=1000):
    conn.executemany("INSERT INTO pulse_daily (business_date, marketplace, status, revenue_cents, run_id) "
                     "VALUES (?, ?, ?, ?, 'r')",
                     [(day, mk, st, revenue if st == "ok" else None) for mk, st in statuses.items()])


ALL_OK = {"shopgoodwill": "ok", "amazon": "ok", "ebay": "ok", "other": "not_configured"}


# --- V2.3: status ----------------------------------------------------------------------------

def test_status_counts_complete_partial_and_not_loaded_days(conn):
    add_day(conn, "2026-09-01", ALL_OK)
    add_day(conn, "2026-09-02", {**ALL_OK, "ebay": "missing"})
    add_day(conn, "2026-09-03", {**ALL_OK, "amazon": "stale"})
    s = store_status(conn, "2026-09-01", "2026-09-05")
    assert (s["days_expected"], s["days_loaded"]) == (5, 3)
    assert s["complete"] == ["2026-09-01"]
    assert s["partial"] == {"2026-09-02": ["ebay missing"], "2026-09-03": ["amazon stale"]}
    assert s["not_loaded"] == ["2026-09-04", "2026-09-05"]
    assert s["marketplaces"]["ebay"] == {"ok": 2, "missing": 1, "stale": 0, "unknown": 0, "not_loaded": 2,
                                         "revenue_cents": 2000}
    assert "other" not in s["marketplaces"]  # not configured on every day: not shown


def test_status_no_data_is_none_not_zero_and_other_shows_when_it_has_data(conn):
    add_day(conn, "2026-09-01", {**ALL_OK, "amazon": "missing", "other": "ok"})
    s = store_status(conn, "2026-09-01", "2026-09-01")
    assert s["marketplaces"]["amazon"]["revenue_cents"] is None
    assert s["marketplaces"]["other"]["ok"] == 1


def test_month_bounds_and_compress():
    assert month_bounds("2026-02") == ("2026-02-01", "2026-02-28")
    assert month_bounds("2026-12") == ("2026-12-01", "2026-12-31")
    assert compress(["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-07"]) == "2026-09-01..2026-09-03, 2026-09-07"


def test_status_cli_on_an_empty_store_and_on_the_latest_month(tmp_path, capsys):
    db = str(tmp_path / "s.db")
    assert store_main(["--db", db, "status"]) == 0
    assert "is empty" in capsys.readouterr().out
    c = connect(db)
    with c:
        add_day(c, "2026-09-14", ALL_OK)
    c.close()
    assert store_main(["--db", db, "status"]) == 0
    out = capsys.readouterr().out
    assert "2026-09-01 to 2026-09-30: 1 of 30 days loaded, 1 complete, 0 partial, 29 not loaded" in out
    assert "not loaded: 2026-09-01..2026-09-13, 2026-09-15..2026-09-30" in out


# --- V2.4: backfill --------------------------------------------------------------------------

def test_backfill_three_september_days_match_the_answer_key(conn, tmp_path):
    key = json.loads((CLEAN_MONTH / "expected.json").read_text(encoding="utf-8"))["days"]
    results = backfill(conn, CLEAN_MONTH / "inbox", tmp_path / "out", "2026-09-01", "2026-09-03")
    assert [r["result"] for r in results] == ["ok", "ok", "ok"]
    for r in results:
        assert r["revenue_cents"] == key[r["date"]]["enterprise"]["revenue_cents"], r["date"]
    assert sorted(p.name for p in (tmp_path / "out" / "pulse").glob("2026-*.json")) == \
        ["2026-09-01.json", "2026-09-02.json", "2026-09-03.json"]
    assert store_status(conn, "2026-09-01", "2026-09-03")["complete"] == ["2026-09-01", "2026-09-02", "2026-09-03"]


def test_a_backfilled_day_is_what_engine_run_writes(conn, tmp_path):
    backfill(conn, CLEAN_MONTH / "inbox", tmp_path / "bf", "2026-09-02", "2026-09-02")
    engine_run(CLEAN_MONTH / "inbox", tmp_path / "run", "2026-09-02")
    for name in ("transactions.csv", "warnings.json"):
        assert (tmp_path / "bf" / name).read_text(encoding="utf-8") == (tmp_path / "run" / name).read_text(encoding="utf-8")
    status = [json.loads((tmp_path / d / "source_status.json").read_text(encoding="utf-8")) for d in ("bf", "run")]
    for s in status:
        s.pop("generated_at")
    assert status[0] == status[1]


def test_a_failed_day_is_reported_and_the_others_still_load(conn, tmp_path, monkeypatch):
    real = backfill_mod.run_pulse

    def pulse_fails_on_the_2nd(out, day):
        if day == "2026-09-02":
            raise PulseError("recon.pulse failed (exit 1): boom")
        real(out, day)

    monkeypatch.setattr(backfill_mod, "run_pulse", pulse_fails_on_the_2nd)
    results = backfill(conn, CLEAN_MONTH / "inbox", tmp_path / "out", "2026-09-01", "2026-09-03")
    assert [(r["date"], r["result"]) for r in results] == \
        [("2026-09-01", "ok"), ("2026-09-02", "failed"), ("2026-09-03", "ok")]
    assert "boom" in results[1]["message"]
    assert store_status(conn, "2026-09-01", "2026-09-03")["not_loaded"] == ["2026-09-02"]


def test_backfill_cli_exit_code_and_summary(tmp_path, capsys):
    db, out = str(tmp_path / "b.db"), str(tmp_path / "out")
    code = store_main(["--db", db, "backfill", "--inbox", str(CLEAN_MONTH / "inbox"),
                       "--from", "2026-09-29", "--to", "2026-10-01", "--out", out])
    text = capsys.readouterr().out
    # October 1 is outside the sample: the engine finds no rows, the pulse says stale, nothing is invented
    assert code == 0, text
    assert "3 of 3 days loaded" in text
    assert "2 complete, 1 partial" in text
