"""The 15 KPIs against values worked out by hand: two days of a week, compared with the week before."""
import unittest
from datetime import date

from recon.kpi import calc, facts, periods
from recon.kpi.kpis import BY_ORDERS, PER_ORDER, median
from recon.kpi.store import InternalRow, PulseRow, Sale, WindowData

SG, AM, EB = "shopgoodwill", "amazon", "ebay"
W40 = periods.parse("week", "2026-W40")  # Monday Sep 28 to Sunday Oct 4
WIN = periods.Window(W40, date(2026, 9, 29))  # reported to date: Monday and Tuesday
MON, TUE = "2026-09-28", "2026-09-29"


def ok(day, marketplace, gross, refunds, fees, orders):
    return PulseRow(day, marketplace, "ok", gross, refunds, gross + refunds, fees, orders)


def gap(day, marketplace, status="missing"):
    return PulseRow(day, marketplace, status, None, None, None, None, None)


def internal(day, metric, value, dimension="total", source="mock"):
    return InternalRow(day, metric, dimension, value, source)


# This week, Monday and Tuesday: revenue 35000, fees 1985, 19 orders.
PULSE = [
    ok(MON, SG, 10000, 0, 0, 4), ok(MON, AM, 3000, -500, 450, 3), ok(MON, EB, 5000, 0, 650, 2),
    ok(TUE, SG, 12000, 0, 0, 5), ok(TUE, AM, 2000, 0, 300, 2), ok(TUE, EB, 4500, -1000, 585, 3),
]
# 12 buyers (ShopGoodwill b1..b8, eBay x1..x4), 2 of them with two orders; Amazon gives no buyer id.
SALES = [
    Sale(SG, "s1", "b1", None), Sale(SG, "s2", "b2", None), Sale(SG, "s3", "b3", None), Sale(SG, "s4", "b4", None),
    Sale(SG, "s5", "b1", None), Sale(SG, "s6", "b5", None), Sale(SG, "s7", "b6", None), Sale(SG, "s8", "b7", None),
    Sale(SG, "s9", "b8", None),
    Sale(AM, "a1", "", None), Sale(AM, "a2", "", None), Sale(AM, "a3", "", None), Sale(AM, "a4", "", None),
    Sale(AM, "a5", "", None),
    Sale(EB, "e1", "x1", None), Sale(EB, "e2", "x1", None), Sale(EB, "e3", "x2", None), Sale(EB, "e4", "x3", None),
    Sale(EB, "e5", "x4", None),
]
INTERNAL = [
    internal(MON, "labor_hours", 20.0), internal(TUE, "labor_hours", 15.0),
    internal(MON, "labor_cost_cents", 3000), internal(TUE, "labor_cost_cents", 2250),
    internal(MON, "employees", 4.0), internal(TUE, "employees", 6.0),
    internal(MON, "listings_created", 6, SG), internal(MON, "listings_created", 4, EB),
    internal(TUE, "listings_created", 7, SG), internal(TUE, "listings_created", 5, AM),
    internal(TUE, "listings_created", 3, EB),
    internal(MON, "donation_to_listing_days", 3, "2"), internal(MON, "donation_to_listing_days", 2, "5"),
    internal(TUE, "donation_to_listing_days", 5, "9"),
    internal(MON, "unlisted_backlog", 120), internal(TUE, "unlisted_backlog", 110),
    internal(MON, "active_listings_by_age", 50, "0-30"), internal(MON, "active_listings_by_age", 30, "31-60"),
    internal(MON, "active_listings_by_age", 10, "61-90"), internal(MON, "active_listings_by_age", 10, "91+"),
    internal(TUE, "active_listings_by_age", 60, "0-30"), internal(TUE, "active_listings_by_age", 25, "31-60"),
    internal(TUE, "active_listings_by_age", 10, "61-90"), internal(TUE, "active_listings_by_age", 5, "91+"),
    internal(MON, "shipping_net_cost_cents", 1000), internal(TUE, "shipping_net_cost_cents", 1500),
    internal(MON, "category_sales_cents", 6000, "A"), internal(MON, "category_sales_cents", 3000, "B"),
    internal(TUE, "category_sales_cents", 2000, "A"), internal(TUE, "category_sales_cents", 1000, "B"),
    internal(TUE, "category_sales_cents", 8000, "C"),
    internal(MON, "category_cogs_cents", 2000, "A"), internal(MON, "category_cogs_cents", 1000, "B"),
    internal(TUE, "category_cogs_cents", 1000, "B"), internal(TUE, "category_cogs_cents", 2000, "C"),
]
# The same two days of the week before: revenue 28000, 13 orders; only some internal data, no transactions.
PRIOR = WindowData(
    pulse=[
        ok("2026-09-21", SG, 9000, 0, 0, 3), ok("2026-09-21", AM, 2000, 0, 300, 2),
        ok("2026-09-21", EB, 3000, 0, 390, 1),
        ok("2026-09-22", SG, 8000, 0, 0, 3), ok("2026-09-22", AM, 2500, 0, 375, 2),
        ok("2026-09-22", EB, 3500, 0, 455, 2),
    ],
    sales=[],
    internal=[
        internal("2026-09-21", "labor_hours", 20.0), internal("2026-09-22", "labor_hours", 20.0),
        internal("2026-09-21", "employees", 4.0), internal("2026-09-22", "employees", 4.0),
        internal("2026-09-21", "listings_created", 10, SG), internal("2026-09-22", "listings_created", 10, SG),
    ],
)
# And of the week before that: revenue 20000.
BEFORE = WindowData(
    pulse=[ok(day, m, cents, 0, 0, 1)
           for day in ("2026-09-14", "2026-09-15") for m, cents in ((SG, 6000), (AM, 2000), (EB, 2000))],
    sales=[],
    internal=[],
)
NOTHING = WindowData([], [], [])
NO_DELTA = {"value": None, "pct": None, "reason": "no_prior_period"}


