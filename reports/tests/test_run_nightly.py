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
    path = tmp_path / "ecom.db"
    monkeypatch.setenv("ECOM_DB", str(path))
    return path


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
        k = json.loads((ROOT / "out" / "kpi" / f"{name}.json").read_text(encoding="utf-8"))
        assert len(k["kpis"]) == 15, name


def test_simulated_night_skips_the_store(db, capsys):
    assert run_nightly.main(["--scenario", SCENARIO, "--simulated"]) == 0
    assert "SKIPPED (simulated pulse" in capsys.readouterr().out
    assert not db.exists()


def test_a_store_failure_is_logged_and_the_pulse_page_still_renders(db, capsys, monkeypatch):
    monkeypatch.setattr(run_nightly, "STORE_CMD", ["-c", "import sys; print('store: disk full'); sys.exit(3)"])
    page = ROOT / "reports" / "pulse" / f"{DAY}.html"
    page.unlink(missing_ok=True)
    assert run_nightly.main(["--scenario", SCENARIO]) == 1
    out = capsys.readouterr().out
    assert "store: disk full" in out and "FAILED: store load, internal pull, KPIs" in out
    assert page.exists()  # the morning page doesn't depend on the store
