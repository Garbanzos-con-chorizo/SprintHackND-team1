"""The site map's link check: every link and button resolves, every page has a way home."""
import tempfile
import unittest
from pathlib import Path

from reports import bc_export, close_report, hub, scorecard, sitemap

EXAMPLES = scorecard.ROOT / "docs" / "contracts" / "examples"


class SitemapCheckTest(unittest.TestCase):
    def test_broken_links_dead_buttons_and_pages_without_a_way_home_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").mkdir()
            (root / "index.html").write_text('<h1>Home</h1><a href="a/x.html">X</a><a href="gone.csv">Gone</a>', encoding="utf-8")
            (root / "a" / "x.html").write_text(
                '<h1>X</h1><button aria-controls="nowhere" aria-label="Open"></button><a href="#top">Top</a>', encoding="utf-8")
            (root / "a" / "y.html").write_text('<a href="../index.html">Home</a>', encoding="utf-8")
            path, pages, unlinked = sitemap.build(root)
            self.assertIn("Broken link “Gone” to gone.csv", pages["index.html"]["problems"])
            x = pages["a/x.html"]["problems"]
            self.assertIn("Button “Open” points at #nowhere, which is not on the page", x)
            self.assertIn("Anchor #top is not on the page", x)
            self.assertIn("No way back to the home page", x)
            self.assertEqual(unlinked, ["a/y.html"])
            self.assertIn("Not linked from anywhere", path.read_text(encoding="utf-8"))
            self.assertEqual(sitemap.main(["--root", str(root)]), 1)

    def test_the_suite_built_from_the_examples_has_no_broken_link_and_a_home_button_everywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "reports"
            for name in ("kpi.sample.month.json", "kpi.sample.week.json", "kpi.sample.day.json"):
                scorecard.build(EXAMPLES / name, root / "scorecard")
            self.assertEqual(bc_export.main(["--out", str(Path(tmp) / "close")]), 0)
            close_report.build("2026-09", Path(tmp) / "close", root / "close")
            hub.build(root)
            path, pages, unlinked = sitemap.build(root)
            problems = [(rel, p) for rel, page in pages.items() for p in page["problems"]]
            self.assertEqual(problems, [])
            self.assertEqual(unlinked, [])
            self.assertTrue(all(page["home"] for page in pages.values()))
            html = path.read_text(encoding="utf-8")
            self.assertIn("every page has a Home button", html)
            self.assertIn('id="n-close-2026-09-html"', html)
            self.assertIn('class="home-btn"', (root / "close" / "2026-09.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