def build(pulse=PULSE, sales=SALES, rows=INTERNAL, prior=PRIOR, before=BEFORE, win=WIN):
    doc = calc.build(win, WindowData(list(pulse), list(sales), list(rows)), prior, before)
    return doc, {k["id"]: k for k in doc["kpis"]}


def without(rows, *metrics, day=None):
    return [r for r in rows if not (r.metric in metrics and day in (None, r.business_date))]


class Shape(unittest.TestCase):
    def setUp(self):
        self.doc, self.kpis = build()

    def test_fifteen_kpis_three_per_area_in_order(self):
        areas = [a["id"] for a in self.doc["areas"]]
        self.assertEqual(areas, ["financial", "productivity", "inventory", "sales", "category_customer"])
        self.assertEqual([k["area"] for k in self.doc["kpis"]], [a for a in areas for _ in range(3)])
        self.assertEqual(len(set(self.kpis)), 15)

    def test_every_kpi_has_every_key(self):
        keys = ["id", "area", "pillar", "name", "kind", "unit", "per", "value", "rows", "status", "reason", "note",
                "basis", "covers", "prior_value", "delta", "good_direction", "source", "simulated", "definition",
                "inputs"]
        for k in self.doc["kpis"]:
            self.assertEqual(list(k), keys, k["id"])

    def test_every_kpi_speaks_to_one_of_the_five_pillars(self):
        pillars = [p["id"] for p in self.doc["pillars"]]
        self.assertEqual(pillars, ["growth", "profitability", "productivity", "inventory", "engagement"])
        count = {p: sum(k["pillar"] == p for k in self.doc["kpis"]) for p in pillars}
        self.assertEqual(count,
                         {"growth": 4, "profitability": 2, "productivity": 4, "inventory": 4, "engagement": 1})
        self.assertEqual(self.kpis["sales.sell_through"]["pillar"], "inventory")  # slide 36: inventory velocity

    def test_period_and_comparison(self):
        self.assertEqual(self.doc["period"], {
            "type": "week", "id": "2026-W40", "label": "Week 40, 2026 (to date)", "start": MON, "end": "2026-10-04",
            "through": TUE, "days": 2, "complete": False})
        self.assertEqual(self.doc["prior_period"], {
            "id": "2026-W39", "label": "September 21 to 22, 2026", "start": "2026-09-21", "through": "2026-09-22",
            "days": 2, "available": True})

    def test_coverage(self):
        self.assertEqual(self.doc["coverage"], {
            "days_expected": 2, "days_complete": 2, "days_partial": 0, "days_missing": 0, "complete": True,
            "by_marketplace": {SG: 2, AM: 2, EB: 2}, "gaps": []})

    def test_other_is_not_an_expected_marketplace(self):
        # the store keeps a not_configured row for `other` every day: it is neither a gap nor revenue
        doc, kpis = build(pulse=PULSE + [gap(MON, "other", "not_configured"), gap(TUE, "other", "not_configured")])
        self.assertEqual((doc["coverage"]["complete"], doc["coverage"]["gaps"]), (True, []))
        self.assertEqual((kpis["fin.revenue"]["value"], kpis["fin.revenue"]["status"]), (35000, "ok"))

    def test_other_counts_on_the_days_it_has_data(self):
        doc, kpis = build(pulse=PULSE + [ok(MON, "other", 1000, 0, 0, 1)])
        self.assertEqual((kpis["fin.revenue"]["value"], kpis["fin.revenue"]["inputs"]["orders"]), (36000, 20))
        self.assertTrue(doc["coverage"]["complete"])

    def test_internal_data_is_labelled_simulated(self):
        self.assertEqual(self.doc["internal_data"],
                         {"source": "mock", "label": "Simulated internal data", "as_of": TUE})
        simulated = {k["id"] for k in self.doc["kpis"] if k["simulated"]}
        self.assertEqual(simulated, {k["id"] for k in self.doc["kpis"] if k["source"] != "files"})
        self.assertEqual(len(simulated), 11)


