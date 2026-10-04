"""Phase 2 wiring kept from the branch: the portal's store card, the pulse labels.

The weekly page is covered by test_weekly.py (main's weekly.py, which renders the week's KPI file).
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from reports import hub, pulse, store_view

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs" / "contracts" / "examples"


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
