"""Phase 2 wiring: the weekly page from the week's KPI file, the portal's store card, the pulse labels."""
import csv
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from reports import email_gen, hub, pulse, store_view, weekly

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs" / "contracts" / "examples"


class WeeklyFromKpiFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.page = weekly.build(EXAMPLES / "kpi.sample.week.json", self.root / "weekly", self.root / "scorecard")

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_page_is_the_scorecard_and_a_copy_goes_where_the_email_reads_it(self):
        self.assertEqual(self.page, self.root / "scorecard" / "week-2026-W40.html")
        html = self.page.read_text(encoding="utf-8")
        self.assertIn("COO scorecard: Week 40, 2026", html)
        self.assertEqual(html.count('<div class="tile '), 15)
        self.assertEqual((self.root / "weekly" / "2026-W40.html").read_text(encoding="utf-8"), html)

    def test_csv_keeps_the_email_layout_and_takes_every_number_from_the_file(self):
        kf = json.loads((EXAMPLES / "kpi.sample.week.json").read_text(encoding="utf-8"))
        with open(self.root / "weekly" / "2026-W40.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0]), weekly.CSV_COLUMNS)
        by_kpi = {r["KPI"]: r for r in rows if not r["Category"]}
        revenue = next(k for k in kf["kpis"] if k["id"] == "fin.revenue")
        self.assertEqual(by_kpi[revenue["name"]]["Value"], f'{revenue["value"] / 100:.2f}')
        self.assertEqual(by_kpi[revenue["name"]]["Source"], "Marketplace files")
        for k in kf["kpis"]:
            if k["simulated"] and k["kind"] != "ranking":
                self.assertEqual(by_kpi[k["name"]]["Source"], kf["internal_data"]["label"])
        top = next(k for k in kf["kpis"] if k["id"] == "cat.top_revenue")
        self.assertEqual(sum(r["KPI"] == top["name"] for r in rows), len(top["rows"]))

    def test_weekly_email_still_builds_from_these_files(self):
        report = email_gen.payload("Weekly", "2026-W40", root=self.root)
        self.assertIsNotNone(report)
        self.assertIn("Total E-Commerce Revenue", report["html"])
        self.assertNotIn("Simulated", report["html"].split("KPIs calculated")[0])  # only file-based KPIs in the table
        msg = email_gen.message({"name": "COO", "email": "coo@example.org", "type": "Weekly"}, report,
                                datetime(2026, 10, 5, 6, 0).astimezone())
        self.assertEqual([p.get_filename() for p in msg.iter_attachments()], ["2026-W40.html", "2026-W40.csv"])

    def test_a_missing_week_file_without_a_store_stops_with_the_commands_to_run(self):
        with mock.patch.dict(os.environ, {"ECOM_DB": str(self.root / "no-store.db")}), self.assertRaises(SystemExit) as e:
            weekly.kpi_file("2026-W01", self.root / "no-kpi-here")
        self.assertIn("python -m recon.kpi --week 2026-W01", str(e.exception))


def make_store(path):
    """A store built from Victor's schema file only, as store.md's "Rules for readers" shows."""
    con = sqlite3.connect(path)
    con.executescript((ROOT / "engine" / "store" / "schema.sql").read_text(encoding="utf-8"))
    pulse_rows = []
    for day, ebay in (("2026-10-01", "ok"), ("2026-10-02", "ok"), ("2026-10-03", "missing")):
        for mk, status in (("shopgoodwill", "ok"), ("amazon", "ok"), ("ebay", ebay), ("other", "not_configured")):
            ok = status == "ok"
            pulse_rows.append((day, mk, status, *([10000, 0, 10000, 1000, 5, 5, "order"] if ok else [None] * 7), "load-1"))
    con.executemany("INSERT INTO pulse_daily VALUES (?,?,?,?,?,?,?,?,?,?,?)", pulse_rows)
    con.executemany("INSERT INTO internal_daily VALUES (?,?,?,?,?,?,?)",
                    [(d, "labor_hours", "total", 80, "hours", "mock", "pull-1") for d in ("2026-10-01", "2026-10-02")])
    con.executemany("INSERT INTO runs (run_id, command, business_date, started_at, result, rows_written, message) "
                    "VALUES (?,?,?,?,?,?,?)",
                    [("load-1", "load", "2026-10-03", "2026-10-04T00:15:00-04:00", "ok", 12, ""),
                     ("pull-1", "pull", "2026-10-03", "2026-10-04T00:16:00-04:00", "failed", 0, "API down")])
    con.commit()
    con.close()


class StoreCardTest(unittest.TestCase):
    def test_summary_reads_the_named_tables_and_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ecom.db"
            make_store(db)
            s = store_view.summary(db)
            self.assertEqual((s["days"], s["first"], s["last"]), (3, "2026-10-01", "2026-10-03"))
            self.assertEqual(s["partial"], ["2026-10-03"])
            self.assertEqual((s["internal_days"], s["internal_sources"], s["failed_runs"]), (2, ["mock"], 1))
            self.assertEqual([t["revenue_cents"] for t in s["trend"]], [30000, 30000, 20000])
            self.assertEqual(s["runs"][0]["command"], "pull")  # newest first

    def test_portal_shows_the_store_and_says_when_there_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, db = Path(tmp) / "reports", Path(tmp) / "ecom.db"
            root.mkdir()
            make_store(db)
            html = hub.build(root, db).read_text(encoding="utf-8")
            self.assertIn("Nightly store", html)
            self.assertIn("2 of 3", html)  # complete days
            self.assertIn('<span class="pill warn">Simulated</span>', html)
            self.assertIn("Partial day: Oct 3, 2026", html)
            self.assertEqual(html.count('<path class="bar'), 3)
            self.assertIn('class="bar partial"', html)
            html = hub.build(root, Path(tmp) / "none.db").read_text(encoding="utf-8")
            self.assertIn("Not built yet", html)
            self.assertIsNone(store_view.summary(Path(tmp) / "none.db"))


class PulseLabelsTest(unittest.TestCase):
    def test_slide_31_labels_and_an_other_row_that_is_always_there(self):
        p = json.loads((EXAMPLES / "pulse.sample.json").read_text(encoding="utf-8"))
        p["marketplaces"]["other"] = {"status": "not_configured"}
        for html in (pulse.render_day(p), pulse.render_email(p)):
            self.assertIn("Other e-commerce channels", html)
            self.assertIn("Total e-commerce", html)
            self.assertNotIn("Enterprise total", html)
        row = pulse.row_html("other", {"status": "not_configured"})
        self.assertEqual(row.count('<td class="dash"'), 3)
        self.assertIn("Not tracked", row)


if __name__ == "__main__":
    unittest.main()