class HandComputed(unittest.TestCase):
    """Complete data for the window: every KPI is ok except the repeat buyer rate (Amazon has no buyer id)."""

    def setUp(self):
        self.doc, self.kpis = build()

    def check(self, kpi_id, value, inputs, prior_value=None, delta=NO_DELTA, **more):
        k = self.kpis[kpi_id]
        expected = {"value": value, "status": "ok", "reason": None, "inputs": inputs, "prior_value": prior_value,
                    "delta": delta, **more}
        self.assertEqual({key: k[key] for key in expected}, expected)

    def test_revenue(self):
        self.check("fin.revenue", 35000,
                   {"gross_cents": 36500, "refunds_cents": -1500, "fees_cents": 1985, "orders": 19},
                   prior_value=28000, delta={"value": 7000, "pct": 25.0, "reason": None})

    def test_revenue_growth(self):
        # (35000 - 28000) / 28000; the week before grew (28000 - 20000) / 20000
        self.check("fin.revenue_growth", 0.25, {"revenue_cents": 35000, "prior_revenue_cents": 28000},
                   prior_value=0.4, delta={"value": -0.15, "pct": None, "reason": None}, basis="prior_period")

    def test_net_margin(self):
        # cost of goods 3500 per category = 10500; 35000 - 1985 - 10500 - 2500 - 5250 = 14765
        self.check("fin.net_margin", 0.4219, {
            "revenue_cents": 35000, "fees_cents": 1985, "cogs_cents": 10500, "shipping_net_cost_cents": 2500,
            "labor_cost_cents": 5250, "net_profit_cents": 14765})

    def test_listings_created(self):
        self.check("prod.listings_created", 25, {"by_marketplace": {SG: 13, AM: 5, EB: 7}},
                   prior_value=20, delta={"value": 5, "pct": 25.0, "reason": None})

    def test_revenue_per_labor_hour(self):
        self.check("prod.revenue_per_labor_hour", 1000, {"revenue_cents": 35000, "labor_hours": 35.0},
                   prior_value=700, delta={"value": 300, "pct": 42.9, "reason": None}, per="labor hour")

    def test_listings_per_employee(self):
        # 25 listings / 5.0 employees on average (4 on Monday, 6 on Tuesday)
        self.check("prod.listings_per_employee", 5.0, {"listings_created": 25, "employees": 5.0},
                   prior_value=5.0, delta={"value": 0.0, "pct": 0.0, "reason": None})

    def test_days_from_donation_to_listing(self):
        # ages 2, 2, 2, 5, 5, 9, 9, 9, 9, 9: the middle two are 5 and 9
        self.check("inv.days_donation_to_listing", 7.0, {"items_listed": 10})

    def test_unlisted_backlog_is_the_last_snapshot(self):
        self.check("inv.unlisted_backlog", 110, {"as_of": TUE})

    def test_unsold_inventory(self):
        self.check("inv.unsold_pct", 0.4, {"as_of": TUE, "active_listings": 100, "active_over_threshold": 40,
                                           "threshold_days": 30})

    def test_average_selling_price_falls_back_to_per_order(self):
        # 35000 / 19 = 1842.1; the week before 28000 / 13 = 2153.8
        self.check("sales.asp", 1842, {"revenue_cents": 35000, "units": None, "orders": 19},
                   prior_value=2154, delta={"value": -312, "pct": -14.5, "reason": None},
                   basis="per_order", per="order", note=PER_ORDER[1], definition=PER_ORDER[0])

    def test_sell_through_falls_back_to_orders(self):
        self.check("sales.sell_through", 0.76, {"units_sold": None, "orders": 19, "units_listed": 25},
                   prior_value=0.65, delta={"value": 0.11, "pct": None, "reason": None},
                   basis="orders", note=BY_ORDERS[1])

    def test_sales_per_employee(self):
        self.check("sales.sales_per_employee", 7000, {"revenue_cents": 35000, "employees": 5.0},
                   prior_value=7000, delta={"value": 0, "pct": 0.0, "reason": None})

    def test_top_categories_by_revenue(self):
        # internal sales A 8000, B 4000, C 8000: revenue 35000 splits 40 / 20 / 40; a tie keeps the label order
        k = self.kpis["cat.top_revenue"]
        self.assertEqual(k["rows"], [
            {"rank": 1, "label": "A", "value": 14000, "share": 0.4, "ratio": None},
            {"rank": 2, "label": "C", "value": 14000, "share": 0.4, "ratio": None},
            {"rank": 3, "label": "B", "value": 7000, "share": 0.2, "ratio": None}])
        self.assertEqual(k["inputs"], {"revenue_cents": 35000, "internal_sales_cents": 20000, "categories": 3,
                                       "rest_cents": 0})
        self.assertEqual((k["value"], k["status"], k["basis"], k["prior_value"]), (None, "ok", "internal_split", None))
        self.assertEqual(k["delta"], {"value": None, "pct": None, "reason": "not_applicable"})

    def test_top_categories_by_margin(self):
        # cost ratios A 2000/8000, B 2000/4000, C 2000/8000: margins 10500, 3500, 10500 of 24500
        k = self.kpis["cat.top_margin"]
        self.assertEqual(k["rows"], [
            {"rank": 1, "label": "A", "value": 10500, "share": 0.4286, "ratio": 0.75},
            {"rank": 2, "label": "C", "value": 10500, "share": 0.4286, "ratio": 0.75},
            {"rank": 3, "label": "B", "value": 3500, "share": 0.1429, "ratio": 0.5}])
        self.assertEqual(k["inputs"], {"revenue_cents": 35000, "cogs_cents": 10500, "margin_cents": 24500,
                                       "categories": 3, "rest_cents": 0})

    def test_margin_ranking_and_net_margin_use_the_same_cost_of_goods(self):
        self.assertEqual(self.kpis["cat.top_margin"]["inputs"]["cogs_cents"],
                         self.kpis["fin.net_margin"]["inputs"]["cogs_cents"])

    def test_repeat_buyer_rate_covers_only_marketplaces_with_buyer_ids(self):
        k = self.kpis["cust.repeat_buyer_rate"]
        self.assertEqual((k["value"], k["status"], k["reason"]), (0.1667, "partial", "no_buyer_ids"))
        self.assertEqual(k["covers"], [SG, EB])
        self.assertEqual(k["note"], "ShopGoodwill and eBay only (74% of orders): Amazon gives no buyer id.")
        self.assertEqual(k["inputs"], {"buyers": 12, "repeat_buyers": 2, "orders_with_buyer_id": 14, "orders": 19})

    def test_everything_else_is_ok(self):
        not_ok = {k["id"]: k["status"] for k in self.doc["kpis"] if k["status"] != "ok"}
        self.assertEqual(not_ok, {"cust.repeat_buyer_rate": "partial"})


