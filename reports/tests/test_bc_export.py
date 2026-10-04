"""Business Central export: balance check, refusal, reconciliation status and the file read-back."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reports import bc_export as bc


class BcExportTest(unittest.TestCase):
    def setUp(self):
        self.payload = bc._mock_payload()
        self.mapping = bc.load_mapping()

    def run_build(self, payload=None):
        return bc.build(payload or self.payload, self.mapping)

    def test_mock_close_balances_and_reconciles(self):
        journal, invoice, control, exceptions = self.run_build()
        self.assertEqual(bc.unbalanced(journal), {})
        self.assertEqual({r["Status"] for r in control}, {"RECONCILED"})
        self.assertEqual(exceptions, [])
        for line in invoice:
            self.assertEqual(line["Quantity"] * line["Unit Price"], line["Amount"])

    def test_written_files_pass_the_read_back_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(bc.main(["--out", tmp]), 0)
            paths = {k: Path(tmp) / "2026-09" / f"{k}_2026-09.csv" for k in ("general_journal", "ar_invoice")}
            problems, lines, docs = bc.verify_files(paths)
            self.assertEqual(problems, [])
            self.assertEqual((lines, docs), (30, 12))

    def test_read_back_catches_an_edited_amount(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.main(["--out", tmp])
            gj = Path(tmp) / "2026-09" / "general_journal_2026-09.csv"
            gj.write_text(gj.read_text(encoding="utf-8").replace("-20052.32", "-20052.23"), encoding="utf-8")
            problems, _, _ = bc.verify_files({"general_journal": gj, "ar_invoice": gj.with_name("ar_invoice_2026-09.csv")})
            self.assertTrue(any("ECOM-2609-EBAY" in p for p in problems))

    def test_unbalanced_journal_is_refused_and_nothing_written(self):
        journal, invoice, control, exceptions = self.run_build()
        journal[1]["Amount"] += 1  # one cent off
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(bc, "build", return_value=(journal, invoice, control, exceptions)):
            self.assertEqual(bc.main(["--out", tmp]), 1)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_missing_deposit_leaves_an_open_balance_but_still_balances(self):
        payload = copy.deepcopy(self.payload)
        last = [d for d in payload["deposits"] if d["source"] == "amazon"][-1]
        payload["deposits"].remove(last)
        journal, _, control, _ = self.run_build(payload)
        self.assertEqual(bc.unbalanced(journal), {})
        amazon = next(r for r in control if r["Source"] == "Amazon")
        self.assertEqual((amazon["Status"], amazon["Open Balance"]), ("OPEN", last["amount_cents"]))

    def test_unmapped_source_and_its_deposit_become_exceptions(self):
        payload = copy.deepcopy(self.payload)
        payload["sources"]["cashmonkey"] = {"sales_cents": 1000, "refunds_cents": 0, "shipping_cents": 0,
                                            "fees_cents": 0}
        payload["deposits"].append({"date": "2026-09-20", "source": "cashmonkey", "amount_cents": 1000})
        journal, invoice, control, exceptions = self.run_build(payload)
        self.assertEqual({e["kind"] for e in exceptions}, {"unmapped_source", "unmatched_deposit"})
        self.assertFalse(any("cashmonkey" in str(line).lower() for line in journal + invoice))

    def test_invoice_path_fees_post_against_the_customer(self):
        payload = copy.deepcopy(self.payload)
        payload["sources"]["shopgoodwill"]["fees_cents"] = 5000
        last = [d for d in payload["deposits"] if d["source"] == "shopgoodwill"][-1]
        last["amount_cents"] -= 5000  # the marketplace keeps its fee
        journal, _, control, _ = self.run_build(payload)
        self.assertEqual(bc.unbalanced(journal), {})
        self.assertIn("ECOM-2609-SGW-FEES", {line["Document No."] for line in journal})
        sgw = next(r for r in control if r["Source"] == "ShopGoodwill")
        self.assertEqual(sgw["Status"], "RECONCILED")


if __name__ == "__main__":
    unittest.main()
