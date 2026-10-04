"""V3.2: the engine writes payouts.csv and bank.csv for the month-end close (close-inputs.md)."""
import csv
import json
from pathlib import Path

from engine.cli import run
from engine.contract import BANK_COLUMNS, PAYOUT_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
MESSY = ROOT / "data" / "sample" / "messy_month"

EBAY_HEADER = ('"Transaction creation date","Type","Order number","Buyer username","Item subtotal",'
               '"Net amount","Payout currency"\n')
BANK_HEADER = "Posting Date,Description,Debit,Credit,Balance\n"


def read(path: Path, columns: list[str]) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == columns
        return list(reader)


def run_inbox(tmp_path, files):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, text in files.items():
        (inbox / name).write_text(text, encoding="utf-8")
    run(inbox, tmp_path / "out", "2026-10-02")
    out = tmp_path / "out"
    return (read(out / "payouts.csv", PAYOUT_COLUMNS), read(out / "bank.csv", BANK_COLUMNS),
            json.loads((out / "warnings.json").read_text(encoding="utf-8")))


def test_messy_month_payouts_and_bank(tmp_path):
    run(MESSY / "inbox", tmp_path, "2026-09-30")
    payouts = read(tmp_path / "payouts.csv", PAYOUT_COLUMNS)
    bank = read(tmp_path / "bank.csv", BANK_COLUMNS)
    warnings = json.loads((tmp_path / "warnings.json").read_text(encoding="utf-8"))

    assert len(payouts) == 31
    assert sum(p["marketplace"] == "ebay" for p in payouts) == 29
    assert sum(p["marketplace"] == "amazon" for p in payouts) == 2
    assert len({p["payout_id"] for p in payouts}) == 31
    # Every payout the files report equals the answer key (eBay's Oct 1 payout is after the last download).
    key = json.loads((MESSY / "expected.json").read_text(encoding="utf-8"))["close"]["payouts"]
    expected = {(k["source"], k["paid_date"]): k["amount_cents"] for k in key if k["source"] != "shopgoodwill"}
    mine = {(p["marketplace"], p["paid_date"]): int(p["amount_cents"]) for p in payouts}
    assert set(expected) - set(mine) == {("ebay", "2026-10-01")}
    assert all(expected[k] == v for k, v in mine.items())

    assert len(bank) == 26
    assert sum(int(b["amount_cents"]) > 0 for b in bank) == 24
    assert sum(int(b["amount_cents"]) < 0 for b in bank) == 2
    assert {b["account"] for b in bank} == {"OPERATING"}
    assert not [w for w in warnings if w["source_file"] == "bank_activity_2026-09.csv"]
    # Payouts repeated in the overlapping eBay download are logged, never silently dropped.
    assert any(w["kind"] == "duplicate" and "same payout" in w["reason"] for w in warnings)


def test_payout_rows_are_payouts_not_sales(tmp_path):
    payouts, _, warnings = run_inbox(tmp_path, {"ebay_2026-10-02.csv": EBAY_HEADER + (
        '"Oct 1, 2026","Order","25-1","ann","10.00","8.50","USD"\n'
        '"Oct 2, 2026","Payout","--","--","--","-441.65","USD"\n'
        '"Oct 2, 2026","Payout","--","--","--","-10.00","USD"\n')})
    assert warnings == []
    assert [(p["payout_id"], p["paid_date"], p["amount_cents"]) for p in payouts] == [
        ("ebay:2026-10-02", "2026-10-02", "44165"),
        ("ebay:2026-10-02#2", "2026-10-02", "1000"),  # two payouts one day stay two
    ]
    assert payouts[0]["period_from"] == payouts[0]["period_to"] == ""
    transactions = (tmp_path / "out" / "transactions.csv").read_text(encoding="utf-8")
    assert "Payout" not in transactions and transactions.count("\n") == 2  # header + the one sale


def test_amazon_transfer_keeps_the_date_it_was_written_on(tmp_path):
    payouts, _, _ = run_inbox(tmp_path, {"amazon_2026-10-02.csv": (
        '"date/time","settlement id","type","order id","product sales","total"\n'
        '"Oct 1, 2026 11:30:00 PM PDT","1","Transfer","","0","-1,052.64"\n')})
    # 11:30 PM Pacific is Oct 2 in Eastern; the payout is dated as the report dates it.
    assert [(p["payout_id"], p["amount_cents"]) for p in payouts] == [("amazon:2026-10-01", "105264")]


def test_bank_lines_are_signed_and_overlapping_exports_count_once(tmp_path):
    first = BANK_HEADER + ('10/01/2026,EBAY COMMERCE INC DES:PAYOUT,,469.47,"1,469.47"\n'
                           '10/01/2026,ADP PAYROLL,"1,000.00",,469.47\n')
    second = BANK_HEADER + ('10/01/2026,ADP PAYROLL,"1,000.00",,469.47\n'
                            '10/02/2026,SHOPGOODWILL.COM DES:SELLER PAYOUT,,25.00,494.47\n')
    _, bank, warnings = run_inbox(tmp_path, {"bank_activity_a.csv": first, "bank_activity_b.csv": second})
    assert [(b["posting_date"], b["amount_cents"], b["balance_cents"]) for b in bank] == [
        ("2026-10-01", "46947", "146947"), ("2026-10-01", "-100000", "46947"), ("2026-10-02", "2500", "49447")]
    assert bank[0]["bank_txn_id"] == "bank_activity_a.csv:1" and bank[0]["account"] == "OPERATING"
    assert [(w["source_file"], w["kind"]) for w in warnings] == [("bank_activity_b.csv", "duplicate")]


def test_bank_lines_without_a_balance_are_never_merged(tmp_path):
    text = "Posting Date,Description,Debit,Credit\n10/01/2026,FEE,5.00,\n10/01/2026,FEE,5.00,\n"
    _, bank, warnings = run_inbox(tmp_path, {"bank_activity.csv": text})
    assert [b["amount_cents"] for b in bank] == ["-500", "-500"] and bank[0]["balance_cents"] == ""
    assert warnings == []
