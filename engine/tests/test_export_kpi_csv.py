"""V2.8: the KPI CSV renders the KPI file (docs/contracts/kpi.md) without computing anything."""
import csv
import json
import shutil
from pathlib import Path

import pytest

from engine.export import COLUMNS, write_kpi_csv
from engine.export.cli import main as export_main

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs" / "contracts" / "examples"


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def export(tmp_path, name):
    kpi = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    return kpi, read(write_kpi_csv(EXAMPLES / name, tmp_path))


@pytest.mark.parametrize("name", ["kpi.sample.month.json", "kpi.sample.month.partial.json",
                                  "kpi.sample.week.json", "kpi.sample.day.json"])
def test_every_kpi_and_every_ranking_row_is_in_the_csv(tmp_path, name):
    kpi, rows = export(tmp_path, name)
    with open(tmp_path / f"{kpi['period']['type']}-{kpi['period']['id']}.csv", encoding="utf-8") as f:
        assert f.readline().strip() == ",".join(COLUMNS)
    expected = sum(max(len(k["rows"] or []), 1) if k["kind"] == "ranking" else 1 for k in kpi["kpis"])
    assert len(rows) == expected
    assert {r["KPI id"] for r in rows} == {k["id"] for k in kpi["kpis"]}
    assert {r["Period"] for r in rows} == {kpi["period"]["id"]}
    for k in kpi["kpis"]:  # simulated numbers say so in every row, file-only ones don't
        flags = {r["Simulated"] for r in rows if r["KPI id"] == k["id"]}
        assert flags == ({kpi["internal_data"]["label"]} if k["simulated"] else {""}), k["id"]


def test_money_in_dollars_ratios_as_fractions_and_no_data_blank(tmp_path):
    kpi, rows = export(tmp_path, "kpi.sample.month.json")
    by_id = {r["KPI id"]: r for r in rows if not r["Rank"]}
    k = {x["id"]: x for x in kpi["kpis"]}
    revenue = by_id["fin.revenue"]
    assert float(revenue["Value"]) == k["fin.revenue"]["value"] / 100 and revenue["Unit"] == "USD"
    assert revenue["Display"] == f"${k['fin.revenue']['value'] / 100:,.2f}"
    margin = by_id["fin.net_margin"]
    assert float(margin["Value"]) == k["fin.net_margin"]["value"] and margin["Display"].endswith("%")
    rplh = by_id["prod.revenue_per_labor_hour"]
    assert rplh["Display"].endswith("per labor hour") and rplh["Per"] == "labor hour"
    for kid, x in k.items():
        if x["kind"] == "scalar" and x["value"] is None:  # no data is blank, never 0
            assert (by_id[kid]["Value"], by_id[kid]["Display"]) == ("", "no data"), kid


def test_ranking_rows_add_up_with_the_rest_to_the_total(tmp_path):
    kpi, rows = export(tmp_path, "kpi.sample.month.json")
    top = next(x for x in kpi["kpis"] if x["id"] == "cat.top_revenue")
    ranked = [r for r in rows if r["KPI id"] == "cat.top_revenue"]
    assert [int(r["Rank"]) for r in ranked] == list(range(1, len(top["rows"]) + 1))
    assert [r["Category"] for r in ranked] == [x["label"] for x in top["rows"]]
    revenue = next(x for x in kpi["kpis"] if x["id"] == "fin.revenue")["value"]
    assert round(sum(float(r["Value"]) for r in ranked) * 100) + top["inputs"]["rest_cents"] == revenue
    margin = [r for r in rows if r["KPI id"] == "cat.top_margin"]
    assert all(r["Category margin"] for r in margin)


def test_changes_against_the_prior_period_come_through(tmp_path):
    kpi, rows = export(tmp_path, "kpi.sample.month.partial.json")
    k = next(x for x in kpi["kpis"] if x["id"] == "fin.revenue")
    r = next(r for r in rows if r["KPI id"] == "fin.revenue")
    assert float(r["Change"]) == k["delta"]["value"] / 100
    assert float(r["Change %"]) == k["delta"]["pct"]
    assert r["Change note"] == (k["delta"]["reason"] or "")
    assert r["Complete"] == "FALSE"


def test_cli_latest_period_and_missing_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out" / "kpi").mkdir(parents=True)
    assert export_main(["kpi-csv", "--period", "month"]) == 1
    assert "run `python -m recon.kpi` first" in capsys.readouterr().err
    shutil.copy(EXAMPLES / "kpi.sample.month.json", tmp_path / "out" / "kpi" / "latest-month.json")
    assert export_main(["kpi-csv", "--period", "month", "--dest", "exports"]) == 0
    assert (tmp_path / "exports" / "month-2026-09.csv").exists()
    (tmp_path / "bad.json").write_text("{}", encoding="utf-8")
    assert export_main(["kpi-csv", "--kpi-file", "bad.json"]) == 1
