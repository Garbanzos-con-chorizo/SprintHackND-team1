import json
import unittest
from pathlib import Path

from recon.pulse import calc, io

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = Path(__file__).parents[2] / "docs" / "contracts" / "examples"
SCENARIOS = ("clean_day", "refund_day", "missing_source", "duplicate_rows", "zero_revenue")
DAY = "2026-10-02"
NULLS = dict.fromkeys(calc.NUMBERS) | {"customer_basis": None}


def pulse_for(scenario, business_date=DAY, with_status=True, deltas=False, prior_pulse=None):
    folder = FIXTURES / scenario
    rows, _ = io.load_transactions(folder / "transactions.csv")
    status = io.load_source_status(folder / "source_status.json") if with_status else None
    warnings = io.load_warnings(folder / "warnings.json")
    pulse = calc.build_pulse(rows, status, warnings, business_date, prior_pulse=prior_pulse)
    if not deltas:
        for section in (*pulse["marketplaces"].values(), pulse["enterprise"]):
            del section["delta"]
    return pulse


def delta(prior_revenue, prior_customers, revenue, pct, customers, reason=None):
    return {
        "prior_date": "2026-10-01",
        "prior_revenue_cents": prior_revenue,
        "prior_customers": prior_customers,
        "revenue_cents": revenue,
        "revenue_pct": pct,
        "customers": customers,
        "reason": reason,
    }


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


class Deltas(unittest.TestCase):
    def test_clean_day_against_prior_day_rows(self):
        pulse = pulse_for("clean_day", deltas=True)
        m = pulse["marketplaces"]
        self.assertEqual(m["shopgoodwill"]["delta"], delta(19000, 1, 1900, 10.0, 1))
        self.assertEqual(m["amazon"]["delta"], delta(5200, 2, -402, -7.7, 0))
        self.assertEqual(m["ebay"]["delta"], delta(1600, 1, 2849, 178.1, 1))
        self.assertEqual(m["other"]["delta"], delta(None, None, None, None, None, "current_not_ok"))
        self.assertEqual(pulse["enterprise"]["delta"], delta(25800, 4, 4347, 16.8, 2))

    def test_no_prior_day(self):
        pulse = pulse_for("zero_revenue", deltas=True)
        unavailable = delta(None, None, None, None, None, "prior_unavailable")
        self.assertEqual(pulse["marketplaces"]["ebay"]["delta"], unavailable)
        self.assertEqual(pulse["enterprise"]["delta"], unavailable)

    def test_missing_today_keeps_the_prior_figure(self):
        pulse = pulse_for("missing_source", deltas=True)
        m = pulse["marketplaces"]
        self.assertEqual(m["amazon"]["delta"], delta(5200, 2, None, None, None, "current_not_ok"))
        self.assertEqual(m["shopgoodwill"]["delta"], delta(None, None, None, None, None, "prior_unavailable"))
        # today only ShopGoodwill reports, the day before only Amazon
        self.assertEqual(pulse["enterprise"]["delta"], delta(5200, 2, None, None, None, "coverage_changed"))

    def test_prior_zero_gives_amounts_but_no_percent(self):
        prior = pulse_for("zero_revenue")
        prior["business_date"] = "2026-10-01"
        pulse = pulse_for("clean_day", deltas=True, prior_pulse=prior)
        self.assertEqual(pulse["marketplaces"]["ebay"]["delta"], delta(0, 1, 4449, None, 1, "prior_zero"))
        self.assertEqual(pulse["marketplaces"]["amazon"]["delta"], delta(4798, 2, 0, 0.0, 0))

    def test_prior_pulse_for_the_wrong_day_is_ignored(self):
        wrong_day = pulse_for("zero_revenue")  # dated 2026-10-02, not the prior day
        pulse = pulse_for("clean_day", deltas=True, prior_pulse=wrong_day)
        self.assertEqual(pulse["marketplaces"]["ebay"]["delta"], delta(1600, 1, 2849, 178.1, 1))


class MatchesThePublishedMocks(unittest.TestCase):
    """The calculator reproduces docs/contracts/examples/pulse.sample*.json in full."""

    PRIOR = {
        "business_date": "2026-10-01",
        "marketplaces": {
            "shopgoodwill": {"status": "ok", "revenue_cents": 19000, "customers": 2},
            "amazon": {"status": "ok", "revenue_cents": 5200, "customers": 3},
            "ebay": {"status": "ok", "revenue_cents": 1600, "customers": 1},
            "other": {"status": "not_configured", "revenue_cents": None, "customers": None},
        },
        "enterprise": {"revenue_cents": 25800, "customers": 6, "included": ["shopgoodwill", "amazon", "ebay"]},
    }

    def check(self, mock_name, ebay_status, warnings):
        rows, _ = io.load_transactions(EXAMPLES / "transactions.sample.csv")
        sources = {"shopgoodwill": {"status": "ok"}, "amazon": {"status": "ok"}, "ebay": {"status": ebay_status}}
        status = {"business_date": DAY, "sources": sources}
        mock = json.loads((EXAMPLES / mock_name).read_text(encoding="utf-8"))
        pulse = calc.build_pulse(rows, status, warnings, DAY, mock["generated_at"], self.PRIOR)
        self.assertEqual(pulse, mock)
        self.assertEqual(list(pulse["marketplaces"]), list(mock["marketplaces"]))

    def test_clean_sample(self):
        self.check("pulse.sample.json", "ok", [])

    def test_missing_sample(self):
        warnings = [{"kind": "duplicate"}, {"kind": "duplicate"}, {"kind": "bad_date"}]
        self.check("pulse.sample.missing.json", "missing", warnings)


if __name__ == "__main__":
    unittest.main()
