"""Scorecard page (renders Dani's KPI files) and the month-end close page."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from reports import bc_export, close_report, scorecard

EXAMPLES = scorecard.ROOT / "docs" / "contracts" / "examples"


class ScorecardTest(unittest.TestCase):
    def render(self, name):
        kf = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
        return kf, scorecard.render(kf)

    def test_every_example_renders_all_15_kpis_with_the_file_s_states(self):
        for name in ("kpi.sample.month.json", "kpi.sample.month.partial.json", "kpi.sample.week.json",
                     "kpi.sample.day.json"):
            with self.subTest(name):
                kf, html = self.render(name)
                self.assertEqual(html.count('<div class="tile '), 15)
                self.assertEqual(html.count('class="sim"'), sum(k["simulated"] for k in kf["kpis"]))
                no_data = sum(k["status"] == "no_data" or (k["kind"] == "ranking" and not k["rows"]) for k in kf["kpis"])
                self.assertEqual(html.count('value none">No data'), no_data)
                for area in kf["areas"]:
                    self.assertIn(f'<h2>{area["name"].replace("+", "+")}</h2>', html.replace("&amp;", "&"))

    def test_rankings_render_their_rows_and_partial_coverage_raises_the_banner(self):
        kf, html = self.render("kpi.sample.month.partial.json")
        rank = next(k for k in kf["kpis"] if k["id"] == "cat.top_revenue")
        for row in rank["rows"]:
            self.assertIn(row["label"].replace("&", "&amp;"), html)
        self.assertIn('class="summary alert"', html)
        self.assertIn("Data missing:", html)

    def test_change_colour_follows_good_direction(self):
        kf, html = self.render("kpi.sample.month.partial.json")
        backlog = next(k for k in kf["kpis"] if k["id"] == "inv.unlisted_backlog")  # up, and lower is better
        self.assertEqual((backlog["good_direction"], backlog["delta"]["value"] > 0), ("down", True))
        tile = re.search(r'Unlisted Inventory Backlog.*?</div></div>', html, re.S)[0]
        self.assertIn('class="chg down"', tile)

    def test_no_internal_data_says_so(self):
        kf, _ = self.render("kpi.sample.month.json")
        kf = dict(kf, internal_data=None)
        self.assertIn("No internal data stored for this period", scorecard.render(kf))


class ClosePageTest(unittest.TestCase):
    def test_close_page_from_the_mock_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "close", Path(tmp) / "reports"
            self.assertEqual(bc_export.main(["--out", str(src)]), 0)
            page = close_report.build("2026-09", src, dest)
            html = page.read_text(encoding="utf-8")
            self.assertIn("12 journal documents, all balanced to 0.00", html)
            self.assertEqual(html.count(">RECONCILED<"), 3)
            self.assertNotIn('class="summary alert"', html)
            for k, _ in close_report.FILES:
                self.assertTrue((dest / "2026-09" / f"{k}_2026-09.csv").exists())


if __name__ == "__main__":
    unittest.main()
