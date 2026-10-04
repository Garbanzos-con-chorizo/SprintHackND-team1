"""V3.4: `engine.store log-close` records a month-end close in the runs log (store.md v0.6)."""
import json

from engine.store import connect
from engine.store.cli import main
from engine.store.close_log import log_close
from engine.store.status import format_status, store_status

STATUS = {  # the shape of docs/contracts/close-outputs.md
    "month": "2026-09", "run_id": "2026-10-01T00-15-07", "run_at": "2026-10-01T00:15:07-04:00",
    "inboxes": ["data/sample/messy_month/inbox", "out/close_sources/2026-09/inbox"],
    "sources": {"ebay": {"status": "OPEN", "open_cents": 146556, "unexplained_cents": 0},
                "amazon": {"status": "INCOMPLETE", "open_cents": 466706, "unexplained_cents": 0}},
    "journal": {"lines": 56, "documents": 25, "balanced": True}, "invoices": {"documents": 1, "lines": 3},
    "exceptions": {"total": 18, "by_kind": {"payout_data_gap": 2}}, "needs_review": True,
    "posting": {"status": "not_posted", "reason": "no Business Central connection: import files only",
                "checks": [], "problems": []},
}


def write_status(close_dir, status=STATUS):
    folder = close_dir / status["month"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"close_status_{status['month']}.json").write_text(json.dumps(status), encoding="utf-8")


def runs(conn):
    return conn.execute("SELECT run_id, command, business_date, started_at, files_read, rows_written, warnings_total, "
                        "result, message FROM runs").fetchall()


def test_a_close_that_wrote_its_files_is_logged_from_its_status_file(tmp_path):
    conn = connect(tmp_path / "ecom.db")
    write_status(tmp_path / "close")
    row = log_close(conn, "2026-09", 0, tmp_path / "close")
    assert row["result"] == "ok"
    [(run_id, command, day, started, files, rows, warnings, result, message)] = runs(conn)
    assert (run_id, command, day, result) == ("close-2026-09-2026-10-01T00-15-07", "close", "2026-09-30", "ok")
    assert started == STATUS["run_at"] and json.loads(files) == STATUS["inboxes"]
    assert (rows, warnings) == (59, 18)  # journal and invoice lines; exceptions
    assert message == "ebay=OPEN; amazon=INCOMPLETE; 18 exceptions; needs review; not posted"
    # Logging the same run again changes nothing.
    assert log_close(conn, "2026-09", 0, tmp_path / "close").get("already_logged") is True
    assert len(runs(conn)) == 1


def test_a_refused_close_is_logged_as_failed_and_never_reads_an_older_status_file(tmp_path):
    conn = connect(tmp_path / "ecom.db")
    write_status(tmp_path / "close")  # left by an earlier run
    row = log_close(conn, "2026-09", 1, tmp_path / "close")
    assert row["result"] == "failed" and "refused" in row["message"]
    [(run_id, command, day, _, files, rows, warnings, result, _)] = runs(conn)
    assert (command, day, result, json.loads(files), rows, warnings) == ("close", "2026-09-30", "failed", [], 0, 0)
    assert "2026-10-01T00-15-07" not in run_id


def test_files_that_failed_the_read_back_check_are_logged_as_failed(tmp_path):
    conn = connect(tmp_path / "ecom.db")
    write_status(tmp_path / "close")
    row = log_close(conn, "2026-09", 2, tmp_path / "close")
    assert row["result"] == "failed" and row["message"].endswith("files failed the read-back check")


def test_status_shows_the_last_close_even_after_later_runs(tmp_path, capsys):
    db = tmp_path / "ecom.db"
    write_status(tmp_path / "close")
    assert main(["--db", str(db), "log-close", "--month", "2026-09", "--exit-code", "0",
                 "--close-dir", str(tmp_path / "close")]) == 0
    assert "close 2026-09 logged as ok" in capsys.readouterr().out
    conn = connect(db)
    with conn:  # a later night's run
        conn.execute("INSERT INTO runs (run_id, command, business_date, started_at, finished_at, files_read, "
                     "rows_written, warnings_total, result, message) VALUES ('later', 'load', '2026-10-02', "
                     "'2026-10-03T00:15:00-04:00', '2026-10-03T00:15:02-04:00', '[]', 1, 0, 'ok', '')")
    text = format_status(store_status(conn, "2026-10-01", "2026-10-03"))
    assert "last run: load 2026-10-02 ok" in text
    assert "last close: 2026-09 ok at" in text and "amazon=INCOMPLETE" in text and "not posted" in text
