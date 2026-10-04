"""V2.7: shipping_cents, handling_cents and units in transactions.csv (transaction.md v2) and in the store."""
import csv
import json
import sqlite3
from pathlib import Path

from engine.cli import run
from engine.contract import COLUMNS
from engine.store import connect, load_day

ROOT = Path(__file__).resolve().parents[2]
MESSY = ROOT / "data" / "sample" / "messy_month"

EBAY_HEADER = ('"Transaction creation date","Type","Order number","Buyer username","Quantity","Item subtotal",'
               '"Shipping and handling","Final Value Fee - variable","Payout currency"\n')
CM_HEADER = "Order ID,Line ID,Order Date (UTC),Channel,Quantity,Item Price,Shipping,Marketplace Fees,Currency\n"


def engine_rows(tmp_path, files, date="2026-10-02"):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, text in files.items():
        (inbox / name).write_text(text, encoding="utf-8")
    run(inbox, tmp_path / "out", date)
    with open(tmp_path / "out" / "transactions.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COLUMNS
        return {r["txn_id"]: r for r in reader}


def test_messy_month_shipping_and_handling_equal_the_answer_key(tmp_path):
    """What reports/reconcile.py read from the answer key (STOPGAP) now comes from the files."""
    key = json.loads((MESSY / "expected.json").read_text(encoding="utf-8"))["close"]["marketplace_totals_from_files"]
    run(MESSY / "inbox", tmp_path, "2026-09-30")
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["business_date"].startswith("2026-09")]
    for mk, k in key.items():
        mine = [r for r in rows if r["marketplace"] == mk]
        assert sum(int(r["shipping_cents"]) for r in mine) == k["shipping_cents"], mk
        assert sum(int(r["handling_cents"]) for r in mine) == k["handling_cents"], mk
        sales = [r for r in mine if r["type"] == "sale"]
        assert all(r["units"] for r in sales) and sum(int(r["units"]) for r in sales) >= k["orders"], mk


def test_refunds_carry_negative_shipping_and_no_units(tmp_path):
    rows = engine_rows(tmp_path, {"ebay_2026-10-02.csv": EBAY_HEADER
                                  + '"Oct 2, 2026","Order","25-1","b1","2","20.00","5.99","-2.60","USD"\n'
                                  + '"Oct 2, 2026","Refund","25-1","b1","1","-20.00","-5.99","--","USD"\n'})
    sale, refund = rows["ebay:25-1:sale"], rows["ebay:25-1:refund"]
    assert (sale["shipping_cents"], sale["handling_cents"], sale["units"]) == ("599", "0", "2")
    assert (refund["gross_cents"], refund["shipping_cents"], refund["units"]) == ("-2000", "-599", "0")


def test_lines_of_one_order_sum_units_and_shipping(tmp_path):
    rows = engine_rows(tmp_path, {"orders2023-20261002-1-1.csv": CM_HEADER
                                  + "E-1,a,2026-10-02 15:00:00,eBay,1,10.00,3.00,1.00,USD\n"
                                  + "E-1,b,2026-10-02 15:00:00,eBay,2,8.00,1.50,0.80,USD\n"})
    r = rows["cashmonkey:E-1:sale"]
    assert (r["gross_cents"], r["shipping_cents"], r["units"]) == ("1800", "450", "3")


def test_no_quantity_column_means_units_unknown_not_zero(tmp_path):
    header = '"Transaction creation date","Type","Order number","Buyer username","Item subtotal","Payout currency"\n'
    rows = engine_rows(tmp_path, {"ebay_2026-10-02.csv": header + '"Oct 2, 2026","Order","25-9","b9","12.00","USD"\n'})
    r = rows["ebay:25-9:sale"]
    assert (r["units"], r["shipping_cents"], r["handling_cents"]) == ("", "0", "0")


# --- store ---------------------------------------------------------------------------------

V1_TRANSACTIONS = """CREATE TABLE transactions (txn_id TEXT NOT NULL PRIMARY KEY, source TEXT NOT NULL,
    marketplace TEXT NOT NULL, type TEXT NOT NULL, business_date TEXT NOT NULL, order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL DEFAULT '', customer_basis TEXT NOT NULL, gross_cents INTEGER NOT NULL,
    fee_cents INTEGER NOT NULL DEFAULT 0, units INTEGER, source_file TEXT NOT NULL, source_row INTEGER NOT NULL,
    run_id TEXT NOT NULL)"""


def test_a_version_1_store_gets_the_new_columns_and_keeps_its_rows(tmp_path):
    path = tmp_path / "v1.db"
    old = sqlite3.connect(path)
    old.execute(V1_TRANSACTIONS)
    old.execute("INSERT INTO transactions VALUES ('ebay:1:sale','ebay','ebay','sale','2026-09-01','1','','order',"
                "500,0,NULL,'f.csv',1,'r')")
    old.execute("PRAGMA user_version = 1")
    old.commit()
    old.close()
    c = connect(path)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 2
    assert c.execute("SELECT gross_cents, shipping_cents, handling_cents FROM transactions").fetchall() == [(500, 0, 0)]
    c.close()


def test_store_load_keeps_shipping_handling_and_units_and_still_reads_a_v1_csv(tmp_path):
    c = connect(tmp_path / "s.db")
    out = tmp_path / "out"
    run(MESSY / "inbox", out, "2026-09-14")
    from recon.pulse.cli import main as pulse_main
    assert pulse_main(["--date", "2026-09-14", "--in-dir", str(out)]) == 0
    load_day(c, out, "2026-09-14")
    ship, units = c.execute("SELECT SUM(shipping_cents), SUM(units) FROM transactions WHERE business_date = '2026-09-14' "
                            "AND type = 'sale'").fetchone()
    assert ship > 0 and units > 0
    # a transactions.csv written before v2 (no shipping, handling, units) still loads: 0, 0, unknown
    with open(out / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    v1 = COLUMNS[:COLUMNS.index("shipping_cents")]
    with open(out / "transactions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=v1, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    load_day(c, out, "2026-09-14")
    assert c.execute("SELECT SUM(shipping_cents), COUNT(units) FROM transactions WHERE business_date = '2026-09-14'"
                     ).fetchone() == (0, 0)
    c.close()
