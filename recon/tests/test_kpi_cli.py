import contextlib
import io as stdio
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from recon.kpi import cli
from recon.tests import kpi_samples
from recon.tests.kpi_samples import EXAMPLES, answer_days, build_sample_db, make_db


def run(*argv):
    out, err = stdio.StringIO(), stdio.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


class KpiCommand(unittest.TestCase):
    """On the database behind the contract examples: September, and October 1 to 4 with eBay missing on the 3rd."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "ecom.db"
        build_sample_db(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(dir=self.tmp.name))

    def kpi(self, *argv):
        code, _, err = run(*argv, "--db", self.db, "--out-dir", self.out)
        self.assertEqual((code, err), (0, ""))

    def read(self, name):
        return json.loads((self.out / name).read_text(encoding="utf-8"))

    def by_id(self, name):
        return {k["id"]: k for k in self.read(name)["kpis"]}

    def assert_is_the_example(self, written, example):
        """If this fails after a deliberate change: python -m recon.tests.kpi_samples, and say so in kpi.md."""
        expected = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
        self.assertTrue(written.pop("generated_at"))
        expected.pop("generated_at")
        self.assertEqual(written, expected)

    def test_reproduces_every_contract_example(self):
        for example, kind, text, _ in kpi_samples.SAMPLES:
            with self.subTest(example=example):
                self.kpi("--period", kind, {"day": "--date", "week": "--week", "month": "--month"}[kind], text)
                self.assert_is_the_example(self.read(f"{kind}-{text}.json"), example)

    def test_period_alone_is_the_one_with_the_latest_stored_day(self):
        for kind, name, example in (("month", "month-2026-10.json", "kpi.sample.month.partial.json"),
                                    ("week", "week-2026-W40.json", "kpi.sample.week.json"),
                                    ("day", "day-2026-10-04.json", "kpi.sample.day.json")):
            with self.subTest(kind=kind):
                self.kpi("--period", kind)
                self.assert_is_the_example(self.read(name), example)

    def test_the_examples_show_the_states_the_page_must_handle(self):
        def states(example):
            doc = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
            return {(k["status"], k["reason"]) for k in doc["kpis"]}

        self.assertEqual(states("kpi.sample.month.json"),
                         {("ok", None), ("no_data", "no_prior_period"), ("partial", "no_buyer_ids")})
        self.assertLessEqual({("partial", "missing_days"), ("partial", "missing_internal_days"),
                              ("no_data", "no_internal_data")}, states("kpi.sample.month.partial.json"))
        self.assertLessEqual({("partial", "missing_days"), ("partial", "missing_internal_days")},
                             states("kpi.sample.week.json"))
        self.assertLessEqual({("no_data", "period_too_short"), ("no_data", "zero_denominator"),
                              ("no_data", "no_internal_data")}, states("kpi.sample.day.json"))

    def query(self, sql, *args):
        con = sqlite3.connect(self.db)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()

    def test_the_kpis_are_recorded_in_the_store(self):
        logged = "SELECT rows_written, result FROM runs WHERE command = 'kpi' AND run_id LIKE 'kpi-month-2026-09-%'"
        before = len(self.query(logged))
        self.kpi("--month", "2026-09")
        self.kpi("--month", "2026-09")  # a second run replaces the period's rows
        rows = self.query("SELECT kpi_id, dimension, value, unit, status, source, period_end FROM kpi_values"
                          " WHERE period_type = 'month' AND period_start = '2026-09-01'")
        kpis = self.by_id("month-2026-09.json")
        self.assertEqual(len(rows), 13 + 10 + 10)  # 13 single values and two top 10 lists
        by_key = {(kpi_id, dimension): rest for kpi_id, dimension, *rest in rows}
        self.assertEqual(by_key[("fin.revenue", "")], [7075396, "cents", "ok", "files", "2026-09-30"])
        self.assertEqual(by_key[("fin.revenue_growth", "")], [None, "ratio", "no_data", "files", "2026-09-30"])
        top = kpis["cat.top_revenue"]["rows"][0]
        self.assertEqual(by_key[("cat.top_revenue", top["label"])][:3], [top["value"], "cents", "ok"])
        runs = self.query(logged)
        self.assertEqual((len(runs) - before, set(runs)), (2, {(33, "ok")}))

    def test_a_period_to_date_is_recorded_through_its_last_day(self):
        self.kpi("--month", "2026-10")
        ends = self.query("SELECT DISTINCT period_end FROM kpi_values WHERE period_type = 'month'"
                          " AND period_start = '2026-10-01'")
        self.assertEqual(ends, [("2026-10-04",)])

    def test_a_ranking_without_data_is_one_empty_row(self):
        self.kpi("--month", "2026-08")
        rows = self.query("SELECT dimension, value, status FROM kpi_values WHERE period_start = '2026-08-01'"
                          " AND kpi_id = 'cat.top_margin'")
        self.assertEqual(rows, [("", None, "no_data")])

    def test_september_revenue_is_the_answer_key_to_the_cent(self):
        answers = answer_days()
        expected = sum(row["enterprise"]["revenue_cents"] for day, row in answers.items() if day.startswith("2026-09"))
        self.kpi("--month", "2026-09")
        revenue = self.by_id("month-2026-09.json")["fin.revenue"]
        self.assertEqual((revenue["value"], revenue["status"]), (expected, "ok"))
        self.assertEqual(expected, 7075396)

    def test_latest_stays_on_the_greatest_period(self):
        self.kpi("--month", "2026-10")
        self.kpi("--month", "2026-09")
        self.assertEqual(self.read("latest-month.json")["period"]["id"], "2026-10")
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ["latest-month.json", "month-2026-09.json", "month-2026-10.json"])

    def test_through_reports_part_of_a_period(self):
        self.kpi("--month", "2026-09", "--through", "2026-09-04")
        doc = self.read("month-2026-09.json")
        self.assertEqual((doc["period"]["days"], doc["period"]["complete"], doc["period"]["label"]),
                         (4, False, "September 2026 (to date)"))
        self.assertEqual(doc["kpis"][0]["value"], 895886)  # what October 1 to 4 is compared with in the example

    def test_a_week(self):
        code, out, _ = run("--week", "2026-W40", "--db", self.db, "--out-dir", self.out)
        self.assertEqual(code, 0)
        self.assertIn("Week 40, 2026: ", out)
        doc = self.read("week-2026-W40.json")
        self.assertEqual((doc["period"]["start"], doc["period"]["through"], doc["period"]["complete"]),
                         ("2026-09-28", "2026-10-04", True))
        self.assertEqual(doc["prior_period"]["label"], "Week 39, 2026")
        self.assertEqual(doc["coverage"]["gaps"], [{"date": "2026-10-03", "marketplace": "ebay", "status": "missing"}])
        self.assertEqual(self.read("latest-week.json"), doc)

    def test_a_day_with_a_missing_marketplace(self):
        self.kpi("--period", "day", "--date", "2026-10-03")
        kpis = self.by_id("day-2026-10-03.json")
        answer = answer_days()["2026-10-03"]["enterprise"]["revenue_cents"]
        self.assertEqual((kpis["fin.revenue"]["value"], kpis["fin.revenue"]["status"]), (answer, "partial"))
        self.assertEqual(kpis["fin.revenue"]["note"], "eBay has no data on 2026-10-03, so this is partial.")
        self.assertEqual(kpis["cust.repeat_buyer_rate"]["reason"], "period_too_short")

    def test_a_period_before_anything_was_stored_is_all_no_data(self):
        self.kpi("--month", "2026-07")  # August has one row: the stock count of the 31st
        doc = self.read("month-2026-07.json")
        self.assertEqual((doc["period"]["complete"], doc["coverage"]["days_missing"]), (True, 31))
        self.assertEqual({k["status"] for k in doc["kpis"]}, {"no_data"})
        self.assertIsNone(doc["internal_data"])

    def test_options_that_do_not_go_together(self):
        for argv in (["--period", "week", "--month", "2026-09"], [], ["--month", "2026-13"], ["--week", "2026-38"],
                     ["--month", "2026-09", "--through", "2026-10-01"]):
            with self.subTest(argv=argv):
                code, out, err = run(*argv, "--db", self.db, "--out-dir", self.out)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("kpi: "))
        self.assertEqual(list(self.out.iterdir()), [])

    def test_a_missing_database_writes_nothing(self):
        code, out, err = run("--month", "2026-09", "--db", self.out / "nothing.db", "--out-dir", self.out / "kpi")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("no database at", err)
        self.assertFalse((self.out / "kpi").exists())

    def test_the_database_path_comes_from_the_environment(self):
        with mock.patch.dict(os.environ, {"ECOM_DB": str(self.db)}):
            code, _, _ = run("--month", "2026-09", "--out-dir", self.out)
        self.assertEqual(code, 0)
        self.assertTrue((self.out / "month-2026-09.json").exists())


class EmptyDatabase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        make_db(self.dir / "ecom.db")

    def test_there_is_no_latest_period(self):
        code, _, err = run("--period", "month", "--db", self.dir / "ecom.db", "--out-dir", self.dir / "kpi")
        self.assertEqual(code, 2)
        self.assertIn("no pulse rows yet", err)

    def test_a_named_period_is_written_as_no_data(self):
        code, _, _ = run("--month", "2026-10", "--db", self.dir / "ecom.db", "--out-dir", self.dir / "kpi")
        self.assertEqual(code, 0)
        doc = json.loads((self.dir / "kpi" / "month-2026-10.json").read_text(encoding="utf-8"))
        self.assertEqual((doc["period"]["through"], doc["period"]["days"]), ("2026-10-01", 1))
        self.assertEqual({k["status"] for k in doc["kpis"]}, {"no_data"})


class OlderDatabase(unittest.TestCase):
    def test_a_store_without_kpi_values_still_gets_its_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ecom.db"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE pulse_daily (business_date TEXT, marketplace TEXT, status TEXT, gross_cents"
                        " INTEGER, refunds_cents INTEGER, revenue_cents INTEGER, fees_cents INTEGER, orders INTEGER)")
            con.execute("INSERT INTO pulse_daily VALUES ('2026-10-01', 'ebay', 'ok', 5000, -1000, 4000, 650, 3)")
            con.commit()
            con.close()
            code, out, err = run("--date", "2026-10-01", "--db", db, "--out-dir", Path(tmp) / "kpi")
            self.assertEqual(code, 0)
            self.assertIn("kpi_values not written", err)
            doc = json.loads((Path(tmp) / "kpi" / "day-2026-10-01.json").read_text(encoding="utf-8"))
            self.assertEqual((doc["kpis"][0]["value"], doc["kpis"][0]["status"]), (4000, "partial"))


class Examples(unittest.TestCase):
    def test_every_example_is_listed_for_regeneration(self):
        self.assertEqual({name for name, *_ in kpi_samples.SAMPLES},
                         {p.name for p in EXAMPLES.glob("kpi.sample.*.json")})


if __name__ == "__main__":
    unittest.main()
