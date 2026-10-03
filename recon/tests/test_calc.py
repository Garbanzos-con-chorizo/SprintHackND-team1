import json
import unittest
from pathlib import Path

from recon.pulse import calc, io

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = Path(__file__).parents[2] / "docs" / "contracts" / "examples"
SCENARIOS = ("clean_day", "refund_day", "missing_source", "duplicate_rows", "zero_revenue")
DAY = "2026-10-02"
NULLS = dict.fromkeys(calc.NUMBERS) | {"customer_basis": None}


def pulse_for(scenario, business_date=DAY, with_status=True):
    folder = FIXTURES / scenario
    rows, _ = io.load_transactions(folder / "transactions.csv")
    status = io.load_source_status(folder / "source_status.json") if with_status else None
    return calc.build_pulse(rows, status, io.load_warnings(folder / "warnings.json"), business_date)


def numbers(gross, refunds, fees, orders, customers, basis):
    return {
        "status": "ok",
        "gross_cents": gross,
        "refunds_cents": refunds,
        "revenue_cents": gross + refunds,
        "fees_cents": fees,
        "orders": orders,
        "customers": customers,
        "customer_basis": basis,
    }


class CleanDay(unittest.TestCase):
    def setUp(self):
        self.pulse = pulse_for("clean_day")

    def test_marketplaces(self):
        m = self.pulse["marketplaces"]
        self.assertEqual(list(m), ["shopgoodwill", "amazon", "ebay", "other"])
        self.assertEqual(m["shopgoodwill"], numbers(20900, 0, 0, 2, 2, "buyer"))
        self.assertEqual(m["amazon"], numbers(4798, 0, 720, 2, 2, "order"))
        self.assertEqual(m["ebay"], numbers(4449, 0, 576, 2, 2, "buyer"))
        self.assertEqual(m["other"], {"status": "not_configured", **NULLS})

    def test_enterprise(self):
        e = self.pulse["enterprise"]
        self.assertEqual(e["revenue_cents"], 30147)
        self.assertEqual((e["fees_cents"], e["orders"], e["customers"]), (1296, 6, 6))
        self.assertEqual(e["customer_basis"], "mixed")
        self.assertEqual(e["included"], ["shopgoodwill", "amazon", "ebay"])
        self.assertEqual(e["excluded"], [])

    def test_data_quality_and_definitions(self):
        self.assertEqual(self.pulse["data_quality"], {"warnings_total": 0, "by_kind": {}})
        self.assertEqual(set(self.pulse["definitions"]), {"revenue", "fees", "customers", "day"})


class Scenarios(unittest.TestCase):
    def test_refund_day(self):
        pulse = pulse_for("refund_day")
        # one refund of a same-day sale, one of a sale from the day before
        self.assertEqual(pulse["marketplaces"]["ebay"], numbers(4449, -4199, 576, 2, 2, "buyer"))
        self.assertEqual(pulse["enterprise"]["refunds_cents"], -4199)
        self.assertEqual(pulse["enterprise"]["revenue_cents"], 25948)

    def test_missing_and_stale_sources_are_null_and_left_out(self):
        pulse = pulse_for("missing_source")
        m, e = pulse["marketplaces"], pulse["enterprise"]
        self.assertEqual(m["ebay"], {"status": "missing", **NULLS})
        self.assertEqual(m["amazon"], {"status": "stale", **NULLS})
        self.assertEqual(e["revenue_cents"], 20900)
        self.assertEqual(e["included"], ["shopgoodwill"])
        self.assertEqual(
            e["excluded"],
            [{"marketplace": "amazon", "status": "stale"}, {"marketplace": "ebay", "status": "missing"}],
        )
        self.assertEqual(e["customer_basis"], "buyer")

    def test_duplicate_rows_do_not_double_count(self):
        pulse = pulse_for("duplicate_rows")
        self.assertEqual(pulse["marketplaces"]["ebay"], numbers(4449, 0, 576, 2, 2, "buyer"))
        self.assertEqual(pulse["enterprise"]["revenue_cents"], 30147)
        self.assertEqual(pulse["data_quality"], {"warnings_total": 2, "by_kind": {"duplicate": 2}})

    def test_zero_revenue_is_a_real_zero(self):
        ebay = pulse_for("zero_revenue")["marketplaces"]["ebay"]
        self.assertEqual(ebay, numbers(2599, -2599, 336, 1, 1, "buyer"))
        self.assertEqual(ebay["revenue_cents"], 0)

    def test_totals_equal_the_sum_of_the_rows_shown(self):
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                pulse = pulse_for(name)
                shown = [m for m in pulse["marketplaces"].values() if m["status"] == "ok"]
                for k in calc.NUMBERS:
                    self.assertEqual(pulse["enterprise"][k], sum(m[k] for m in shown))


class StatusWithoutAMatchingFile(unittest.TestCase):
    def test_status_file_for_another_day(self):
        m = pulse_for("missing_source", business_date="2026-10-01")["marketplaces"]
        self.assertEqual(m["amazon"], numbers(5200, 0, 780, 2, 2, "order"))
        self.assertEqual(m["shopgoodwill"]["status"], "unknown")
        self.assertEqual(m["ebay"]["status"], "unknown")
        self.assertEqual(m["other"]["status"], "not_configured")

    def test_no_status_file(self):
        pulse = pulse_for("missing_source", with_status=False)
        m = pulse["marketplaces"]
        self.assertEqual([m[k]["status"] for k in m], ["ok", "unknown", "unknown", "not_configured"])
        self.assertEqual(pulse["enterprise"]["revenue_cents"], 20900)

    def test_no_data_at_all(self):
        e = pulse_for("clean_day", business_date="2026-09-01", with_status=False)["enterprise"]
        self.assertEqual((e["revenue_cents"], e["included"], e["customer_basis"]), (0, [], None))
        self.assertEqual(len(e["excluded"]), 3)

    def test_absent_warnings_file(self):
        self.assertIsNone(calc.data_quality(None))


class MatchesThePublishedMock(unittest.TestCase):
    def test_contract_sample(self):
        rows, _ = io.load_transactions(EXAMPLES / "transactions.sample.csv")
        status = {"business_date": DAY, "sources": {s: {"status": "ok"} for s in ("shopgoodwill", "amazon", "ebay")}}
        pulse = calc.build_pulse(rows, status, [], DAY)
        mock = json.loads((EXAMPLES / "pulse.sample.json").read_text(encoding="utf-8"))
        for section in (pulse["marketplaces"], {"enterprise": pulse["enterprise"]}):
            for name, got in section.items():
                want = mock["marketplaces"][name] if name != "enterprise" else mock["enterprise"]
                self.assertEqual(got, {k: v for k, v in want.items() if k != "delta"}, name)
        self.assertEqual(pulse["definitions"], mock["definitions"])
        self.assertEqual(pulse["data_quality"], mock["data_quality"])


if __name__ == "__main__":
    unittest.main()
