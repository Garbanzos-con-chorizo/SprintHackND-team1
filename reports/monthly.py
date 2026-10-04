"""Month rollup, and the month's COO scorecard from Dani's KPI file (phase 2, O2.1 / O2.5).

Reads out/pulse/<YYYY-MM>-DD.json and writes:
  reports/scorecard/month-<YYYY-MM>.html     the 15 KPIs, rendered from out/kpi/month-<YYYY-MM>.json
                                            (python -m recon.kpi) by reports.scorecard; no arithmetic here
  reports/monthly/<YYYY-MM>-kpis.csv        those KPIs, with their source (files or simulated)
  reports/monthly/<YYYY-MM>.csv   one row per day and marketplace, dollars, for Excel / Power BI
  reports/monthly/<YYYY-MM>.json  daily series plus month totals, for reports/monthly/index.html
  reports/monthly/months.json     list of months available, so the page can find them

    python -m reports.monthly --month 2026-09 [--src out/pulse] [--dest reports/monthly]
"""
import argparse
import calendar
import json
import re
from datetime import date, datetime
from pathlib import Path

from reports import hub, scorecard
from reports.schema import MARKETPLACES, day_record, write_csv

ROOT = Path(__file__).resolve().parent.parent
SUMMABLE = ["revenue_cents", "refunds_cents", "fees_cents", "orders"]  # customers repeat across days


def load_pulses(src, month):
    pulses = []
    for f in sorted(Path(src).glob(f"{month}-*.json")):
        if re.fullmatch(rf"{month}-\d{{2}}", f.stem):
            pulses.append(json.loads(f.read_text(encoding="utf-8")))
    return pulses


def aggregate(month, pulses):
    year, mon = map(int, month.split("-"))
    all_dates = [date(year, mon, d).isoformat() for d in range(1, calendar.monthrange(year, mon)[1] + 1)]
    days = [day_record(p) for p in pulses]
    have = {d["date"] for d in days}

    totals = {}
    for mk in MARKETPLACES:
        ok_days = [d["marketplaces"][mk] for d in days if d["marketplaces"][mk]["status"] == "ok"]
        totals[mk] = {"days_with_data": len(ok_days),
                      **{k: sum(r[k] for r in ok_days) if ok_days else None for k in SUMMABLE}}
    totals["enterprise"] = {"days_with_data": len(days),
                            "days_complete": sum(d["enterprise"]["complete"] for d in days),
                            **{k: sum(d["enterprise"][k] for d in days) if days else None for k in SUMMABLE}}
    return {
        "month": month,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "currency": "USD cents",
        "days_expected": len(all_dates),
        "days_missing": [d for d in all_dates if d not in have],
        "notes": ["Month totals add only days and marketplaces with data.",
                  "Customers are not totalled: a repeat buyer would be counted once per day."],
        "totals": totals,
        "days": days,
    }


def write_manifest(dest):
    months = sorted(f.stem for f in dest.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}", f.stem))
    (dest / "months.json").write_text(json.dumps({"months": months}, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--src", default=str(ROOT / "out" / "pulse"), help="folder with daily pulse JSON")
    ap.add_argument("--dest", default=str(ROOT / "reports" / "monthly"))
    args = ap.parse_args(argv)
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", args.month):
        raise SystemExit("--month must look like 2026-09")
    pulses = load_pulses(args.src, args.month)
    if not pulses:
        raise SystemExit(f"no pulse files for {args.month} in {args.src}")
    agg = aggregate(args.month, pulses)
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    write_csv(dest / f"{args.month}.csv", agg["days"])
    (dest / f"{args.month}.json").write_text(json.dumps(agg, indent=2) + "\n", encoding="utf-8")
    write_manifest(dest)
    kpi_file = ROOT / "out" / "kpi" / f"month-{args.month}.json"
    if kpi_file.exists():
        print(f"wrote {scorecard.build(kpi_file)}")
    else:
        print(f"no KPI file for {args.month}: run python -m recon.kpi --month {args.month}, then this again")
    print(f"wrote {hub.build(dest.parent)}")


if __name__ == "__main__":
    main()