class MissingMarketplaceData(unittest.TestCase):
    def test_a_missing_day_makes_file_kpis_partial_and_leaves_internal_ones_ok(self):
        pulse = [r for r in PULSE if (r.business_date, r.marketplace) != (TUE, EB)] + [gap(TUE, EB)]
        doc, kpis = build(pulse=pulse)
        self.assertEqual(doc["coverage"]["gaps"], [{"date": TUE, "marketplace": EB, "status": "missing"}])
        self.assertEqual((doc["coverage"]["days_complete"], doc["coverage"]["days_partial"]), (1, 1))
        note = "eBay has no data on 2026-09-29, so this is partial."
        revenue = kpis["fin.revenue"]
        self.assertEqual((revenue["value"], revenue["status"], revenue["reason"], revenue["note"]),
                         (31500, "partial", "missing_days", note))
        # the change is still given, flagged
        self.assertEqual(revenue["delta"], {"value": 3500, "pct": 12.5, "reason": "partial_period"})
        partial = {k["id"] for k in doc["kpis"] if k["status"] == "partial"}
        self.assertEqual(partial, {k["id"] for k in doc["kpis"] if k["source"] != "internal"})
        # a fallback note follows the gap note; a second reason of the same status is named too
        self.assertEqual(kpis["sales.asp"]["note"], f"{note} {PER_ORDER[1]}")
        repeat = kpis["cust.repeat_buyer_rate"]
        self.assertEqual(repeat["reason"], "missing_days")
        self.assertTrue(repeat["note"].startswith(note) and repeat["note"].endswith("Amazon gives no buyer id."))

    def test_a_day_that_was_never_loaded_is_a_gap(self):
        doc, kpis = build(pulse=[r for r in PULSE if r.business_date == MON])
        self.assertEqual({g["status"] for g in doc["coverage"]["gaps"]}, {"not_loaded"})
        self.assertEqual((doc["coverage"]["days_complete"], doc["coverage"]["days_missing"]), (1, 1))
        self.assertEqual(kpis["fin.revenue"]["note"],
                         "ShopGoodwill has no data on 2026-09-29; Amazon has no data on 2026-09-29; "
                         "eBay has no data on 2026-09-29, so this is partial.")

    def test_no_marketplace_data_is_never_a_zero(self):
        doc, kpis = build(pulse=[gap(day, m) for day in (MON, TUE) for m in (SG, AM, EB)], sales=[])
        revenue = kpis["fin.revenue"]
        self.assertEqual((revenue["value"], revenue["status"], revenue["reason"]),
                         (None, "no_data", "no_marketplace_data"))
        self.assertEqual(revenue["inputs"],
                         {"gross_cents": None, "refunds_cents": None, "fees_cents": None, "orders": None})
        self.assertEqual(revenue["delta"], {"value": None, "pct": None, "reason": "current_no_data"})
        self.assertEqual(revenue["prior_value"], 28000)
        self.assertEqual(kpis["cat.top_revenue"]["rows"], [])
        # internal-only KPIs do not depend on the marketplace files
        self.assertEqual(kpis["prod.listings_created"]["status"], "ok")

    def test_a_real_zero_stays_a_zero(self):
        pulse = [ok(day, m, 0, 0, 0, 0) for day in (MON, TUE) for m in (SG, AM, EB)]
        _, kpis = build(pulse=pulse, sales=[])
        self.assertEqual((kpis["fin.revenue"]["value"], kpis["fin.revenue"]["status"]), (0, "ok"))
        self.assertEqual(kpis["prod.revenue_per_labor_hour"]["value"], 0)
        for kpi_id in ("fin.net_margin", "sales.asp", "cat.top_revenue", "cat.top_margin"):
            self.assertEqual((kpis[kpi_id]["status"], kpis[kpi_id]["reason"]), ("no_data", "zero_denominator"), kpi_id)


