"""Reconciliation from the raw messy-month inbox, checked against the answer key deposit by deposit
and payout by payout, plus the payout-window rule on hand-made rows."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from reports import bc_export as bc
from reports import reconcile

SAMPLE = reconcile.ROOT / "data" / "sample" / "messy_month"
PREFIX = {"EBAY": "ebay", "AMZN": "amazon", "SGW": "shopgoodwill"}
D = date.fromisoformat


class MessyMonthReconcileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = json.loads((SAMPLE / "expected.json").read_text(encoding="utf-8"))["close"]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.payload = reconcile.build(SAMPLE / "inbox", "2026-09", bc.load_mapping(), Path(cls.tmp.name) / "engine",
                                      {"close": cls.key})
        cls.paid = {p["id"]: p["paid_date"] for p in cls.key["payouts"]}
        cls.amounts = {(e["kind"], e["source"]): e["amount_cents"] for e in cls.payload["exceptions"]
                       if e["kind"] in ("payout_data_gap", "not_yet_paid_out")}

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
        self.assertEqual(self.amounts[("not_yet_paid_out", "ebay")], ebay_late["amount_cents"])

    def test_missing_reports_and_prior_month_refunds_are_detected_from_the_files(self):
        kinds = [e["kind"] for e in self.payload["exceptions"]]
        self.assertEqual(kinds.count("missing_report"), 2)
        self.assertEqual(kinds.count("prior_month_refund"), 2)
        self.assertIn("bad_amount", kinds)
        self.assertIn("bad_date", kinds)

    def test_shopgoodwill_deposits_become_payouts_with_the_weekly_windows_of_the_answer_key(self):
        # ShopGoodwill has no payout report in the files, so each of its deposits is a payout whose window
        # comes from the cycle in bc_mapping.csv (weekly, through Sunday).
        got = sorted((p["activity_from"], p["activity_to"], p["amount_cents"])
                     for p in self.payload["payouts"] if p["source"] == "shopgoodwill")
        expected = sorted((p["activity_from"], p["activity_to"], p["amount_cents"])
                          for p in self.key["payouts"] if p["source"] == "shopgoodwill")
        self.assertEqual(got, expected)
        self.assertTrue(all(p["inferred"] for p in self.payload["payouts"] if p["source"] == "shopgoodwill"))

    def test_every_payout_window_equals_the_answer_key(self):
        mine = {(p["source"], p["activity_to"]): p for p in self.payload["payouts"]}
        compared = 0
        for k in self.key["payouts"]:
            p = mine.get((k["source"], k["activity_to"]))
            if p is None:  # eBay's payout for Sep 30 is paid on Oct 1: not in September's files
                self.assertEqual((k["source"], k["paid_date"]), ("ebay", "2026-10-01"))
                continue
            self.assertEqual((p["activity_from"], p["files_net_cents"], p["gap_cents"]),
                             (k["activity_from"], k["net_in_files_cents"], k["data_gap_cents"]), k["id"])
            compared += 1
        self.assertEqual(compared, 35)

    def test_the_226_78_is_two_amounts_and_shopgoodwill_hides_nothing(self):
        totals = self.key["marketplace_totals_from_files"]
        gap = {p["source"]: p["data_gap_cents"] for p in self.key["payouts"] if p["data_gap_cents"]}
        self.assertEqual(gap, {"amazon": 74310, "shopgoodwill": 187564})
        for src in ("amazon", "shopgoodwill"):
            self.assertEqual(self.amounts[("payout_data_gap", src)], -gap[src])
            self.assertEqual(self.amounts[("not_yet_paid_out", src)], totals[src]["unpaid_activity_cents"])
        self.assertEqual(self.amounts[("not_yet_paid_out", "amazon")] + self.amounts[("payout_data_gap", "amazon")], -22678)
        details = {e["source"]: e["detail"] for e in self.payload["exceptions"] if e["kind"] == "payout_data_gap"}
        self.assertIn("2026-09-21 to 2026-09-22", details["amazon"])
        self.assertIn("2026-09-07", details["shopgoodwill"])

    def test_every_cent_is_explained_and_the_two_sources_read_incomplete(self):
        journal, _, control, _ = bc.build(self.payload, bc.load_mapping())
        self.assertEqual(bc.unbalanced(journal), {})
        self.assertEqual({r["Source"]: r["Status"] for r in control},
                         {"eBay": "OPEN", "ShopGoodwill": "INCOMPLETE", "Amazon": "INCOMPLETE"})
        self.assertEqual([r["Unexplained"] for r in control], [0, 0, 0])
        kinds = {e["kind"] for e in self.payload["exceptions"]}
        self.assertFalse(kinds & {"payout_mismatch", "no_order_times", "residual_unexplained"})


class MessyMonthWithoutOrderTimesTest(unittest.TestCase):
    """If the engine's rows carried no order time, the two sources that pay by Pacific days could not be
    checked payout by payout: they fall back to the older check of the open balance as one figure, and the
    output says so. (The engine writes `occurred_at` since transaction.md v0.5; this pins the fallback.)"""

    def test_sources_that_pay_by_pacific_days_fall_back_and_say_so(self):
        run_engine = reconcile.run_engine

        def without_times(inbox, out, month_end):
            rows, warnings = run_engine(inbox, out, month_end)
            for r in rows:
                r["occurred_at"] = ""
            return rows, warnings

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(reconcile, "run_engine", without_times):
            payload = reconcile.build(SAMPLE / "inbox", "2026-09", bc.load_mapping(), Path(tmp) / "engine")
        journal, _, control, _ = bc.build(payload, bc.load_mapping())
        self.assertEqual(bc.unbalanced(journal), {})
        self.assertEqual({e["source"] for e in payload["exceptions"] if e["kind"] == "no_order_times"},
                         {"amazon", "shopgoodwill"})
        # eBay pays by Eastern days, the engine's own day: still checked payout by payout.
        self.assertEqual({r["Source"]: r["Status"] for r in control},
                         {"eBay": "OPEN", "ShopGoodwill": "OPEN", "Amazon": "UNEXPLAINED"})
        self.assertEqual(sum("files_net_cents" in p for p in payload["payouts"]), 29)


class UnmappedMarketplaceTest(unittest.TestCase):
    """A marketplace with rows but no row in bc_mapping.csv (Goodwill Books arrives as `other`) is never
    left out in silence: it reaches the export, which reports it and posts nothing for it."""

    def test_rows_of_a_marketplace_without_a_mapping_row_become_an_exception(self):
        def row(marketplace, order_id, gross, fee=0):
            return {"marketplace": marketplace, "business_date": "2026-09-10", "type": "sale", "order_id": order_id,
                    "gross_cents": str(gross), "fee_cents": str(fee), "shipping_cents": "0", "handling_cents": "0"}

        rows = [row("ebay", "E-1", 5000, 650), row("other", "B-1", 1899, 285)]
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(reconcile, "run_engine", return_value=(rows, [])):
            engine = Path(tmp) / "engine"  # what the engine writes when no payout or bank line was reported
            engine.mkdir()
            (engine / "payouts.csv").write_text("payout_id,marketplace,paid_date,amount_cents,period_from,period_to\n")
            (engine / "bank.csv").write_text("bank_txn_id,account,posting_date,description,amount_cents\n")
            payload = reconcile.build(Path(tmp), "2026-09", bc.load_mapping(), engine)
        self.assertEqual(set(payload["sources"]), {"ebay", "other"})
        self.assertEqual(payload["origin"], "reconciled from the raw inbox")
        self.assertNotIn("mock", payload)

        journal, invoice, control, exceptions = bc.build(payload, bc.load_mapping())
        unmapped = [e for e in exceptions if e["kind"] == "unmapped_source"]
        self.assertEqual([(e["source"], e["amount_cents"], e["effect"]) for e in unmapped], [("other", 1614, "not_posted")])
        self.assertEqual(bc.unbalanced(journal), {})
        self.assertEqual([r["Source"] for r in control], ["eBay"])
        self.assertFalse(any("other" in str(line).lower() for line in journal + invoice))


class EngineFilesTest(unittest.TestCase):
    """The close reads the bank and the payouts from the engine's files (close-inputs.md), not from the
    raw reports."""

    def write(self, folder, name, text):
        (folder / name).write_text(text, encoding="utf-8")

    def test_bank_credits_are_classified_and_debits_left_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(Path(tmp), "bank.csv",
                       "bank_txn_id,account,posting_date,description,amount_cents,balance_cents,source_file,source_row\n"
                       "b:1,OPERATING,2026-09-04,EBAY COMMERCE INC DES:PAYOUT ID:0901,46947,,b.csv,1\n"
                       "b:2,OPERATING,2026-09-15,ADP PAYROLL DES:PAYROLL,-1834211,,b.csv,2\n"
                       "b:3,OPERATING,2026-09-17,REMOTE DEPOSIT CAPTURE REF 88213,41237,,b.csv,3\n")
            credits = reconcile.bank_credits(Path(tmp), bc.load_mapping())
        self.assertEqual([(c["date"], c["amount_cents"], c["source"]) for c in credits],
                         [(D("2026-09-04"), 46947, "ebay"), (D("2026-09-17"), 41237, None)])

    def test_payouts_keep_their_display_id_and_a_period_the_report_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(Path(tmp), "payouts.csv",
                       "payout_id,marketplace,paid_date,amount_cents,period_from,period_to,source_file,source_row\n"
                       "shopgoodwill:2026-09-14,shopgoodwill,2026-09-14,1531893,2026-09-07,2026-09-13,p.csv,2\n"
                       "ebay:2026-09-02#2,ebay,2026-09-02,100,,,e.csv,9\n"
                       "ebay:2026-09-02,ebay,2026-09-02,46947,,,e.csv,4\n")
            payouts = reconcile.reported_payouts(Path(tmp))
        self.assertEqual([p["id"] for p in payouts], ["EBAY-PAID-0902", "EBAY-PAID-0902-2", "SHOPGOODWILL-PAID-0914"])
        self.assertEqual((payouts[2]["period_from"], payouts[2]["period_to"]), (D("2026-09-07"), D("2026-09-13")))
        self.assertNotIn("period_from", payouts[0])

    def test_a_missing_engine_file_stops_the_close_with_a_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SystemExit) as stop:
            reconcile.reported_payouts(Path(tmp))
        self.assertIn("payouts.csv is missing", str(stop.exception))


class PayoutWindowTest(unittest.TestCase):
    """The rule itself, on hand-made rows."""

    MAPPING = {"Label": "Amazon", "Payout_Cutoff": "previous_day", "Payout_Timezone": "America/Los_Angeles"}
    FIRST, LAST = D("2026-09-01"), D("2026-09-30")

    @staticmethod
    def row(business_date, net, occurred_at=""):
        return {"business_date": business_date, "gross_cents": str(net), "shipping_cents": "0", "handling_cents": "0",
                "fee_cents": "0", "occurred_at": occurred_at}

    @staticmethod
    def payout(paid, amount, **extra):
        return {"id": f"P-{paid[5:7]}{paid[8:]}", "source": "amazon", "paid": D(paid), "amount_cents": amount, **extra}

    def explain(self, rows, payouts, covered=(), mapping=None):
        found = reconcile.explain_payouts("amazon", mapping or self.MAPPING, rows, payouts, set(covered),
                                          self.FIRST, self.LAST)
        return {e["kind"]: e for e in found}

    def test_windows_by_rule(self):
        def windows(rule, *paid, **extra):
            ps = reconcile.set_windows([self.payout(p, 1, **extra) for p in paid], rule, self.FIRST)
            return [(p["activity_from"].isoformat(), p["activity_to"].isoformat()) for p in ps]

        self.assertEqual(windows("daily", "2026-09-02", "2026-09-03"),
                         [("2026-09-01", "2026-09-01"), ("2026-09-02", "2026-09-02")])
        self.assertEqual(windows("previous_day", "2026-09-15", "2026-09-29"),
                         [("2026-09-01", "2026-09-14"), ("2026-09-15", "2026-09-28")])
        # Tuesday Sep 8 and Wednesday Sep 16 (a bank holiday pushed it): each covers through the Sunday before.
        self.assertEqual(windows("weekly:SUN", "2026-09-08", "2026-09-16"),
                         [("2026-09-01", "2026-09-06"), ("2026-09-07", "2026-09-13")])
        self.assertEqual(windows("daily", "2026-09-20", period_from=D("2026-09-07"), period_to=D("2026-09-13")),
                         [("2026-09-07", "2026-09-13")])
        with self.assertRaises(SystemExit):
            windows("fortnightly", "2026-09-15")

    def test_a_payout_that_equals_its_window_says_nothing(self):
        got = self.explain([self.row("2026-09-03", 1000, "2026-09-03T12:00:00-07:00")], [self.payout("2026-09-15", 1000)])
        self.assertEqual(got, {})

    def test_an_order_just_after_eastern_midnight_belongs_to_the_pacific_day_before(self):
        # 01:30 Eastern on the 15th is 22:30 Pacific on the 14th: inside the settlement that closes on the 14th.
        late = self.row("2026-09-15", 2326, "2026-09-15T01:30:00-04:00")
        self.assertEqual(self.explain([late], [self.payout("2026-09-15", 2326)]), {})
        self.assertEqual(reconcile.payout_day(late, "America/Los_Angeles"), (D("2026-09-14"), True))
        # Without the order time all we have is the Eastern day: exact for a marketplace that pays by
        # Eastern days, not for one that pays by Pacific days (the close then skips its payout windows).
        untimed = self.row("2026-09-15", 2326)
        self.assertEqual(reconcile.payout_day(untimed, "America/New_York"), (D("2026-09-15"), True))
        self.assertEqual(reconcile.payout_day(untimed, "America/Los_Angeles"), (D("2026-09-15"), False))
        # A time without an offset says nothing about the zone, so it is not trusted either.
        naive = self.row("2026-09-15", 2326, "2026-09-15T01:30:00")
        self.assertEqual(reconcile.payout_day(naive, "America/Los_Angeles"), (D("2026-09-15"), False))

    def test_paid_more_than_the_files_hold_with_days_no_report_covers_is_a_data_gap(self):
        rows = [self.row("2026-09-16", 5000, "2026-09-16T10:00:00-07:00")]
        covered = [d for d in (D(f"2026-09-{n:02d}") for n in range(1, 31)) if d.day not in (21, 22)]
        payouts = [self.payout("2026-09-15", 0), self.payout("2026-09-29", 5743)]
        got = self.explain(rows, payouts, covered)
        self.assertEqual(set(got), {"payout_data_gap"})
        self.assertEqual((got["payout_data_gap"]["amount_cents"], got["payout_data_gap"]["effect"]), (-743, "open_balance"))
        self.assertIn("2026-09-21 to 2026-09-22", got["payout_data_gap"]["detail"])
        self.assertEqual(payouts[1]["days_missing"], ["2026-09-21", "2026-09-22"])

    def test_a_difference_with_no_missing_day_is_a_mismatch_never_a_data_gap(self):
        rows = [self.row("2026-09-16", 5000, "2026-09-16T10:00:00-07:00")]
        covered = [D(f"2026-09-{n:02d}") for n in range(1, 31)]
        got = self.explain(rows, [self.payout("2026-09-15", 0), self.payout("2026-09-29", 5743)], covered)
        self.assertEqual(set(got), {"payout_mismatch"})
        self.assertEqual((got["payout_mismatch"]["amount_cents"], got["payout_mismatch"]["effect"]), (743, "info"))
        # Paid less than the files hold is never "missing data", even when a report is missing.
        got = self.explain(rows, [self.payout("2026-09-15", 0), self.payout("2026-09-29", 4000)], covered[:20])
        self.assertEqual(set(got), {"payout_mismatch"})

    def test_activity_after_the_last_cutoff_is_not_yet_paid_out_to_the_cent(self):
        rows = [self.row("2026-09-10", 1000, "2026-09-10T09:00:00-07:00"),
                self.row("2026-09-29", 300, "2026-09-29T09:00:00-07:00"),
                self.row("2026-09-30", 216, "2026-09-30T09:00:00-07:00")]
        got = self.explain(rows, [self.payout("2026-09-15", 1000)])
        self.assertEqual(set(got), {"not_yet_paid_out"})
        self.assertEqual(got["not_yet_paid_out"]["amount_cents"], 516)
        self.assertIn("2026-09-29 to 2026-09-30", got["not_yet_paid_out"]["detail"])

    def test_a_payout_for_last_months_activity_is_not_matched_against_this_month(self):
        mapping = {**self.MAPPING, "Payout_Cutoff": "daily"}
        got = self.explain([], [self.payout("2026-09-01", 4200)], mapping=mapping)
        self.assertEqual(set(got), {"prior_month_payout"})
        self.assertEqual((got["prior_month_payout"]["amount_cents"], got["prior_month_payout"]["effect"]),
                         (-4200, "open_balance"))

    def test_day_ranges(self):
        days = [D("2026-09-30"), D("2026-09-21"), D("2026-09-22"), D("2026-09-21")]
        self.assertEqual(reconcile.day_ranges(days), "2026-09-21 to 2026-09-22, 2026-09-30")


if __name__ == "__main__":
    unittest.main()
