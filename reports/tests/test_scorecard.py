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
                no_data = sum((k["status"] == "no_data" and not k.get("parts")) or (k["kind"] == "ranking" and not k["rows"])
                              for k in kf["kpis"])
                self.assertEqual(html.count('value none">No data'), no_data)
                boxes = [p for k in kf["kpis"] for p in k.get("parts") or []]
                self.assertEqual(html.count('<div class="part">'), len(boxes))
                self.assertEqual(html.count('pv none">No data'), sum(p["value"] is None for p in boxes))
                for area in kf["areas"]:
                    self.assertIn(f'<h2>{area["name"].replace("+", "+")}</h2>', html.replace("&amp;", "&"))

    def test_sell_through_shows_its_two_boxes_and_the_overall_rate(self):
        kf, html = self.render("kpi.sample.week.json")
        tile = re.search(r'<div class="tile [^"]*">(?:(?!<div class="tile ).)*Sell-Through Rate.*?(?=<div class="tile |</section>)', html, re.S)[0]
        self.assertIn("Listed in the period</span><span class=\"pv\">68.5%", tile)
        self.assertIn("606 of 885 units", tile)
        self.assertIn("Left from earlier</span><span class=\"pv\">0.0%", tile)
        self.assertIn("0 of 2,310 units", tile)
        self.assertIn('<span class="muted">Overall</span> 68.5%', tile)
        self.assertIn("How the boxes are split", tile)  # the assumption, behind the info button
        _, day = self.render("kpi.sample.day.json")  # nothing listed that day: first box has no value
        self.assertIn("Overall: no data", day)
        self.assertIn('Listed in the period</span><span class="pv none">No data', day)

    def test_period_switch_links_the_day_week_and_month_pages_and_their_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for name in ("kpi.sample.month.json", "kpi.sample.month.partial.json", "kpi.sample.week.json"):
                scorecard.build(EXAMPLES / name, dest)
            month = (dest / "month-2026-10.html").read_text(encoding="utf-8")
            self.assertIn('<a href="week-2026-W40.html" title="Week 40, 2026">Week</a>', month)
            self.assertIn('<span class="off" title="No day scorecard built yet">Day</span>', month)
            self.assertIn('href="month-2026-09.html"', month)  # previous month
            self.assertNotIn('month-2026-10.pdf', month)
            (dest / "month-2026-10.pdf").write_bytes(b"%PDF-1.4")
            scorecard.build(EXAMPLES / "kpi.sample.day.json", dest)  # a new page relinks the others
            month = (dest / "month-2026-10.html").read_text(encoding="utf-8")
            self.assertIn('<a href="day-2026-10-04.html" title="Oct 4, 2026">Day</a>', month)
            self.assertIn('href="month-2026-10.pdf" download', month)
            index = (dest / "index.html").read_text(encoding="utf-8")
            for label in ("Day", "Week", "Month", "October 2026", "September 2026", "Week 40, 2026", "Oct 4, 2026"):
                self.assertIn(label, index)

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
