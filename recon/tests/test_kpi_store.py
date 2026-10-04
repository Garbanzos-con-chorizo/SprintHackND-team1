import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from recon.kpi import store
from recon.kpi.store import InternalRow, PulseRow, Sale
from recon.tests.kpi_samples import make_db

OCT1 = date(2026, 10, 1)
PULSE = [
    ("2026-09-30", "ebay", "ok", 100, 0, 13, 1),
    ("2026-10-01", "ebay", "ok", 5000, -1000, 650, 3),
    ("2026-10-01", "amazon", "missing", None, None, None, None),
    ("2026-10-02", "ebay", "ok", 200, 0, 26, 1),
]
SALES = [
    ("2026-09-30", "ebay", "e0", "x0"),
    ("2026-10-01", "ebay", "e1", "x1"),
    ("2026-10-01", "amazon", "a1", ""),
]
INTERNAL = [
    ("2026-09-29", "active_listings_by_age", "0-30", 90),
    ("2026-09-30", "active_listings_by_age", "0-30", 100),
    ("2026-09-30", "active_listings_by_age", "91+", 5),
    ("2026-09-30", "labor_hours", "total", 40.0),
    ("2026-10-01", "labor_hours", "total", 41.5),
    ("2026-10-01", "listings_created", "ebay", 12, "api"),
]


class Store(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "ecom.db"

    def open(self, **rows):
        make_db(self.db, **rows)
        con = store.connect(self.db)
        self.addCleanup(con.close)
        return con

    def test_loads_only_the_days_asked_for(self):
        data = store.load(self.open(pulse=PULSE, sales=SALES, internal=INTERNAL), OCT1, OCT1)
        self.assertEqual(data.pulse, [
            PulseRow("2026-10-01", "amazon", "missing", None, None, None, None, None),
            PulseRow("2026-10-01", "ebay", "ok", 5000, -1000, 4000, 650, 3)])
        self.assertEqual(data.sales, [Sale("amazon", "a1", "", None), Sale("ebay", "e1", "x1", None)])
        self.assertEqual(data.internal, [
            InternalRow("2026-10-01", "labor_hours", "total", 41.5, "mock"),
            InternalRow("2026-10-01", "listings_created", "ebay", 12.0, "api")])

    def test_the_stock_of_the_night_before_comes_with_the_window(self):
        data = store.load(self.open(pulse=PULSE, internal=INTERNAL), OCT1, date(2026, 10, 2))
        self.assertEqual(data.opening, [
            InternalRow("2026-09-30", "active_listings_by_age", "0-30", 100.0, "mock"),
            InternalRow("2026-09-30", "active_listings_by_age", "91+", 5.0, "mock")])
        self.assertEqual(store.load(self.open_again(), date(2026, 9, 29), OCT1).opening, [])

    def test_latest_business_date(self):
        self.assertEqual(store.latest_business_date(self.open(pulse=PULSE)), date(2026, 10, 2))
        self.assertEqual(len(store.load(self.open_again(), date(2026, 9, 1), date(2026, 10, 31)).pulse), 4)

    def open_again(self):
        con = store.connect(self.db)
        self.addCleanup(con.close)
        return con

    def test_an_empty_database_has_no_latest_date(self):
        con = self.open()
        self.assertIsNone(store.latest_business_date(con))
        self.assertEqual(store.load(con, OCT1, OCT1), store.WindowData([], [], []))

    def test_refunds_are_not_sales(self):
        make_db(self.db, sales=SALES)
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO transactions (txn_id, source, marketplace, type, business_date, order_id,"
                    " customer_id, customer_basis, gross_cents, fee_cents, source_file, source_row, run_id)"
                    " VALUES ('ebay:e1:refund', 'ebay', 'ebay', 'refund', '2026-10-01', 'e1', 'x1', 'buyer', -500, 0,"
                    " 'test.csv', 9, 'test')")
        con.commit()
        con.close()
        self.assertEqual(len(store.load(self.open_again(), OCT1, OCT1).sales), 2)

    def test_unit_counts_are_read_when_they_are_there(self):
        con = self.open(sales=[(*SALES[1], 3), (*SALES[2], 1)])
        self.assertEqual([s.units for s in store.load(con, OCT1, OCT1).sales], [1, 3])

    def test_a_transactions_table_without_units_still_reads(self):
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE pulse_daily (business_date TEXT, marketplace TEXT, status TEXT, gross_cents INTEGER,"
                    " refunds_cents INTEGER, revenue_cents INTEGER, fees_cents INTEGER, orders INTEGER)")
        con.execute("CREATE TABLE transactions (business_date TEXT, marketplace TEXT, type TEXT, order_id TEXT,"
                    " customer_id TEXT)")
        con.execute("INSERT INTO transactions VALUES ('2026-10-01', 'ebay', 'sale', 'e1', 'x1')")
        con.commit()
        con.close()
        self.assertEqual(store.load(self.open_again(), OCT1, OCT1).sales, [Sale("ebay", "e1", "x1", None)])

    def test_only_pulse_daily_is_required(self):
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE pulse_daily (business_date TEXT, marketplace TEXT, status TEXT, gross_cents INTEGER,"
                    " refunds_cents INTEGER, revenue_cents INTEGER, fees_cents INTEGER, orders INTEGER)")
        con.execute("INSERT INTO pulse_daily VALUES ('2026-10-01', 'ebay', 'ok', 5000, -1000, 4000, 650, 3)")
        con.commit()
        con.close()
        data = store.load(self.open_again(), OCT1, OCT1)
        self.assertEqual((len(data.pulse), data.sales, data.internal), (1, [], []))

    def test_an_absent_database_is_an_error(self):
        with self.assertRaisesRegex(store.StoreError, "no database at"):
            store.connect(self.db)

    def test_a_database_without_pulse_daily_is_an_error(self):
        sqlite3.connect(self.db).close()
        with self.assertRaisesRegex(store.StoreError, "no pulse_daily table"):
            store.connect(self.db)

    def test_a_file_that_is_not_a_database_is_an_error(self):
        self.db.write_bytes(b"not a database at all, just some text that is long enough to be read\n" * 4)
        with self.assertRaisesRegex(store.StoreError, "cannot read"):
            store.connect(self.db)

    def test_the_database_is_opened_read_only(self):
        con = self.open(pulse=PULSE)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("DELETE FROM pulse_daily")

    def test_saving_kpis_needs_the_kpi_values_table(self):
        sqlite3.connect(self.db).close()
        doc = {"period": {"type": "day", "id": "2026-10-01", "start": "2026-10-01", "through": "2026-10-01",
                          "label": "October 1, 2026"}, "generated_at": "2026-10-02T00:20:00-04:00", "kpis": []}
        with self.assertRaisesRegex(store.StoreError, "kpi_values not written"):
            store.save_kpis(self.db, doc)

    def test_default_path(self):
        with mock.patch.dict(os.environ, {"ECOM_DB": str(self.db)}):
            self.assertEqual(store.default_path(), self.db)
        with mock.patch.dict(os.environ, clear=True):
            self.assertEqual(store.default_path(), Path("out") / "store" / "ecom.db")


if __name__ == "__main__":
    unittest.main()
