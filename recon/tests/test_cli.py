import contextlib
import io as stdio
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from recon.pulse import cli

FIXTURES = Path(__file__).parent / "fixtures"


def run(*argv):
    with contextlib.redirect_stdout(stdio.StringIO()), contextlib.redirect_stderr(stdio.StringIO()):
        return cli.main(list(argv))


class PulseCommand(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "out"
        shutil.copytree(FIXTURES / "clean_day", self.out)

    def read(self, name):
        return json.loads((self.out / "pulse" / name).read_text(encoding="utf-8"))

    def test_default_date_comes_from_source_status(self):
        self.assertEqual(run("--in-dir", str(self.out)), 0)
        pulse = self.read("2026-10-02.json")
        self.assertEqual(pulse["enterprise"]["revenue_cents"], 30147)
        self.assertEqual(pulse["enterprise"]["delta"]["revenue_cents"], 4347)
        self.assertTrue(pulse["generated_at"])
        self.assertEqual(self.read("latest.json"), pulse)

    def test_latest_stays_on_the_greatest_date(self):
        run("--in-dir", str(self.out))
        self.assertEqual(run("--in-dir", str(self.out), "--date", "2026-10-01"), 0)
        self.assertEqual(self.read("2026-10-01.json")["enterprise"]["revenue_cents"], 25800)
        self.assertEqual(self.read("latest.json")["business_date"], "2026-10-02")

    def test_prior_pulse_file_is_used_for_the_delta(self):
        run("--in-dir", str(self.out), "--date", "2026-10-01")
        prior_path = self.out / "pulse" / "2026-10-01.json"
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        prior["marketplaces"]["ebay"]["status"] = "missing"
        prior["enterprise"]["included"] = ["shopgoodwill", "amazon"]
        prior_path.write_text(json.dumps(prior), encoding="utf-8")

        run("--in-dir", str(self.out))
        pulse = self.read("2026-10-02.json")
        self.assertEqual(pulse["marketplaces"]["ebay"]["delta"]["reason"], "prior_unavailable")
        self.assertEqual(pulse["enterprise"]["delta"]["reason"], "coverage_changed")

    def test_unreadable_prior_file_falls_back_to_the_rows(self):
        (self.out / "pulse").mkdir()
        (self.out / "pulse" / "2026-10-01.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(run("--in-dir", str(self.out)), 0)
        self.assertEqual(self.read("2026-10-02.json")["enterprise"]["delta"]["revenue_cents"], 4347)

    def test_out_dir_option(self):
        elsewhere = self.out.parent / "elsewhere"
        self.assertEqual(run("--in-dir", str(self.out), "--out-dir", str(elsewhere)), 0)
        self.assertTrue((elsewhere / "2026-10-02.json").exists())

    def test_no_transactions_file_is_an_error(self):
        self.assertEqual(run("--in-dir", str(self.out / "nope")), 1)

    def test_no_date_and_no_status_file_is_an_error(self):
        (self.out / "source_status.json").unlink()
        self.assertEqual(run("--in-dir", str(self.out)), 1)
        self.assertEqual(run("--in-dir", str(self.out), "--date", "2026-10-02"), 0)


if __name__ == "__main__":
    unittest.main()
