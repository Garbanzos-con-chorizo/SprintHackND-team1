"""V3.5 onward: the month-end sources we have never seen, as simulated APIs (docs/ASSUMPTIONS.md 2c).

`engine fetch --simulate --close-month` writes each file with an answer key computed from the generated
records. These tests read the engine's output of those files and apply the close's rule in plain Python:
the result must equal the key. They never call a simulator's own arithmetic to check a parser.
"""
import csv
import json
from pathlib import Path

import pytest

from engine.cli import fetch, fetch_close, main, run
from engine.contract import CLOSE_TABLES
from engine.coverage import SIMULATED_MANIFEST

MONTH = "2026-09"


def read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def close_month(tmp_path_factory):
    """One simulated month end, fetched and run through the engine: (inbox, engine out, answer key, log)."""
    base = tmp_path_factory.mktemp("close_month")
    assert fetch_close(base / "inbox", base / "key", MONTH, simulate=True) == 0
    run(base / "inbox", base / "out", "2026-09-30")
    key = json.loads((base / "key" / "expected_close_sources.json").read_text(encoding="utf-8"))
    log = json.loads((base / "key" / "fetch_log.json").read_text(encoding="utf-8"))
    return base / "inbox", base / "out", key, log


def test_every_simulated_file_is_marked_and_read_without_a_warning(close_month):
    inbox, out, key, log = close_month
    assert key["month"] == MONTH and key["simulated"] is True and "synthetic" in key["note"]
    assert log["close_month"] == MONTH and log["sources"]
    assert all(e["status"] == "ok" and e["simulated"] is True for e in log["sources"].values())
    written = sorted(n for e in log["sources"].values() for n in e["files"])
    assert written == sorted(p.name for p in inbox.iterdir() if p.name != SIMULATED_MANIFEST)
    assert json.loads((out / "warnings.json").read_text(encoding="utf-8")) == [] or all(
        w["kind"] == "missing_supplier" for w in json.loads((out / "warnings.json").read_text(encoding="utf-8")))
    coverage = json.loads((out / "source_coverage.json").read_text(encoding="utf-8"))["sources"]
    files = [f for s in coverage.values() for f in s["files"]]
    assert sorted(f["name"] for f in files) == written and all(f["simulated"] is True for f in files)


def test_the_same_month_always_gives_the_same_files(close_month, tmp_path):
    inbox, _, key, _ = close_month
    assert fetch_close(tmp_path / "inbox", tmp_path / "key", MONTH, simulate=True) == 0
    for path in inbox.iterdir():
        assert path.read_bytes() == (tmp_path / "inbox" / path.name).read_bytes(), path.name
    assert json.loads((tmp_path / "key" / "expected_close_sources.json").read_text(encoding="utf-8")) == key


def test_without_simulate_every_month_end_source_says_not_configured(tmp_path, capsys):
    assert main(["fetch", "--close-month", MONTH, "--inbox", str(tmp_path / "inbox"), "--out", str(tmp_path / "o")]) == 0
    log = json.loads((tmp_path / "o" / "fetch_log.json").read_text(encoding="utf-8"))
    assert log["sources"] and all(e["status"] == "not_configured" and not e["files"] for e in log["sources"].values())
    assert not (tmp_path / "o" / "expected_close_sources.json").exists()
    assert not list((tmp_path / "inbox").iterdir())


def test_the_nightly_fetch_never_delivers_a_month_end_source(tmp_path):
    assert fetch(tmp_path / "inbox", tmp_path / "out", "2026-10-02", simulate=True) == 0
    log = json.loads((tmp_path / "out" / "fetch_log.json").read_text(encoding="utf-8"))
    assert sorted(log["sources"]) == ["amazon", "cashmonkey", "ebay", "upright"]


def test_an_ordinary_run_writes_every_close_table_with_its_header_only(tmp_path):
    (tmp_path / "inbox").mkdir()
    run(tmp_path / "inbox", tmp_path / "out", "2026-10-02")
    for name, columns in CLOSE_TABLES.items():
        assert (tmp_path / "out" / f"{name}.csv").read_text(encoding="utf-8") == ",".join(columns) + "\n"


# ---------------------------------------------------------------- V3.5: FedEx from the ledger

def test_fedex_net_from_the_ledger_equals_the_key(close_month):
    inbox, out, key, _ = close_month
    assert (inbox / f"bc_gl_entries_{MONTH}.csv").exists()
    ledger = read(out / "ledger.csv")
    fedex = key["fedex"]
    assert (fedex["gl_account"], fedex["department"], fedex["vendor_no"]) == ("40356", "180", "V00122")  # slide 38
    mine = [r for r in ledger if (r["gl_account"], r["department"], r["vendor_no"]) == ("40356", "180", "V00122")]
    refunds = [r for r in mine if r["document_no"].startswith(fedex["refund_document_prefix"])]
    charges = [r for r in mine if r not in refunds]
    assert sum(int(r["amount_cents"]) for r in charges) == fedex["charges_cents"] > 0
    assert -sum(int(r["amount_cents"]) for r in refunds) == fedex["refunds_cents"] > 0
    assert sum(int(r["amount_cents"]) for r in mine) == fedex["net_cents"]
    assert len(mine) == fedex["entries"]
    # The parser keeps every row of the export: the ones the filter leaves out are there too.
    left_out = [r for r in ledger if r not in mine]
    assert len(left_out) == fedex["entries_left_out"] > 0
    assert {"40356"} < {r["gl_account"] for r in ledger} and {"180"} < {r["department"] for r in ledger}
    assert {"V00122"} < {r["vendor_no"] for r in ledger}
    assert all(r["posting_date"].startswith(MONTH) and r["source_file"] and r["entry_no"] for r in ledger)


def test_a_ledger_export_downloaded_twice_counts_once(close_month, tmp_path):
    inbox, out, _, _ = close_month
    (tmp_path / "inbox").mkdir()
    text = (inbox / f"bc_gl_entries_{MONTH}.csv").read_text(encoding="utf-8")
    (tmp_path / "inbox" / f"bc_gl_entries_{MONTH}.csv").write_text(text, encoding="utf-8")
    (tmp_path / "inbox" / f"bc_gl_entries_{MONTH} (1).csv").write_text(text, encoding="utf-8")
    run(tmp_path / "inbox", tmp_path / "out", "2026-09-30")
    assert len(read(tmp_path / "out" / "ledger.csv")) == len(read(out / "ledger.csv"))
    warnings = json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8"))
    assert warnings and all(w["kind"] == "duplicate" and "same ledger entry" in w["reason"] for w in warnings)


def test_a_bad_ledger_row_is_a_warning_not_a_crash(tmp_path):
    (tmp_path / "inbox").mkdir()
    (tmp_path / "inbox" / "bc_gl_entries_2026-09.csv").write_text(
        "Entry No.,Posting Date,Document Type,Document No.,G/L Account No.,Department Code,Vendor No.,Description,Amount\n"
        "1,09/01/2026,Invoice,PI-1,40356,180,V00122,FedEx,10.00\n"
        "2,09/31/2026,Invoice,PI-2,40356,180,V00122,FedEx,10.00\n"
        "3,09/02/2026,Invoice,PI-3,40356,180,V00122,FedEx,ten\n", encoding="utf-8")
    run(tmp_path / "inbox", tmp_path / "out", "2026-09-30")
    assert [r["entry_no"] for r in read(tmp_path / "out" / "ledger.csv")] == ["1"]
    warnings = json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8"))
    assert [(w["source_row"], w["kind"]) for w in warnings] == [(2, "bad_date"), (3, "bad_amount")]
