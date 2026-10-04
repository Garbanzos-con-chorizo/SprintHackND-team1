"""The three list pages (Daily Reports, COO Scorecards, Month-end Close): one row per report, with a finder."""
import json
import re

from reports import hub, pulse, scorecard

EXAMPLES = scorecard.ROOT / "docs" / "contracts" / "examples"


def rows(html):
    return re.findall(r'<tr data-find="([^"]*)" data-tags="([^"]*)">', html)


def test_scorecards_are_listed_by_period_with_revenue_and_data_state(tmp_path):
    for name in ("kpi.sample.month.json", "kpi.sample.month.partial.json", "kpi.sample.week.json", "kpi.sample.day.json"):
        scorecard.build(EXAMPLES / name, tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "<h1>COO Scorecards</h1>" in html and "Synthetic sample data" in html
    found = rows(html)
    pages = [f for f in tmp_path.glob("*.html") if f.name != "index.html"]
    assert len(found) == len(pages)
    assert {tags for _, tags in found} <= {"month", "week", "day"}
    for page in pages:
        kf = json.loads(page.with_suffix(".json").read_text(encoding="utf-8"))
        assert f'<a href="{page.name}">{kf["period"]["label"]}</a>' in html
    assert 'type="search"' in html and html.count('class="chip"') >= 2


def test_daily_reports_show_each_night_and_name_what_is_missing(tmp_path):
    def night(day, missing):
        ok = {"status": "ok", "revenue_cents": 123400, "refunds_cents": 0, "fees_cents": 0, "orders": 10, "customers": 9}
        markets = {k: ({"status": "missing"} if k in missing else dict(ok)) for k in ("shopgoodwill", "amazon", "ebay")}
        count = 3 - len(missing)
        return {"business_date": day, "marketplaces": {**markets, "other": {"status": "not_configured"}},
                "enterprise": {"revenue_cents": 123400 * count, "refunds_cents": 0, "fees_cents": 0, "orders": 10 * count,
                               "customers": 9 * count, "excluded": list(missing), "delta": None}}

    pulse.render(night("2026-10-02", ()), tmp_path)
    pulse.render(night("2026-10-03", ("amazon", "ebay")), tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "<h1>Daily Reports</h1>" in html and "Synthetic sample data" in html
    assert [tags for _, tags in rows(html)] == ["gaps", "complete"]          # newest first
    assert '<span class="pill missing">No data: Amazon, eBay</span>' in html
    assert '<span class="pill ok">Complete</span>' in html
    assert '<td class="num">$3,702.00</td><td class="num">30</td>' in html   # the full night: three marketplaces
    assert '<td class="num">$1,234.00</td><td class="num">10</td>' in html   # the other: only what reported
    assert '<a href="2026-10-03.csv">CSV</a>' in html
    assert '<a href="2026-10-03.xlsx">Excel</a>' in html                     # the full day, one sheet per table
    found = dict((tags, find) for find, tags in rows(html))
    assert "10/03/2026" in found["gaps"] and "10/3/2026" in found["gaps"]    # searchable as MM/DD/YYYY
    assert "10/02/2026" in found["complete"] and "10/03/2026" not in found["complete"]


def test_the_close_list_reads_the_files_beside_the_page_and_says_not_posted(tmp_path):
    month = tmp_path / "close" / "2026-09"
    month.mkdir(parents=True)
    (tmp_path / "close" / "2026-09.html").write_text("<p>close</p>", encoding="utf-8")
    (month / "control_totals_2026-09.csv").write_text(
        "Source,Path,Status\neBay,Journal,OPEN\nAmazon,Journal,INCOMPLETE\n", encoding="utf-8")
    (month / "exceptions_2026-09.csv").write_text("Kind,Source\nin_transit,Amazon\nmissing_report,Amazon\n", encoding="utf-8")
    hub.close_index(tmp_path)
    html = (tmp_path / "close" / "index.html").read_text(encoding="utf-8")
    assert "<h1>Month-End Close</h1>" in html and "Not posted" in html
    assert '<span class="pill stale">eBay OPEN</span>' in html and '<span class="pill missing">Amazon INCOMPLETE</span>' in html
    assert '<a href="2026-09.html">September 2026</a>' in html
    assert rows(html) == [("september 2026 2026-09 ebay open amazon incomplete not posted needs amazon", "review")]
    assert "Needs 1 report" in html                          # what the month still needs, seen from the list
    assert '<td class="num">2</td>' in html                 # the exceptions, counted from the file
    assert "general_journal" not in html                    # a file that is not there gets no link
