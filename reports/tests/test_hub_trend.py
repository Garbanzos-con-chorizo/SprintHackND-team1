"""The portal: the data label every page carries, and the revenue-by-night chart built from the pulse CSVs."""
from reports import hub
from reports.schema import CSV_COLUMNS

DAYS = {
    "2026-10-02": [("ShopGoodwill", "ok", "1228.00"), ("Amazon", "ok", "310.50"), ("eBay", "ok", "702.25"),
                   ("Other", "not_configured", "")],
    "2026-10-03": [("ShopGoodwill", "ok", "2324.00"), ("Amazon", "missing", ""), ("eBay", "missing", ""),
                   ("Other", "not_configured", "")],
}


def portal(tmp_path, days=DAYS):
    pulse = tmp_path / "pulse"
    pulse.mkdir()
    for day, rows in days.items():
        lines = [",".join(CSV_COLUMNS)] + [f"{day},{name},{status},{revenue},,,,," for name, status, revenue in rows]
        (pulse / f"{day}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hub.build(tmp_path).read_text(encoding="utf-8")


def test_the_portal_says_the_data_is_synthetic_and_nothing_is_posted(tmp_path):
    html = portal(tmp_path)
    assert html.count("Synthetic sample data") >= 3          # top bar, the note under the cards, the footer
    assert "no real Goodwill file has been read" in html and "nothing is posted" in html
    assert (tmp_path / "close" / "index.html").exists()      # where the top bar's "Month-end close" lands


def test_the_chart_draws_what_reported_and_names_what_did_not(tmp_path):
    html = portal(tmp_path)
    assert html.count('<a class="col"') == 2
    assert html.count('<i class="seg"') == 4                 # three marketplaces on the 2nd, one on the 3rd
    assert "Oct 2 · eBay: $702.25" in html
    assert '<span class="gap">No data: Amazon, eBay</span>' in html
    assert "Sat, Oct 3: $2,324.00 (no data: Amazon, eBay)" in html
    assert "Amazon: $0.00" not in html                       # no data is never drawn as zero
    assert "Other" not in html.split('class="legend"')[1].split("</div>")[0]


def test_no_chart_from_a_single_night(tmp_path):
    html = portal(tmp_path, {"2026-10-03": DAYS["2026-10-03"]})
    assert '<a class="col"' not in html and '<div class="card trend">' not in html
