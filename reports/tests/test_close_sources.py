"""The close on the month-end sources nobody has shown us, delivered by Victor's simulated APIs:
shipping cost (D3.5: carriers from bank account 0101, FedEx from Business Central's ledger) and the
Goodwill Books statement (D3.13), plus ShopGoodwill's periodic report as its payouts.

The files come from `python -m engine fetch --simulate --close-month`, and every figure is checked
against `expected_close_sources.json`, which that command computes from the records it generated, never
with the engine's parsers and never with this code. Nothing here imports the simulators."""
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reports import bc_export as bc
from reports import reconcile

SAMPLE = reconcile.ROOT / "data" / "sample" / "tidy_month"
MONTH = "2026-09"


class SimulatedSourcesCloseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        fetched = subprocess.run([sys.executable, "-m", "engine", "fetch", "--simulate", "--close-month", MONTH,
                                  "--inbox", str(tmp / "sim"), "--out", str(tmp / "fetch")],
                                 cwd=reconcile.ROOT, capture_output=True, text=True)
        assert fetched.returncode == 0, fetched.stdout + fetched.stderr
        cls.key = json.loads((tmp / "fetch" / "expected_close_sources.json").read_text(encoding="utf-8"))
        cls.inbox = tmp / "inbox"  # the tidy month, its periodic report, and the simulated sources
        shutil.copytree(SAMPLE / "inbox", cls.inbox)
        for folder in (SAMPLE / "periodic", tmp / "sim"):
            for f in folder.iterdir():
                shutil.copy(f, cls.inbox)
        cls.mapping = bc.load_mapping()
        cls.payload = reconcile.build(cls.inbox, MONTH, cls.mapping, tmp / "engine")
        cls.journal, cls.invoice, cls.control, cls.exceptions = bc.build(cls.payload, cls.mapping)
        cls.shipping = {c["carrier"]: c for c in cls.payload["shipping_costs"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_each_bank_paid_carrier_equals_the_answer_key(self):
        carriers = self.key["carriers"]
        for name in ("osm", "pb", "easypost"):
            got = self.shipping[name]
            self.assertEqual((got["net_cents"], got["lines"], got["refunds_cents"]),
                             (carriers[name]["cents"], carriers[name]["payments"], 0), name)
            self.assertIn(carriers[name]["bank_text"], got["figure_from"])
        # The account's other debits (supplies, the service charge) are nobody's shipping cost.
        self.assertGreater(carriers["other_debits"], 0)
        self.assertEqual(sum(self.shipping[n]["net_cents"] for n in ("osm", "pb", "easypost")), carriers["total_cents"])

    def test_fedex_is_the_filtered_ledger_net_of_the_refunds_that_came_back_as_deposits(self):
        want, got = self.key["fedex"], self.shipping["fedex"]
        self.assertEqual((got["charges_cents"], got["refunds_cents"], got["net_cents"], got["lines"]),
                         (want["charges_cents"], want["refunds_cents"], want["net_cents"], want["entries"]))
        self.assertGreater(want["refunds_cents"], 0)
        # The ledger also holds entries of another vendor, department and account: the filter leaves them out.
        with open(Path(self.tmp.name) / "engine" / "ledger.csv", encoding="utf-8", newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))) - got["lines"], want["entries_left_out"])
        self.assertGreater(want["entries_left_out"], 0)

    def test_only_the_bank_paid_carriers_are_posted_and_the_document_balances(self):
        self.assertEqual(bc.unbalanced(self.journal), {})
        doc = [l for l in self.journal if l["Document No."] == "ECOM-2609-SHIP"]
        debits = [l for l in doc if l["Amount"] > 0]
        self.assertEqual(sorted(l["Description"].split(" shipping cost")[0] for l in debits), ["EasyPost", "OSM", "PB"])
        self.assertEqual(sum(l["Amount"] for l in debits), self.key["carriers"]["total_cents"])
        credit = [l for l in doc if l["Amount"] < 0]
        self.assertEqual([(l["Account No."], l["Amount"]) for l in credit], [("10009", -self.key["carriers"]["total_cents"])])
        # FedEx is already in Business Central: reported, never posted again.
        self.assertIsNone(self.shipping["fedex"]["post"])
        self.assertFalse(any(l["Account No."] == self.key["fedex"]["gl_account"] for l in self.journal))

    def test_the_goodwill_books_statement_posts_and_reconciles_with_its_bank_credit(self):
        want, got = self.key["goodwillbooks"], self.payload["sources"]["goodwillbooks"]
        self.assertEqual((got["sales_cents"], got["fees_cents"], bc.net(got)),
                         (want["sales_cents"], want["fees_cents"], want["net_cents"]))
        books = next(r for r in self.control if r["Source"] == "Goodwill Books")
        self.assertEqual((books["Status"], books["Open Balance"], books["Unexplained"], books["Deposits"]),
                         ("RECONCILED", 0, 0, want["net_cents"]))
        deposit = next(d for d in self.payload["deposits"] if d["source"] == "goodwillbooks")
        self.assertEqual((deposit["date"], deposit["amount_cents"], deposit["matches"]),
                         (want["paid_date"], want["net_cents"], [want["reference"]]))
        # The statement reports August and is paid in September: it posts in September and says which month it is.
        sales = next(l for l in self.journal if l["Document No."] == "ECOM-2609-GWB" and l["Amount"] == -want["sales_cents"])
        self.assertIn("Aug 2026", sales["Description"])
        self.assertIn(want["reference"], sales["Description"])

    def test_nothing_is_left_unmatched_and_the_marketplaces_are_unchanged(self):
        kinds = {e["kind"] for e in self.exceptions}
        self.assertLessEqual(kinds, {"in_transit", "not_yet_paid_out", "missing_supplier"})
        status = {r["Source"]: (r["Status"], r["Unexplained"]) for r in self.control}
        self.assertEqual(status, {"eBay": ("OPEN", 0), "Amazon": ("OPEN", 0), "ShopGoodwill": ("OPEN", 0),
                                  "Goodwill Books": ("RECONCILED", 0)})

    def test_shopgoodwill_payouts_come_from_its_periodic_report_with_their_own_periods(self):
        key = json.loads((SAMPLE / "expected.json").read_text(encoding="utf-8"))["close"]
        got = sorted((p["activity_from"], p["activity_to"], p["amount_cents"], p["gap_cents"])
                     for p in self.payload["payouts"] if p["source"] == "shopgoodwill")
        want = sorted((p["activity_from"], p["activity_to"], p["amount_cents"], 0)
                      for p in key["payouts"] if p["source"] == "shopgoodwill")
        self.assertEqual(got, want)
        self.assertFalse(any(p.get("inferred") for p in self.payload["payouts"]))

    def test_a_statement_whose_payment_is_not_in_the_bank_is_not_reconciled(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / "inbox"
            shutil.copytree(self.inbox, inbox)
            (inbox / f"bank_activity_0101_{MONTH}.csv").unlink()
            payload = reconcile.build(inbox, MONTH, self.mapping, Path(tmp) / "engine")
        journal, _, control, exceptions = bc.build(payload, self.mapping)
        self.assertEqual(bc.unbalanced(journal), {})
        books = next(r for r in control if r["Source"] == "Goodwill Books")
        net = self.key["goodwillbooks"]["net_cents"]
        self.assertEqual((books["Status"], books["Unexplained"]), ("UNEXPLAINED", net))
        found = [e for e in exceptions if e["kind"] == "statement_not_in_bank"]
        self.assertEqual([(e["source"], e["amount_cents"]) for e in found], [("goodwillbooks", net)])
        # With that account's feed gone, its carriers are not listed at all; FedEx, from the ledger, still is.
        self.assertEqual([c["carrier"] for c in payload["shipping_costs"]], ["fedex"])


class ShippingRuleTest(unittest.TestCase):
    """The rule on hand-made rows."""

    CARRIERS = reconcile.load_shipping()
    IN_MONTH = staticmethod(lambda iso: "2026-09-01" <= iso <= "2026-09-30")

    @staticmethod
    def bank(account, day, description, cents):
        return {"account": account, "posting_date": day, "description": description, "amount_cents": str(cents)}

    @staticmethod
    def entry(day, document_no, cents, account="40356", department="180", vendor="V00122"):
        return {"posting_date": day, "document_no": document_no, "gl_account": account, "department": department,
                "vendor_no": vendor, "amount_cents": str(cents)}

    def test_a_source_that_did_not_reach_the_run_is_not_listed(self):
        operating = [self.bank("OPERATING", "2026-09-04", "EBAY COMMERCE INC DES:PAYOUT", 46947)]
        self.assertEqual(reconcile.shipping_costs(operating, None, self.CARRIERS, self.IN_MONTH), [])
        # An empty ledger is a ledger: FedEx is listed, with nothing in it.
        only = reconcile.shipping_costs(operating, [], self.CARRIERS, self.IN_MONTH)
        self.assertEqual([(c["carrier"], c["net_cents"], c["lines"]) for c in only], [("fedex", 0, 0)])

    def test_a_carrier_is_its_account_and_its_text_in_the_month(self):
        rows = [self.bank("0101", "2026-09-07", "OSM WORLDWIDE DES:POSTAGE ID:0907", -42287),
                self.bank("0101", "2026-09-20", "osm worldwide refund", 1000),      # a refund: netted
                self.bank("0101", "2026-10-02", "OSM WORLDWIDE DES:POSTAGE ID:1002", -5000),  # next month
                self.bank("OPERATING", "2026-09-09", "OSM WORLDWIDE DES:POSTAGE", -7000),     # another account
                self.bank("0101", "2026-09-03", "ULINE DES:SHIPPING SUPPLIES", -22558)]       # no carrier
        osm = next(c for c in reconcile.shipping_costs(rows, None, self.CARRIERS, self.IN_MONTH) if c["carrier"] == "osm")
        self.assertEqual((osm["charges_cents"], osm["refunds_cents"], osm["net_cents"], osm["lines"]), (42287, 1000, 41287, 2))
        self.assertEqual(osm["post"], {"expense_account": "60510", "offset_account": "10009", "department": "180"})

    def test_fedex_takes_only_its_account_department_and_vendor(self):
        ledger = [self.entry("2026-09-01", "PI-1", 42824), self.entry("2026-09-12", "BNKDEPOSIT-0912", -5000),
                  self.entry("2026-09-03", "PI-2", 13332, department="110"),
                  self.entry("2026-09-05", "PI-3", 9900, vendor="V00340"),
                  self.entry("2026-09-06", "PI-4", 7700, account="40310"),
                  self.entry("2026-10-01", "PI-5", 6600)]
        fedex = reconcile.shipping_costs([], ledger, self.CARRIERS, self.IN_MONTH)[0]
        self.assertEqual((fedex["charges_cents"], fedex["refunds_cents"], fedex["net_cents"], fedex["lines"]),
                         (42824, 5000, 37824, 2))

    def test_a_refund_from_a_carrier_is_not_a_deposit(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "bank.csv").write_text(
                "bank_txn_id,account,posting_date,description,amount_cents\n"
                "b:1,0101,2026-09-20,OSM WORLDWIDE REFUND,1000\n"
                "b:2,0101,2026-09-13,GOODWILL BOOKS DES:PAYMENT ID:GWB-2026-08,313681\n", encoding="utf-8")
            credits = reconcile.bank_credits(Path(tmp), bc.load_mapping(), self.CARRIERS)
        self.assertEqual([(c["amount_cents"], c["source"]) for c in credits], [(313681, "goodwillbooks")])


if __name__ == "__main__":
    unittest.main()
