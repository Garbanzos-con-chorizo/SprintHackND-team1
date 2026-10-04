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
                no_data = sum(k["status"] == "no_data" or (k["kind"] == "ranking" and not k["rows"])
                              for k in kf["kpis"] if not k.get("parts"))  # sell-through draws its two boxes instead
                self.assertEqual(html.count('value none">No data'), no_data)
                for area in kf["areas"]:
                    self.assertIn(f'<h2>{area["name"].replace("+", "+")}</h2>', html.replace("&amp;", "&"))

    def test_every_pillar_name_is_on_the_page(self):
        kf, html = self.render("kpi.sample.month.json")
        for pillar in kf["pillars"]:
            self.assertIn(f'<div class="pillar">{pillar["name"]}</div>', html)
        self.assertEqual(html.count('class="pillar"'), 15)

    def test_sell_through_is_two_boxes_and_a_null_box_says_no_data(self):
        kf, html = self.render("kpi.sample.month.json")
        parts = next(k for k in kf["kpis"] if k["id"] == "sales.sell_through")["parts"]
        self.assertEqual(html.count('class="part"'), 2)
        for p in parts:
            self.assertIn(f'<div class="pname">{p["name"]}</div>', html)
        self.assertIn(f'{parts[0]["value"] * 100:.1f}%', html)
        for k in kf["kpis"]:
            if k["id"] == "sales.sell_through":
                k["parts"][1].update(value=None, available=None)
        self.assertIn('pval none">No data', scorecard.render(kf))

    def test_every_tile_has_an_info_button_that_opens_its_definition_and_note(self):
        for name in ("kpi.sample.month.json", "kpi.sample.month.partial.json"):
            with self.subTest(name):
                kf, html = self.render(name)
                refs = re.findall(r'<button class="info" type="button" popovertarget="([^"]+)"', html)
                self.assertEqual(len(refs), 15)
                self.assertEqual(len(set(refs)), 15)
                for ref in refs:
                    self.assertEqual(html.count(f'id="{ref}" popover'), 1)
                for k in kf["kpis"]:
                    about = re.search(rf'<div class="about-name">{re.escape(scorecard.escape(k["name"]))}</div>(.*?)</div>',
                                      html, re.S)[1]
                    self.assertIn(scorecard.escape(k["definition"]), about)
                    if k.get("note"):
                        self.assertIn(scorecard.escape(k["note"]), about)
                    if k["status"] == "partial":       # the red edge is never the only sign
                        self.assertIn("Partial data", html.split(about)[1].split('<div class="tile ')[0])
                self.assertEqual(html.count('class="flag"'), sum(k["status"] == "partial" for k in kf["kpis"]))

    def test_download_links_appear_only_for_files_that_exist(self):
        kf, _ = self.render("kpi.sample.month.json")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            self.assertNotIn("Download:", scorecard.render(kf, dest))
            (dest / "month-2026-09.csv").write_text("x", encoding="utf-8")
            (dest / "month-2026-09.pdf").write_bytes(b"%PDF")
            html = scorecard.render(kf, dest)
            self.assertIn('<a href="month-2026-09.csv">', html)
            self.assertIn('<a href="month-2026-09.pdf">', html)

    def test_portal_card_switches_between_day_week_and_month_pages(self):
        from reports import hub
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for kind, name in (("day", "kpi.sample.day.json"), ("week", "kpi.sample.week.json"),
                               ("month", "kpi.sample.month.json")):
                scorecard.build(EXAMPLES / name, root / "scorecard")
            html = hub.build(root).read_text(encoding="utf-8")
            self.assertIn("Period:", html)
            for kind in ("day", "week", "month"):
                self.assertRegex(html, rf'href="scorecard/{kind}-[^"]+\.html"')

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
