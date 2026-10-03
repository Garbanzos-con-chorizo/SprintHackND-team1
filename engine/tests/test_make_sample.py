"""The sample generator and its --check: the pipeline must match an answer key it did not produce."""
import csv
import json
from datetime import date

import pytest

from engine.cli import run
from engine.sources.cashmonkey import CashMonkey
from engine.tools.make_sample import build, check, main


@pytest.mark.parametrize("scenario", ["clean_day", "messy_day"])
def test_pipeline_matches_answer_key(tmp_path, scenario):
    key = build(scenario, date(2026, 10, 2), 42, tmp_path)
    ok, lines = check(tmp_path, key)
    assert ok, "\n".join(lines)


@pytest.mark.parametrize("seed", [1, 7, 99])
def test_other_seeds_also_match(tmp_path, seed):
    key = build("messy_day", date(2026, 10, 2), seed, tmp_path)
    assert check(tmp_path, key)[0]


def test_generation_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    build("messy_day", date(2026, 10, 2), 5, a)
    build("messy_day", date(2026, 10, 2), 5, b)
    for f in (a / "inbox").iterdir():
        assert f.read_bytes() == (b / "inbox" / f.name).read_bytes()


def test_check_fails_when_the_answer_key_is_wrong(tmp_path):
    key = build("clean_day", date(2026, 10, 2), 42, tmp_path)
    key["days"]["2026-10-02"]["ebay"]["sales_cents"] += 1
    ok, lines = check(tmp_path, key)
    assert not ok and any(line.startswith("FAIL") for line in lines)


def test_check_catches_a_broken_utc_conversion(tmp_path, monkeypatch):
    key = build("clean_day", date(2026, 10, 2), 42, tmp_path)
    monkeypatch.setattr(CashMonkey, "date_assume_tz", None)  # treat UTC stamps as Eastern: wrong day for evening sales
    assert not check(tmp_path, key)[0]


def test_messy_scenario_contains_the_faults_it_claims(tmp_path):
    build("messy_day", date(2026, 10, 2), 42, tmp_path)
    names = sorted(p.name for p in (tmp_path / "inbox").iterdir())
    assert any("(1)" in n for n in names)                                 # re-downloaded duplicate
    assert not any("10-02-2026" in n for n in names if n.startswith("paid_orders"))  # missing Upright file for D
    cm = (tmp_path / "inbox" / "orders2023-20261002-132256-96170.csv").read_bytes().decode("utf-8")
    assert "n/a" in cm and "not a date" in cm and "\r\n\r\n" in cm      # bad amount, bad date, blank line
    run(tmp_path / "inbox", tmp_path / "out", "2026-10-02")
    warnings = json.loads((tmp_path / "out" / "warnings.json").read_text(encoding="utf-8"))
    assert {"bad_amount", "bad_date", "duplicate"} <= {w["kind"] for w in warnings}


def test_cli_exit_code_and_default_output(tmp_path, capsys):
    assert main(["--scenario", "clean_day", "--out", str(tmp_path), "--check"]) == 0
    assert "PIPELINE MATCHES THE ANSWER KEY" in capsys.readouterr().out


# --- the two real-format parsers, in isolation ---

def test_upright_date_comes_from_file_name_and_other_channels_are_skipped(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    header = "Upright Order ID,Channel,Channel Order ID,Channel Buyer,Subtotal,Currency\n"
    (inbox / "paid_orders_09-30-2026_09-30-2026.csv").write_text(
        header + "1,Shopgoodwill,65748407,okeye904,32.47,USD\n2,Goodwillfinds,999,someone,15.00,USD\n", encoding="utf-8")
    run(inbox, tmp_path / "out", "2026-09-30")
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    r = rows[0]
    assert (r["marketplace"], r["business_date"], r["gross_cents"], r["customer_id"]) == ("shopgoodwill", "2026-09-30", "3247", "okeye904")


def test_cashmonkey_one_line_per_unit_is_one_order_and_utc_crosses_midnight(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "orders2023-20261003-010101-1.csv").write_text(
        "Order ID,Line ID,Order Date (UTC),Channel,Item Price,Marketplace Fees,Currency\n"
        "E-1,a,2026-10-03 01:30:00,eBay,10.00,1.60,USD\n"      # 9:30 PM Eastern on Oct 2
        "E-1,b,2026-10-03 01:30:00,eBay,10.00,1.60,USD\n"      # second, identical unit of the same order
        "G-1,c,2026-10-03 15:00:00,Goodwillbooks,5.00,0.75,USD\n", encoding="utf-8")
    run(inbox, tmp_path / "out", "2026-10-02")
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = {r["order_id"]: r for r in csv.DictReader(f)}
    assert (rows["E-1"]["gross_cents"], rows["E-1"]["fee_cents"], rows["E-1"]["business_date"], rows["E-1"]["marketplace"]) == ("2000", "320", "2026-10-02", "ebay")
    assert (rows["G-1"]["business_date"], rows["G-1"]["marketplace"]) == ("2026-10-03", "other")
