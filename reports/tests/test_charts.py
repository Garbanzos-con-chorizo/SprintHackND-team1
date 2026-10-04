"""The pies (the week on the portal, the period on a scorecard) and the KPI trend of the scorecards list."""
import json
import re

from reports import charts, hub, scorecard
from reports.schema import CSV_COLUMNS

EXAMPLES = scorecard.ROOT / "docs" / "contracts" / "examples"
# Friday and Saturday of ISO week 40; Amazon and eBay have no file on the Saturday.
DAYS = {
    "2026-10-02": [("ShopGoodwill", "ok", "1228.00"), ("Amazon", "ok", "310.50"), ("eBay", "ok", "702.25"),
                   ("Other", "not_configured", "")],
    "2026-10-03": [("ShopGoodwill", "ok", "2324.00"), ("Amazon", "missing", ""), ("eBay", "missing", ""),
                   ("Other", "not_configured", "")],
}


def test_a_pie_gives_each_part_its_amount_and_share_and_leaves_out_what_has_none():
    html = charts.pie([("ShopGoodwill", "#0054A4", 750.0), ("Amazon", "#eb6834", 250.0), ("eBay", "#1baf7a", 0)], "$1,000", "2 nights")
    assert html.count("<circle") == 2 and "eBay" not in html
    assert "<title>ShopGoodwill: $750.00 (75.0%)</title>" in html and "<title>Amazon: $250.00 (25.0%)</title>" in html
    assert "<b>$750</b><em>75%</em>" in html and "<b>$250</b><em>25%</em>" in html
    assert charts.pie([("eBay", "#1baf7a", 0)], "$0", "") == ""


def test_the_portal_shows_the_latest_weeks_revenue_by_marketplace(tmp_path):
    pulse = tmp_path / "pulse"
    pulse.mkdir()
    for day, rows in DAYS.items():
        lines = [",".join(CSV_COLUMNS)] + [f"{day},{name},{status},{revenue},,,,," for name, status, revenue in rows]
        (pulse / f"{day}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    html = hub.build(tmp_path).read_text(encoding="utf-8")
    assert "Week 40 by Marketplace" in html
    assert "<title>ShopGoodwill: $3,552.00 (77.8%)</title>" in html      # both nights
    assert "<title>Amazon: $310.50 (6.8%)</title>" in html               # only the night it reported
    assert "1 with a missing file count only what reported" in html


def test_a_scorecard_draws_its_revenue_by_marketplace_from_the_kpi_file(tmp_path):
    kf = json.loads((EXAMPLES / "kpi.sample.month.json").read_text(encoding="utf-8"))
    revenue = next(k for k in kf["kpis"] if k["id"] == "fin.revenue")
    by = revenue["inputs"]["by_marketplace"]
    assert sum(by.values()) == revenue["value"]
    html = scorecard.render(kf, tmp_path)
    assert "Revenue by Marketplace" in html
    assert f"<title>ShopGoodwill: ${by['shopgoodwill'] / 100:,.2f} (" in html
    revenue["inputs"].pop("by_marketplace")                               # a KPI file from before v0.7: no pie
    assert "Revenue by Marketplace" not in scorecard.render(kf, tmp_path)


def test_the_scorecards_list_has_a_trend_for_every_area_and_period_type(tmp_path):
    for name in ("kpi.sample.month.json", "kpi.sample.month.partial.json", "kpi.sample.week.json", "kpi.sample.day.json"):
        scorecard.build(EXAMPLES / name, tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    sets = re.findall(r'<div class="ex-set" data-kind="(\w+)" data-area="(\w+)"( hidden)?>', html)
    assert {kind for kind, _, _ in sets} == {"day", "week", "month"}
    assert {area for _, area, _ in sets} == {"financial", "productivity", "inventory", "sales", "category_customer"}
    assert len(sets) == 15 and sum(not hidden for _, _, hidden in sets) == 1     # one set shown; the buttons switch
    assert [kind for kind, area, hidden in sets if not hidden] == ["month"]      # the type with the most scorecards on file
    assert html.count('data-pick="area"') == 5 and html.count('data-pick="kind"') == 3
    months = html.split('<div class="ex-set" data-kind="month" data-area="financial"')[1].split('<div class="ex-set"')[0]
    assert "Total E-Commerce Revenue" in months and months.count('<svg class="line"') == 3
    assert 'href="month-2026-09.html"' in months and 'href="month-2026-10.html"' in months   # a dot opens its scorecard
