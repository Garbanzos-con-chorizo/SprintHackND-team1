"""The tidy month through the close: every report downloaded once, so nothing is left unexplained (D3.6).

The inbox is synthetic (`data/generate.py`); the answer key is computed from the generated events, never
by the engine. Everything is written to a temporary folder, never to the real `out/` or `reports/`.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from reports import bc_export as bc
from reports import reconcile, run_scheduled

SAMPLES = reconcile.ROOT / "data" / "sample"
SAMPLE = SAMPLES / "tidy_month"
PREFIX = {"EBAY": "ebay", "AMZN": "amazon", "SGW": "shopgoodwill"}
TIDY_KINDS = {"in_transit", "not_yet_paid_out"}


class TidyMonthCloseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = json.loads((SAMPLE / "expected.json").read_text(encoding="utf-8"))["close"]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.mapping = bc.load_mapping()
        cls.payload = reconcile.build(SAMPLE / "inbox", "2026-09", cls.mapping, Path(cls.tmp.name) / "engine")
        cls.journal, cls.invoice, cls.control, cls.exceptions = bc.build(cls.payload, cls.mapping)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_journal_document_balances(self):
        self.assertTrue(self.journal)
        self.assertEqual(bc.unbalanced(self.journal), {})

    def test_every_source_is_open_with_nothing_unexplained(self):
        for r in self.control:
            self.assertEqual((r["Unexplained"], r["Status"]), (0, "OPEN"), r["Source"])
        labels = {self.mapping[s]["Label"] for s in PREFIX.values()}
        self.assertLessEqual(labels, {r["Source"] for r in self.control})

    def test_every_deposit_is_classified_to_its_source_and_none_is_unmatched(self):
        self.assertTrue(self.key["bank_deposits"])
        self.assertEqual({d["status"] for d in self.key["bank_deposits"]}, {"matched"})
        expected = sorted((d["date"], d["amount_cents"], PREFIX[d["matches"][0].split("-")[0]])
                          for d in self.key["bank_deposits"])
        got = sorted((d["date"], d["amount_cents"], d["source"]) for d in self.payload["deposits"])
        self.assertEqual(got, expected)
        self.assertEqual([e for e in self.exceptions if e["kind"] == "unmatched_deposit"], [])

    def test_the_only_exceptions_are_money_in_transit_and_activity_not_yet_paid_out(self):
        self.assertTrue(self.exceptions)
        self.assertEqual({e["kind"] for e in self.exceptions} - TIDY_KINDS, set())

    def test_month_totals_per_source_equal_the_answer_key(self):
        totals = self.key["marketplace_totals_from_files"]
        self.assertEqual(set(totals), set(PREFIX.values()))
        for src, want in totals.items():
            got = self.payload["sources"][src]
            for field in ("sales_cents", "fees_cents", "shipping_cents", "handling_cents"):
                self.assertEqual(got[field], want[field], f"{src} {field}")
            # The key stores refunds negative, the payload positive.
            self.assertEqual(got["refunds_cents"], -want["refunds_cents"], f"{src} refunds_cents")

    def test_the_scheduled_close_still_reads_the_messy_month(self):
        # run_scheduled takes the first sample in name order whose key has close.month;
        # tidy_month sorts after messy_month on purpose.
        self.assertEqual(run_scheduled.month_inbox("2026-09"), SAMPLES / "messy_month" / "inbox")


class MonthSideFoldersTest(unittest.TestCase):
    """periodic/ and cashmonkey/ sit beside inbox/ in both months (synthetic layouts, see data/README.md)."""

    def test_the_periodic_report_states_the_four_shopgoodwill_payouts_of_the_key(self):
        us = lambda iso: f"{iso[5:7]}/{iso[8:]}/{iso[:4]}"
        for month in ("messy_month", "tidy_month"):
            key = json.loads((SAMPLES / month / "expected.json").read_text(encoding="utf-8"))["close"]
            expected = [(us(p["activity_from"]), us(p["activity_to"]), us(p["paid_date"]),
                         f"{p['amount_cents'] // 100}.{p['amount_cents'] % 100:02d}", p["id"])
                        for p in key["payouts"] if p["source"] == "shopgoodwill"]
            with open(SAMPLES / month / "periodic" / "shopgoodwill_periodic_2026-09.csv", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], ["Period Start", "Period End", "Paid Date", "Payout Amount", "Reference"])
            self.assertEqual([tuple(r) for r in rows[1:]], expected, month)
            self.assertEqual(len(expected), 4)

    def test_the_side_folders_are_not_in_the_inbox(self):
        for month in ("messy_month", "tidy_month"):
            self.assertEqual([p.name for p in (SAMPLES / month / "cashmonkey").iterdir()],
                             ["orders2023-20261001-001512-96170.xlsx"])
            names = [p.name for p in (SAMPLES / month / "inbox").iterdir()]
            self.assertEqual([n for n in names if n.startswith(("orders2023", "shopgoodwill_periodic"))], [])


if __name__ == "__main__":
    unittest.main()
