"""V3.3: source_coverage.json, the days each source's files cover and the days no file covers (close-inputs.md)."""
import json
from pathlib import Path

from engine.cli import fetch, run
from engine.coverage import SIMULATED_MANIFEST, build_source_coverage, named_range, update_manifest

ROOT = Path(__file__).resolve().parents[2]
MESSY = ROOT / "data" / "sample" / "messy_month"


def coverage(out: Path) -> dict:
    return json.loads((out / "source_coverage.json").read_text(encoding="utf-8"))


def test_messy_month_names_the_days_no_report_covers(tmp_path):
    run(MESSY / "inbox", tmp_path, "2026-09-30")
    c = coverage(tmp_path)
    assert c["month"] == "2026-09" and c["through"] == "2026-09-30"
    sources = c["sources"]
    assert sources["amazon"]["days_missing"] == ["2026-09-21", "2026-09-22"]
    assert sources["shopgoodwill"]["days_missing"] == ["2026-09-07"]
    assert sources["ebay"]["days_missing"] == []
    assert sources["bank"]["days_missing"] == []  # bank_activity_2026-09: the whole month
    amazon = sources["amazon"]["files"]
    assert [(f["name"], f["from"], f["to"], f["basis"]) for f in amazon] == [
        ("amazon_daterange_2026-09-01_2026-09-20.csv", "2026-09-01", "2026-09-20", "file_name"),
        ("amazon_daterange_2026-09-23_2026-09-30.csv", "2026-09-23", "2026-09-30", "file_name")]
    assert all(f["rows"] > 0 and f["simulated"] is False for s in sources.values() for f in s["files"])


def test_a_simulated_fetch_is_flagged(tmp_path):
    assert fetch(tmp_path / "inbox", tmp_path / "log", "2026-10-02", simulate=True) == 0
    manifest = json.loads((tmp_path / "inbox" / SIMULATED_MANIFEST).read_text(encoding="utf-8"))
    assert "synthetic" in manifest["note"] and manifest["files"]
    run(tmp_path / "inbox", tmp_path / "out", "2026-10-02")
    sources = coverage(tmp_path / "out")["sources"]
    files = [f for s in sources.values() for f in s["files"]]
    assert files and all(f["simulated"] is True for f in files)
    # A Cash Monkey export of one channel covers that marketplace only.
    assert [f["name"] for f in sources["amazon"]["files"]] == ["amazon_orders_2026-10-02.xlsx"]
    assert sources["ebay"]["days_missing"] == ["2026-10-01"]
    # The manifest is not a report: it never becomes an unreadable-file warning.
    warnings = json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8"))
    assert not [w for w in warnings if w["source_file"] == SIMULATED_MANIFEST]


def test_a_real_fetch_clears_the_simulated_flag(tmp_path):
    update_manifest(tmp_path, {"a.csv": {"source": "ebay"}, "b.csv": {"source": "ebay"}})
    update_manifest(tmp_path, {}, real=["a.csv"])
    files = json.loads((tmp_path / SIMULATED_MANIFEST).read_text(encoding="utf-8"))["files"]
    assert list(files) == ["b.csv"]
    update_manifest(tmp_path, {}, real=["b.csv"])
    assert not (tmp_path / SIMULATED_MANIFEST).exists()


def test_named_range():
    assert named_range("ebay_transactions_2026-09-12_2026-09-18 (1).csv") == ("2026-09-12", "2026-09-18")
    assert named_range("paid_orders_09-07-2026_09-07-2026.xlsx") == ("2026-09-07", "2026-09-07")
    assert named_range("bank_activity_2026-02.csv") == ("2026-02-01", "2026-02-28")
    assert named_range("ebay_2026-10-02.csv") == ("2026-10-02", "2026-10-02")
    assert named_range("orders2023-20261003-001500-96170.xlsx") is None


def test_no_file_means_every_day_missing_and_rows_are_the_fallback():
    files = [{"file": "export.csv", "source": "ebay", "feeds": ["ebay"], "rows": {"ebay": 3},
              "dates": {"ebay": ["2026-09-02", "2026-09-03"]}}]
    sources = build_source_coverage("2026-09-04", files)["sources"]
    assert sources["amazon"] == {"files": [], "days_missing": ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]}
    assert sources["ebay"]["files"][0]["basis"] == "rows"
    assert sources["ebay"]["days_missing"] == ["2026-09-01", "2026-09-04"]
