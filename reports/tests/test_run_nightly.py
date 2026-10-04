"""V2.11: the nightly run loads the store, pulls the internal snapshot and computes the KPIs."""
import json
import sqlite3
from pathlib import Path

import pytest

from reports import run_nightly

ROOT = Path(__file__).resolve().parents[2]
SCENARIO, DAY = "gw_day_clean", "2026-10-01"


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A temporary store, and temporary output and page folders: the tests never touch the real
    out/ and reports/ that the demo shows (Dani's report, 2026-10-03 21:55)."""
    path = tmp_path / "ecom.db"
    monkeypatch.setenv("ECOM_DB", str(path))
    monkeypatch.setattr(run_nightly, "OUT", tmp_path / "out")
    monkeypatch.setattr(run_nightly, "REPORTS", tmp_path / "reports")
    return path


def snapshot(folder):
    return {p: p.stat().st_mtime_ns for p in folder.rglob("*") if p.is_file()} if folder.exists() else {}


def test_a_real_night_fills_the_store_and_writes_the_three_kpi_files(db, capsys):
    assert run_nightly.main(["--scenario", SCENARIO]) == 0
    out = capsys.readouterr().out
    assert "[7/7] Render" in out and "FAILED" not in out
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM pulse_daily WHERE business_date = ?", (DAY,)).fetchone()[0] == 4
    assert c.execute("SELECT COUNT(DISTINCT metric) FROM internal_daily WHERE business_date = ?", (DAY,)).fetchone()[0] == 10
    assert c.execute("SELECT command, COUNT(*) FROM runs GROUP BY 1 ORDER BY 1").fetchall() == \
        [("kpi", 3), ("load", 1), ("pull", 1)]
    for name in (f"day-{DAY}", "week-2026-W40", "month-2026-10"):
        k = json.loads((db.parent / "out" / "kpi" / f"{name}.json").read_text(encoding="utf-8"))
        assert len(k["kpis"]) == 15, name


def test_simulated_night_skips_the_store(db, capsys):
    assert run_nightly.main(["--scenario", SCENARIO, "--simulated"]) == 0
    assert "SKIPPED (simulated pulse" in capsys.readouterr().out
    assert not db.exists()


def test_a_store_failure_is_logged_and_the_pulse_page_still_renders(db, capsys, monkeypatch):
    monkeypatch.setattr(run_nightly, "STORE_CMD", ["-c", "import sys; print('store: disk full'); sys.exit(3)"])
    page = db.parent / "reports" / "pulse" / f"{DAY}.html"
    assert run_nightly.main(["--scenario", SCENARIO]) == 1
    out = capsys.readouterr().out
    assert "store: disk full" in out and "FAILED: store load, internal pull, KPIs" in out
    assert page.exists()  # the morning page doesn't depend on the store


def test_the_tests_leave_the_real_output_folders_alone(db):
    real = {name: snapshot(ROOT / name) for name in ("out/kpi", "out/pulse", "reports/pulse", "out/" + SCENARIO)}
    real_index = (ROOT / "reports" / "index.html").stat().st_mtime_ns if (ROOT / "reports" / "index.html").exists() else None
    assert run_nightly.main(["--scenario", SCENARIO]) == 0
    assert {name: snapshot(ROOT / name) for name in real} == real
    assert ((ROOT / "reports" / "index.html").stat().st_mtime_ns if real_index else None) == real_index
    assert (db.parent / "reports" / "index.html").exists() and (db.parent / "out" / "pulse" / f"{DAY}.json").exists()