class Comparison(unittest.TestCase):
    def test_no_prior_period(self):
        doc, kpis = build(prior=NOTHING, before=NOTHING)
        self.assertFalse(doc["prior_period"]["available"])
        growth = kpis["fin.revenue_growth"]
        self.assertEqual((growth["value"], growth["status"], growth["reason"]), (None, "no_data", "no_prior_period"))
        self.assertEqual(growth["note"], "No data stored for September 21 to 22, 2026.")
        self.assertEqual(growth["inputs"], {"revenue_cents": 35000, "prior_revenue_cents": None})
        self.assertEqual(kpis["fin.revenue"]["delta"], NO_DELTA)
        self.assertIsNone(kpis["fin.revenue"]["prior_value"])

    def test_growth_has_no_prior_value_without_the_window_before(self):
        _, kpis = build(before=NOTHING)
        growth = kpis["fin.revenue_growth"]
        self.assertEqual((growth["value"], growth["prior_value"], growth["delta"]), (0.25, None, NO_DELTA))

    def test_a_partial_comparison_period_is_flagged(self):
        prior = WindowData([r for r in PRIOR.pulse if r.marketplace != AM], [], PRIOR.internal)
        _, kpis = build(prior=prior)
        growth = kpis["fin.revenue_growth"]
        self.assertEqual((growth["status"], growth["reason"]), ("partial", "missing_days"))
        self.assertEqual(growth["note"], "The comparison period (September 21 to 22, 2026) is partial.")
        self.assertEqual(kpis["fin.revenue"]["status"], "ok")
        self.assertEqual(kpis["fin.revenue"]["delta"], {"value": 11500, "pct": 48.9, "reason": "partial_period"})

    def test_zero_revenue_before_gives_no_growth(self):
        zeros = [ok(day, m, 0, 0, 0, 0) for day in ("2026-09-21", "2026-09-22") for m in (SG, AM, EB)]
        prior = WindowData(zeros, [], [])
        _, kpis = build(prior=prior)
        self.assertEqual((kpis["fin.revenue_growth"]["status"], kpis["fin.revenue_growth"]["reason"]),
                         ("no_data", "zero_denominator"))
        self.assertEqual(kpis["fin.revenue"]["delta"], {"value": 35000, "pct": None, "reason": None})

    def test_values_on_different_bases_are_not_compared(self):
        sales = [Sale(s.marketplace, s.order_id, s.customer_id, 2) for s in SALES]  # unit counts appear this week
        _, kpis = build(sales=sales)
        asp = kpis["sales.asp"]
        self.assertEqual((asp["basis"], asp["prior_value"], asp["delta"]), ("per_unit", None, NO_DELTA))


