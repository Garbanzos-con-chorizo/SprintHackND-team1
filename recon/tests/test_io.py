import tempfile
import unittest
from pathlib import Path

from recon.pulse import io

FIXTURES = Path(__file__).parent / "fixtures"
SCENARIOS = ("clean_day", "refund_day", "missing_source", "duplicate_rows", "zero_revenue")
STATUSES = ("ok", "missing", "stale")


class FixturesFollowContract(unittest.TestCase):
    def test_every_scenario_loads(self):
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                folder = FIXTURES / name
                rows, _ = io.load_transactions(folder / "transactions.csv")
                self.assertTrue(rows)
                for r in rows:
                    self.assertEqual(r.txn_id, f"{r.source}:{r.order_id}:{r.type}")
                    self.assertEqual(r.customer_basis, "buyer" if r.customer_id else "order")
                    self.assertTrue(r.gross_cents > 0 if r.type == "sale" else r.gross_cents < 0)
                    self.assertGreaterEqual(r.fee_cents, 0)

                status = io.load_source_status(folder / "source_status.json")
                self.assertEqual(status["business_date"], "2026-10-02")
                for source, s in status["sources"].items():
                    self.assertIn(s["status"], STATUSES)
                    has_rows = any(r.source == source and r.business_date == "2026-10-02" for r in rows)
                    self.assertEqual(has_rows, s["status"] == "ok")

                self.assertIsInstance(io.load_warnings(folder / "warnings.json"), list)


class Loaders(unittest.TestCase):
    def test_repeated_txn_id_is_dropped(self):
        rows, dropped = io.load_transactions(FIXTURES / "duplicate_rows" / "transactions.csv")
        self.assertEqual(dropped, 1)
        self.assertEqual(len({r.txn_id for r in rows}), len(rows))

    def test_absent_optional_files_are_none(self):
        self.assertIsNone(io.load_source_status(FIXTURES / "nope.json"))
        self.assertIsNone(io.load_warnings(FIXTURES / "nope.json"))

    def test_contract_sample_loads(self):
        sample = Path(__file__).parents[2] / "docs" / "contracts" / "examples" / "transactions.sample.csv"
        rows, dropped = io.load_transactions(sample)
        self.assertEqual((len(rows), dropped), (7, 0))

    def test_bad_row_names_the_line(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "transactions.csv"
            good = (FIXTURES / "clean_day" / "transactions.csv").read_text().splitlines()
            bad.write_text("\n".join(good[:2] + [good[2].replace("2600", "26.00")]) + "\n")
            with self.assertRaisesRegex(ValueError, "line 3"):
                io.load_transactions(bad)


if __name__ == "__main__":
    unittest.main()
