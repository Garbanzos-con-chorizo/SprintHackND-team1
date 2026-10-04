"""The month-end close page says what it is: what is simulated, what is not posted, who owns each
exception, and what this run has for each of Goodwill's nine month-end sources (D3.8)."""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from reports import bc_export as bc
from reports import close_report, reconcile

SAMPLES = reconcile.ROOT / "data" / "sample"
MONTH = "2026-09"


def close_into(out, inbox):
    """What the close leaves in out/<month>/: the payload, the engine's files and the four CSVs."""
    folder = out / MONTH
    mapping = bc.load_mapping()
    payload = reconcile.build(inbox, MONTH, mapping, folder / "engine")
    (folder / f"close_payload_{MONTH}.json").write_text(json.dumps(payload), encoding="utf-8")
    journal, invoice, control, exceptions = bc.build(payload, mapping)
    bc.write(folder, MONTH, journal, invoice, control, exceptions, mapping)
    return payload


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class ClosePageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        close_into(tmp / "messy", SAMPLES / "messy_month" / "inbox")
        cls.messy = close_report.build(MONTH, src=tmp / "messy", dest=tmp / "messy_pages").read_text(encoding="utf-8")
        inbox = tmp / "tidy_inbox"  # the tidy month with the Cash Monkey month file dropped in as well
        shutil.copytree(SAMPLES / "tidy_month" / "inbox", inbox)
        for f in (SAMPLES / "tidy_month" / "cashmonkey").iterdir():
            shutil.copy(f, inbox)
        close_into(tmp / "tidy", inbox)
        cls.tidy = close_report.build(MONTH, src=tmp / "tidy", dest=tmp / "tidy_pages").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def states(self, html):
        """{source: what the page says this run has for it}."""
        rows = re.findall(r'<tr class="src"><td>(.*?)</td>.*?<span class="state[^"]*">(.*?)</span>', html, re.S)
        return dict(rows)

    def test_the_page_says_what_is_simulated_and_that_nothing_is_posted(self):
        for html in (self.messy, self.tidy):
            text = text_of(html)
            self.assertIn("Synthetic sample data", text)
            self.assertIn("placeholders", text)
            self.assertIn("Posting status: Not posted", text)
            self.assertIn("role names we chose", text)

    def test_all_nine_sources_are_listed_with_what_this_run_has(self):
        states = self.states(self.messy)
        self.assertEqual(list(states), ["Cash Monkey", "Upright", "Jewelry", "OSM / PB / EasyPost", "FedEx",
                                        "ShopGoodwill", "Goodwill Books", "eBay", "Amazon"])
        for source in ("Upright", "eBay", "Amazon"):
            self.assertEqual(states[source], "sample file", source)
        self.assertEqual(states["Cash Monkey"], "not in this inbox")
        # A source no file reached is never shown as captured.
        for source in ("Jewelry", "OSM / PB / EasyPost", "FedEx", "Goodwill Books", "ShopGoodwill"):
            self.assertEqual(states[source], "not in this inbox", source)
        self.assertIn("a report is missing for some days", self.messy)
        self.assertNotIn("a report is missing for some days", self.tidy)

    def test_every_source_has_a_place_to_choose_the_file_downloaded_by_hand(self):
        # Decision 012: Goodwill's Controller downloads the month-end reports by hand, so the page says so and
        # each of the nine sources has its own file picker; one button hands the chosen files to the close.
        for html in (self.messy, self.tidy):
            rows = re.findall(r'<tr class="src">.*?</tr>', html, re.S)
            self.assertEqual(len(rows), 9)
            for row in rows:
                self.assertEqual(row.count('<input type="file" class="src-file"'), 1, row)
            self.assertIn("Controller downloads these reports by hand today", text_of(html))
            self.assertIn(f'id="pick" data-month="{MONTH}"', html)
            self.assertIn('id="pick-run"', html)
            self.assertIn("Goodwill has no such API today", html)
            self.assertNotIn(">Post<", html)

    def test_a_source_is_only_called_simulated_when_its_file_reached_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / MONTH
            (folder / "engine").mkdir(parents=True)
            payload = {"sources": {"ebay": {}}, "exceptions": [], "cross_checks": []}
            absent = {r["Source"]: present for r, present, _ in close_report.source_states(folder, payload)}
            self.assertEqual([s for s, present in absent.items() if present], ["eBay"])
            (folder / "engine" / "ledger.csv").write_text("posting_date,amount_cents\n2026-09-03,1200\n")
            (folder / "engine" / "statements.csv").write_text("source,net_cents\n")  # header only: nothing arrived
            (folder / "engine" / "bank.csv").write_text("bank_txn_id,account\nb:1,OPERATING\nb:2,0101\n")
            (folder / "engine" / "payouts.csv").write_text("payout_id,marketplace,period_from\ns:1,shopgoodwill,2026-09-07\n")
            present = {r["Source"]: p for r, p, _ in close_report.source_states(folder, payload)}
            self.assertEqual([s for s, p in present.items() if p], ["OSM / PB / EasyPost", "FedEx", "ShopGoodwill", "eBay"])

    def test_exceptions_show_their_owner_and_what_to_do(self):
        self.assertIn('<th class="text">Owner</th><th class="text">What to do</th>', self.messy)
        self.assertIn("Download the missing report and run the close again", self.messy)
        self.assertIn('<span class="pill missing">INCOMPLETE</span>', self.messy)
        self.assertNotIn("INCOMPLETE</span>", self.tidy)

    def test_the_cash_monkey_cross_check_is_shown_when_its_file_is_in_the_inbox(self):
        self.assertNotIn("Cross-check:", self.messy)
        self.assertIn("Cross-check: Cash Monkey", self.tidy)
        self.assertEqual(self.states(self.tidy)["Cash Monkey"], "sample file")
        self.assertIn("$31.99", self.tidy)  # the one Amazon order no September report holds

    def test_the_run_history_appears_when_the_close_command_has_written_one(self):
        self.assertNotIn("Run history", self.messy)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            shutil.copytree(Path(self.tmp.name) / "messy", out)
            (out / MONTH / "runs.csv").write_text("run_id,needs_review\n2026-10-01T00-15-07,True\n", encoding="utf-8")
            html = close_report.build(MONTH, src=out, dest=Path(tmp) / "pages").read_text(encoding="utf-8")
        self.assertIn("Run history", html)
        self.assertIn("2026-10-01T00-15-07", html)


if __name__ == "__main__":
    unittest.main()