class Units(unittest.TestCase):
    def test_unit_counts_give_the_per_unit_definitions(self):
        sales = [Sale(s.marketplace, s.order_id, s.customer_id, 2) for s in SALES]  # 19 orders, 38 units
        _, kpis = build(sales=sales)
        asp, sold = kpis["sales.asp"], kpis["sales.sell_through"]
        self.assertEqual((asp["value"], asp["basis"], asp["per"], asp["note"]), (921, "per_unit", "unit", None))
        self.assertEqual(asp["inputs"], {"revenue_cents": 35000, "units": 38, "orders": 19})
        self.assertEqual(asp["definition"], "Revenue / units sold.")
        self.assertEqual((sold["value"], sold["basis"], sold["note"]), (1.52, "units", None))

    def test_one_sale_without_a_count_keeps_the_fallback(self):
        sales = [Sale(s.marketplace, s.order_id, s.customer_id, 2) for s in SALES[:-1]] + [SALES[-1]]
        _, kpis = build(sales=sales)
        self.assertEqual(kpis["sales.asp"]["basis"], "per_order")


class InternalData(unittest.TestCase):
    def test_no_internal_data_at_all(self):
        doc, kpis = build(rows=[])
        self.assertIsNone(doc["internal_data"])
        self.assertFalse(any(k["simulated"] for k in doc["kpis"]))
        no_data = {k["id"] for k in doc["kpis"] if k["status"] == "no_data"}
        self.assertEqual(no_data, {k["id"] for k in doc["kpis"] if k["source"] != "files"})
        self.assertEqual({kpis[i]["reason"] for i in no_data}, {"no_internal_data"})
        self.assertEqual(kpis["fin.net_margin"]["note"],
                         "The internal API returned no sales by category, cost of goods, shipping cost or labor cost "
                         "for this period.")
        self.assertEqual(kpis["inv.days_donation_to_listing"]["note"],
                         "The internal API returned no donation dates for this period.")
        self.assertEqual(kpis["fin.net_margin"]["inputs"]["revenue_cents"], 35000)
        self.assertEqual(kpis["fin.revenue"]["status"], "ok")

    def test_internal_data_for_only_some_days_is_partial(self):
        _, kpis = build(rows=without(INTERNAL, "labor_hours", day=TUE))
        k = kpis["prod.revenue_per_labor_hour"]
        self.assertEqual((k["value"], k["status"], k["reason"]), (1750, "partial", "missing_internal_days"))
        self.assertEqual(k["note"], "Internal data is incomplete: labor hours (1 of 2 days).")

    def test_an_old_snapshot_is_partial(self):
        _, kpis = build(rows=without(INTERNAL, "unlisted_backlog", "active_listings_by_age", day=TUE))
        backlog, unsold = kpis["inv.unlisted_backlog"], kpis["inv.unsold_pct"]
        self.assertEqual((backlog["value"], backlog["status"], backlog["reason"]),
                         (120, "partial", "missing_internal_days"))
        self.assertEqual(backlog["note"], "The latest backlog count snapshot is from 2026-09-28.")
        self.assertEqual((unsold["value"], unsold["inputs"]["as_of"]), (0.5, MON))

    def test_zero_denominators_are_no_data(self):
        rows = [r if r.metric != "labor_hours" else internal(r.business_date, "labor_hours", 0.0) for r in INTERNAL]
        _, kpis = build(rows=rows)
        k = kpis["prod.revenue_per_labor_hour"]
        self.assertEqual((k["value"], k["status"], k["reason"]), (None, "no_data", "zero_denominator"))
        self.assertEqual(k["inputs"], {"revenue_cents": 35000, "labor_hours": 0.0})

    def test_a_day_without_listed_items_has_no_donation_rows_and_that_is_fine(self):
        _, kpis = build(rows=without(INTERNAL, "donation_to_listing_days", day=TUE))
        k = kpis["inv.days_donation_to_listing"]
        self.assertEqual((k["value"], k["status"], k["inputs"]), (2.0, "ok", {"items_listed": 5}))  # ages 2, 2, 2, 5, 5

    def test_category_sales_that_are_all_zero_cannot_split_revenue(self):
        rows = [r if r.metric != "category_sales_cents" else internal(r.business_date, r.metric, 0, r.dimension)
                for r in INTERNAL]
        _, kpis = build(rows=rows)
        for kpi_id in ("fin.net_margin", "cat.top_revenue", "cat.top_margin"):
            k = kpis[kpi_id]
            self.assertEqual((k["status"], k["reason"], k["note"]),
                             ("no_data", "zero_denominator", "The internal sales by category are all zero."), kpi_id)

    def test_donation_ages_must_be_whole_days(self):
        rows = without(INTERNAL, "donation_to_listing_days") + [internal(MON, "donation_to_listing_days", 4, "30+"),
                                                                 internal(TUE, "donation_to_listing_days", 4, "3")]
        _, kpis = build(rows=rows)
        k = kpis["inv.days_donation_to_listing"]
        self.assertEqual((k["value"], k["status"], k["reason"]), (None, "no_data", "no_internal_data"))

    def test_a_category_without_cost_of_goods_counts_as_zero_and_is_flagged(self):
        _, kpis = build(rows=[r for r in INTERNAL if not (r.metric == "category_cogs_cents" and r.dimension == "C")])
        margin = kpis["cat.top_margin"]
        self.assertEqual((margin["status"], margin["reason"]), ("partial", "missing_internal_days"))
        self.assertEqual(margin["note"], "No cost of goods for C; counted as zero.")
        self.assertEqual(margin["rows"][0], {"rank": 1, "label": "C", "value": 14000, "share": 0.5, "ratio": 1.0})
        self.assertEqual(kpis["fin.net_margin"]["status"], "partial")

    def test_real_internal_data_is_not_marked_simulated(self):
        doc, _ = build(rows=[InternalRow(r.business_date, r.metric, r.dimension, r.value, "api") for r in INTERNAL])
        self.assertEqual(doc["internal_data"], {"source": "api", "label": "Goodwill internal data", "as_of": TUE})
        self.assertFalse(any(k["simulated"] for k in doc["kpis"]))

    def test_one_mock_row_keeps_everything_simulated(self):
        real = [InternalRow(r.business_date, r.metric, r.dimension, r.value, "api") for r in INTERNAL[1:]]
        rows = real + INTERNAL[:1]
        doc, _ = build(rows=rows)
        self.assertEqual(doc["internal_data"]["source"], "mock")

    def test_a_total_dimension_wins_over_the_sum_of_the_others(self):
        rows = INTERNAL + [internal(MON, "labor_hours", 99.0, "photography")]
        _, kpis = build(rows=rows)
        self.assertEqual(kpis["prod.revenue_per_labor_hour"]["inputs"]["labor_hours"], 35.0)


