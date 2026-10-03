import csv
import json

from engine.cli import main
from engine.contract import COLUMNS, EXPECTED_SOURCES


def test_run_on_empty_inbox_writes_valid_files(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    out = tmp_path / "out"

    assert main(["run", "--inbox", str(inbox), "--out", str(out), "--date", "2026-10-02"]) == 0

    with open(out / "transactions.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        assert next(reader) == COLUMNS
        assert list(reader) == []

    status = json.loads((out / "source_status.json").read_text(encoding="utf-8"))
    assert status["business_date"] == "2026-10-02"
    assert set(status["sources"]) == set(EXPECTED_SOURCES)
    assert all(s["status"] == "missing" and s["rows"] == 0 for s in status["sources"].values())

    assert json.loads((out / "warnings.json").read_text(encoding="utf-8")) == []


def test_output_uses_lf_line_endings(tmp_path):
    out = tmp_path / "out"
    main(["run", "--inbox", str(tmp_path), "--out", str(out), "--date", "2026-10-02"])
    assert b"\r" not in (out / "transactions.csv").read_bytes()
