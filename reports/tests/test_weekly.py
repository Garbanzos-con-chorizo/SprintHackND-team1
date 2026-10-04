"""The weekly dashboard is the week's KPI file drawn by reports.scorecard: same numbers, one CSV, no own math."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reports import email_gen, scorecard, weekly

EXAMPLE = scorecard.ROOT / "docs" / "contracts" / "examples" / "kpi.sample.week.json"


class WeeklyTest(unittest.TestCase):
    def test_page_and_csv_come_from_the_kpi_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            kpis, dest = Path(tmp) / "kpi", Path(tmp) / "reports" / "scorecard"
            kpis.mkdir()
            shutil.copyfile(EXAMPLE, kpis / "week-2026-W40.json")
            weekly.main(["--date", "2026-10-01", "--kpi-dir", str(kpis), "--dest", str(dest)])
            html = (dest / "week-2026-W40.html").read_text(encoding="utf-8")
            kf = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            self.assertEqual(html, scorecard.render(kf, dest))
            self.assertEqual(html.count('<div class="tile '), 15)
            self.assertIn('href="week-2026-W40.csv"', html)
            self.assertTrue((dest / "week-2026-W40.csv").exists())

    def test_the_weekly_email_attaches_the_scorecard_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            kpis, root = Path(tmp) / "kpi", Path(tmp) / "reports"
            kpis.mkdir()
            shutil.copyfile(EXAMPLE, kpis / "week-2026-W40.json")
            weekly.main(["--week", "2026-W40", "--kpi-dir", str(kpis), "--dest", str(root / "scorecard")])
            report = email_gen.payload("Weekly", "2026-W40", root)
            self.assertEqual({p.suffix for p in report["attachments"]}, {".csv", ".html", ".json"})
            self.assertIn("Weekly dashboard - 2026-W40", report["subject"])


if __name__ == "__main__":
    unittest.main()