class Buyers(unittest.TestCase):
    def test_a_day_is_too_short(self):
        day = periods.parse("day", MON)
        _, kpis = build(win=periods.Window(day, day.end))
        k = kpis["cust.repeat_buyer_rate"]
        self.assertEqual((k["value"], k["status"], k["reason"]), (None, "no_data", "period_too_short"))

    def test_no_transactions_stored(self):
        _, kpis = build(sales=[])
        k = kpis["cust.repeat_buyer_rate"]
        self.assertEqual((k["value"], k["status"], k["reason"]), (None, "no_data", "no_buyer_ids"))
        self.assertEqual(k["note"], "No transactions are stored for this period.")

    def test_no_marketplace_gives_a_buyer_id(self):
        _, kpis = build(sales=[Sale(s.marketplace, s.order_id, "", None) for s in SALES])
        k = kpis["cust.repeat_buyer_rate"]
        self.assertEqual((k["status"], k["reason"], k["note"]),
                         ("no_data", "no_buyer_ids", "No marketplace gives a buyer id."))

    def test_every_order_with_a_buyer_id_is_ok(self):
        _, kpis = build(sales=[s for s in SALES if s.marketplace != AM])
        k = kpis["cust.repeat_buyer_rate"]
        self.assertEqual((k["value"], k["status"], k["covers"], k["note"]), (0.1667, "ok", None, None))

    def test_the_same_id_on_two_marketplaces_is_two_buyers(self):
        sales = [Sale(SG, "s1", "kim", None), Sale(EB, "e1", "kim", None), Sale(EB, "e2", "kim", None)]
        stats = facts.buyer_stats(sales)
        self.assertEqual((stats["buyers"], stats["repeat_buyers"]), (2, 1))


