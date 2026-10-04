"""The fix a person would make to the messy month: the two reports nobody downloaded are found and
dropped in the inbox, the close runs again, and the two gaps close (D3.9).

`data/sample/messy_month/late/` holds those two reports; `expected_after_late.json` is the answer key of
the month once they are in, computed from the generated events, never by the engine."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reports import bc_export as bc
from reports import reconcile

SAMPLE = reconcile.ROOT / "data" / "sample" / "messy_month"


class LateReportsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = json.loads((SAMPLE / "expected.json").read_text(encoding="utf-8"))["close"]
        cls.key = json.loads((SAMPLE / "expected_after_late.json").read_text(encoding="utf-8"))["close"]
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / "inbox"
            shutil.copytree(SAMPLE / "inbox", inbox)
            for f in (SAMPLE / "late").iterdir():
                shutil.copy(f, inbox)
            cls.payload = reconcile.build(inbox, "2026-09", bc.load_mapping(), Path(tmp) / "engine")
        cls.journal, _, cls.control, cls.exceptions = bc.build(cls.payload, bc.load_mapping())

    def test_the_late_folder_holds_exactly_the_two_reports_the_first_close_asked_for(self):
        self.assertEqual(sorted(p.name for p in (SAMPLE / "late").iterdir()),
                         ["amazon_daterange_2026-09-21_2026-09-22.csv", "paid_orders_09-07-2026_09-07-2026.xlsx"])
        self.assertEqual({p["source"]: p["data_gap_cents"] for p in self.before["payouts"] if p["data_gap_cents"]},
                         {"amazon": 74310, "shopgoodwill": 187564})
        self.assertEqual(sum(p["data_gap_cents"] for p in self.key["payouts"]), 0)

    def test_no_report_is_missing_and_no_source_is_incomplete_any_more(self):
        self.assertEqual(bc.unbalanced(self.journal), {})
        self.assertEqual({r["Source"]: (r["Status"], r["Unexplained"]) for r in self.control},
                         {"eBay": ("OPEN", 0), "Amazon": ("OPEN", 0), "ShopGoodwill": ("OPEN", 0)})
        kinds = {e["kind"] for e in self.exceptions}
        self.assertFalse(kinds & {"payout_data_gap", "missing_report", "payout_mismatch"})

    def test_the_rest_of_the_mess_is_still_reported(self):
        kinds = [e["kind"] for e in self.exceptions]
        self.assertEqual(kinds.count("unmatched_deposit"), 1)
        self.assertEqual(kinds.count("prior_month_refund"), 2)
        self.assertIn("bad_amount", kinds)
        self.assertIn("bad_date", kinds)
        self.assertIn("duplicate_rows", kinds)

    def test_totals_and_every_payout_equal_the_answer_key_of_the_completed_month(self):
        totals = self.key["marketplace_totals_from_files"]
        for src, want in totals.items():
            got = self.payload["sources"][src]
            self.assertEqual((got["sales_cents"], got["refunds_cents"], got["fees_cents"], got["shipping_cents"],
                              got["handling_cents"]),
                             (want["sales_cents"], -want["refunds_cents"], want["fees_cents"], want["shipping_cents"],
                              want["handling_cents"]), src)
            self.assertEqual(bc.net(got), want["net_cents"], src)
        mine = {(p["source"], p["activity_to"]): p for p in self.payload["payouts"]}
        compared = 0
        for k in self.key["payouts"]:
            p = mine.get((k["source"], k["activity_to"]))
            if p is not None:
                self.assertEqual((p["files_net_cents"], p["gap_cents"]), (k["net_in_files_cents"], 0), k["id"])
                compared += 1
        self.assertEqual(compared, 35)
        unpaid = {e["source"]: e["amount_cents"] for e in self.exceptions if e["kind"] == "not_yet_paid_out"}
        self.assertEqual((unpaid["amazon"], unpaid["shopgoodwill"]),
                         (totals["amazon"]["unpaid_activity_cents"], totals["shopgoodwill"]["unpaid_activity_cents"]))


if __name__ == "__main__":
    unittest.main()
