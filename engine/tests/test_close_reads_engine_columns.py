"""The month-end close takes shipping and handling from the engine's columns, never from an answer key."""
import csv
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MESSY = ROOT / "data" / "sample" / "messy_month"

try:  # the report code needs Python 3.12+
    from reports import bc_export, reconcile
except (ImportError, SyntaxError):  # pragma: no cover
    reconcile = None

pytestmark = [
    pytest.mark.skipif(reconcile is None, reason="reports/ needs Python 3.12+"),
    pytest.mark.skipif(not MESSY.exists(), reason="sample data not present"),
]


@pytest.fixture(scope="module")
def payload_without_a_key(tmp_path_factory):
    """Build the close from a copy of the inbox that has no expected.json next to it."""
    base = tmp_path_factory.mktemp("nokey")
    shutil.copytree(MESSY / "inbox", base / "inbox")
    assert not (base / "expected.json").exists()
    return reconcile.build(base / "inbox", "2026-09", bc_export.load_mapping(), base / "engine"), base


def test_no_stopgap_and_no_answer_key_needed(payload_without_a_key):
    payload, _ = payload_without_a_key
    assert payload["stopgaps"] == []
    assert set(payload["sources"]) == {"shopgoodwill", "ebay", "amazon"}


def test_shipping_and_handling_are_the_sums_of_the_engines_rows(payload_without_a_key):
    payload, base = payload_without_a_key
    totals = {}
    with open(base / "engine" / "transactions.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if "2026-09-01" <= r["business_date"] <= "2026-09-30":
                t = totals.setdefault(r["marketplace"], [0, 0])
                t[0] += int(r["shipping_cents"])
                t[1] += int(r["handling_cents"])
    for marketplace, (shipping, handling) in totals.items():
        if marketplace in payload["sources"]:
            assert (payload["sources"][marketplace]["shipping_cents"],
                    payload["sources"][marketplace]["handling_cents"]) == (shipping, handling)


def test_and_they_equal_the_independent_answer_key(payload_without_a_key):
    """The key is only used here, to check the result; the close itself never reads it."""
    payload, _ = payload_without_a_key
    key = json.loads((MESSY / "expected.json").read_text(encoding="utf-8"))["close"]["marketplace_totals_from_files"]
    for marketplace in ("shopgoodwill", "ebay", "amazon"):
        got = payload["sources"][marketplace]
        assert (got["shipping_cents"], got["handling_cents"]) == (
            key[marketplace]["shipping_cents"], key[marketplace]["handling_cents"]), marketplace