class Rankings(unittest.TestCase):
    def test_only_the_top_ten_are_listed_and_the_rest_is_kept(self):
        names = [f"cat{i:02d}" for i in range(12)]
        rows = without(INTERNAL, "category_sales_cents", "category_cogs_cents")
        for day in (MON, TUE):
            rows += [internal(day, "category_sales_cents", 100 * (i + 1), name) for i, name in enumerate(names)]
            rows += [internal(day, "category_cogs_cents", 10 * (i + 1), name) for i, name in enumerate(names)]
        _, kpis = build(rows=rows)
        top = kpis["cat.top_revenue"]
        self.assertEqual(len(top["rows"]), 10)
        self.assertEqual([r["label"] for r in top["rows"]][:2], ["cat11", "cat10"])
        self.assertEqual([r["rank"] for r in top["rows"]], list(range(1, 11)))
        self.assertEqual(top["inputs"]["categories"], 12)
        self.assertEqual(sum(r["value"] for r in top["rows"]) + top["inputs"]["rest_cents"], 35000)
        margin = kpis["cat.top_margin"]
        self.assertEqual(sum(r["value"] for r in margin["rows"]) + margin["inputs"]["rest_cents"],
                         margin["inputs"]["margin_cents"])

    def test_the_split_adds_up_to_the_cent(self):
        self.assertEqual(facts.allocate(100, [1, 1, 1]), [34, 33, 33])
        self.assertEqual(sum(facts.allocate(7075396, [0.17, 0.15, 0.13, 0.55])), 7075396)

    def test_median_of_a_histogram(self):
        self.assertEqual(median([(3, 1), (5, 1), (9, 1)]), 5)
        self.assertEqual(median([(3, 2), (9, 2)]), 6)
        self.assertEqual(median([(4, 7)]), 4)


if __name__ == "__main__":
    unittest.main()
