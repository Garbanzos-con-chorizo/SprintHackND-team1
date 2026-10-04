"""Reconciliation from the raw messy-month inbox, checked against the answer key deposit by deposit."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from reports import bc_export as bc
from reports import reconcile

SAMPLE = reconcile.ROOT / "data" / "sample" / "messy_month"
PREFIX = {"EBAY": "ebay", "AMZN": "amazon", "SGW": "shopgoodwill"}


class MessyMonthReconcileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = json.loads((SAMPLE / "expected.json").read_text(encoding="utf-8"))["close"]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.payload = reconcile.build(SAMPLE / "inbox", "2026-09", bc.load_mapping(), Path(cls.tmp.name) / "engine")
        cls.paid = {p["id"]: p["paid_date"] for p in cls.key["payouts"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_deposit_is_classified_and_matched_like_the_answer_key(self):
        expected, got = {}, {}
        for d in self.key["bank_deposits"]:
            if d["matches"]:
                src = PREFIX[d["matches"][0].split("-")[0]]
                payouts = sorted(self.paid[m] for m in d["matches"]) if src != "shopgoodwill" else []
                expected[(d["date"], d["amount_cents"])] = (src, payouts)
        by_id = {p["id"]: p["paid"] for p in self.payload["payouts"]}
        for d in self.payload["deposits"]:
            got[(d["date"], d["amount_cents"])] = (d["source"], sorted(by_id[m] for m in d["matches"]))
        self.assertEqual(len(got), 23)
        self.assertEqual(got, expected)

    def test_multi_payout_deposits(self):
        multi = sorted(d["date"] for d in self.payload["deposits"] if len(d["matches"]) > 1)
        expected = sorted(d["date"] for d in self.key["bank_deposits"] if len(d["matches"]) > 1)
        self.assertEqual(multi, expected)
        self.assertEqual(len(multi), 4)

    def test_the_412_37_deposit_is_unmatched(self):
        unmatched = [e for e in self.payload["exceptions"] if e["kind"] == "unmatched_deposit"]
        self.assertEqual([(e["amount_cents"], e["effect"]) for e in unmatched], [(41237, "not_posted")])

    def test_in_transit_payouts(self):
        # The answer key has 4 payouts not in the bank on Sep 30; one of them (eBay for Sep 30) is paid on
        # Oct 1, so September's files can't contain it: it shows up as activity not yet paid out instead.
        key_transit = {(p["source"], p["paid_date"]) for p in self.key["payouts"] if p["status"] == "in_transit"}
        paid_in_month = {k for k in key_transit if date.fromisoformat(k[1]) <= date(2026, 9, 30)}
        got = {(p["source"], p["paid"]) for p in self.payload["payouts"] if not p["deposit"]}
        self.assertEqual(len(key_transit), 4)
        self.assertEqual(got, paid_in_month)
        ebay_late = next(p for p in self.key["payouts"] if p["source"] == "ebay" and p["paid_date"] == "2026-10-01")
        not_paid = next(e for e in self.payload["exceptions"]
                        if e["kind"] == "not_yet_paid_out" and e["source"] == "ebay")
        self.assertEqual(not_paid["amount_cents"], ebay_late["amount_cents"])

    def test_missing_reports_and_prior_month_refunds_are_detected_from_the_files(self):
        kinds = [e["kind"] for e in self.payload["exceptions"]]
        self.assertEqual(kinds.count("missing_report"), 2)
        self.assertEqual(kinds.count("prior_month_refund"), 2)
        self.assertIn("bad_amount", kinds)
        self.assertIn("bad_date", kinds)

    def test_close_balances_and_amazon_gap_is_not_hidden(self):
        journal, _, control, _ = bc.build(self.payload, bc.load_mapping())
        self.assertEqual(bc.unbalanced(journal), {})
        status = {r["Source"]: r["Status"] for r in control}
        self.assertEqual(status, {"eBay": "OPEN", "ShopGoodwill": "OPEN", "Amazon": "UNEXPLAINED"})


if __name__ == "__main__":
    unittest.main()
