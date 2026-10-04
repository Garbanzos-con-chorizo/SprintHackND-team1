"""V3.4: on the 1st the scheduler delivers the simulated month-end sources, runs the one-command close and
the store remembers the run. Everything is written under a temporary folder, never the real out/ or reports/."""
import csv
import json
import sqlite3
from pathlib import Path

import pytest

from reports import hub, run_scheduled

ROOT = Path(__file__).resolve().parents[2]
MESSY = ROOT / "data" / "sample" / "messy_month"

pytestmark = pytest.mark.skipif(not MESSY.exists(), reason="sample data not present")


@pytest.fixture(scope="module")
def closed(tmp_path_factory):
    base = tmp_path_factory.mktemp("scheduled_close")
    patch = pytest.MonkeyPatch()
    patch.setenv("ECOM_DB", str(base / "ecom.db"))
    patch.setattr(run_scheduled, "OUT", base / "out")
    patch.setattr(run_scheduled, "REPORTS", base / "reports")
    try:
        ok = run_scheduled.run_close("2026-09", MESSY / "inbox")
    finally:
        patch.undo()
    return base, ok


def test_the_close_runs_on_the_sample_inbox_plus_the_simulated_sources(closed):
    base, ok = closed
    assert ok is True
    status = json.loads((base / "out" / "close" / "2026-09" / "close_status_2026-09.json").read_text(encoding="utf-8"))
    assert len(status["inboxes"]) == 3 and status["inboxes"][0] == "data/sample/messy_month/inbox"
    assert status["inboxes"][1] == "data/sample/messy_month/periodic"
    assert status["journal"]["balanced"] is True and status["posting"]["status"] == "not_posted"
    assert {k: v["status"] for k, v in status["sources"].items()} == {
        "ebay": "OPEN", "amazon": "INCOMPLETE", "shopgoodwill": "INCOMPLETE"}
    # Every simulated file is labelled, in the fetch log and in what the engine read for the close.
    log = json.loads((base / "out" / "close_sources" / "2026-09" / "fetch_log.json").read_text(encoding="utf-8"))
    assert sorted(log["sources"]) == ["bank_0101", "bc_ledger", "goodwillbooks", "jewelry"]
    assert all(e["simulated"] is True for e in log["sources"].values())
    coverage = json.loads((base / "out" / "close" / "2026-09" / "engine" / "source_coverage.json").read_text(encoding="utf-8"))
    simulated = {f["name"] for s in coverage["sources"].values() for f in s["files"] if f["simulated"]}
    assert simulated == {n for e in log["sources"].values() for n in e["files"]}
    engine = base / "out" / "close" / "2026-09" / "engine"
    for name in ("ledger.csv", "statements.csv", "jewelry.csv"):
        with open(engine / name, encoding="utf-8", newline="") as f:
            assert len(list(csv.DictReader(f))) > 0, name


def test_the_page_and_its_status_file_are_where_the_portal_links_them(closed):
    base, _ = closed
    reports = base / "reports"
    page = (reports / "close" / "2026-09.html").read_text(encoding="utf-8")
    assert "Synthetic sample data" in page and "simulated API" in page
    assert (reports / "close" / "2026-09" / "close_status_2026-09.json").exists()
    assert (reports / "close" / "2026-09" / "runs.csv").exists()
    index = hub.build(reports).read_text(encoding="utf-8")
    assert 'href="close/2026-09/close_status_2026-09.json">Run status</a>' in index
    assert 'href="close/2026-09/runs.csv">Run history</a>' in index


def test_the_store_remembers_the_close(closed):
    base, _ = closed
    conn = sqlite3.connect(base / "ecom.db")
    [(command, day, result, message)] = conn.execute(
        "SELECT command, business_date, result, message FROM runs WHERE command = 'close'").fetchall()
    conn.close()
    assert (command, day, result) == ("close", "2026-09-30", "ok")
    assert "amazon=INCOMPLETE" in message and "needs review" in message and message.endswith("not posted")


def test_a_refused_close_is_reported_and_logged_and_builds_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ECOM_DB", str(tmp_path / "ecom.db"))
    monkeypatch.setattr(run_scheduled, "OUT", tmp_path / "out")
    monkeypatch.setattr(run_scheduled, "REPORTS", tmp_path / "reports")
    (tmp_path / "empty").mkdir()
    assert run_scheduled.run_close("2026-09", tmp_path / "empty" / "nothing_here") is False
    assert "close: not built (exit 1" in capsys.readouterr().out
    assert not (tmp_path / "reports" / "close" / "2026-09.html").exists()
    conn = sqlite3.connect(tmp_path / "ecom.db")
    assert conn.execute("SELECT result FROM runs WHERE command = 'close'").fetchall() == [("failed",)]
    conn.close()
