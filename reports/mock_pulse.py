"""Build pulse JSON (docs/contracts/pulse.md, schema_version 1) from a sample scenario's answer key.

Stand-in for `python -m recon.pulse` until the engine's per-source status (P-V4) lands, so the
renderer and the demo can run on the sample data now.

    python -m reports.mock_pulse --scenario day_refund [--out out/pulse]
    python -m reports.mock_pulse --scenario clean_month     # one file per September day
"""
import argparse
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample"
MARKETPLACES = ["shopgoodwill", "amazon", "ebay", "other"]
NUMBERS = ["gross_cents", "refunds_cents", "revenue_cents", "fees_cents", "orders", "customers"]
DEFINITIONS = {  # same wording as docs/contracts/examples/pulse.sample.json
    "revenue": "Sales minus refunds, before marketplace fees. Excludes shipping and tax.",
    "fees": "Marketplace fees are shown separately and are not subtracted from revenue.",
    "customers": "Unique buyers where the marketplace exposes a buyer id, otherwise orders. "
                 "The enterprise count is the sum of the marketplaces.",
    "day": "Order date, Eastern time.",
}


def marketplace(day, mk):
    """One marketplace block from an answer-key day; null numbers unless ok."""
    src = (day or {}).get(mk)
    if mk == "other":
        return {"status": "not_configured", **{n: None for n in NUMBERS}, "customer_basis": None}
    if src is None:
        return {"status": "unknown", **{n: None for n in NUMBERS}, "customer_basis": None}
    if src["status"] != "ok":
        return {"status": src["status"], **{n: None for n in NUMBERS}, "customer_basis": None}
    return {"status": "ok", "gross_cents": src["sales_cents"], "refunds_cents": src["refunds_cents"],
            "revenue_cents": src["revenue_cents"], "fees_cents": src["fees_cents"], "orders": src["orders"],
            "customers": src["customers"], "customer_basis": src["customer_basis"]}


def delta(cur, prev, prior_date, coverage_changed=False):
    d = {"prior_date": prior_date, "prior_revenue_cents": None, "prior_customers": None,
         "revenue_cents": None, "revenue_pct": None, "customers": None, "reason": None}
    if prev and prev["status"] == "ok":
        d["prior_revenue_cents"], d["prior_customers"] = prev["revenue_cents"], prev["customers"]
    if cur["status"] != "ok":
        d["reason"] = "current_not_ok"
    elif not prev or prev["status"] != "ok":
        d["reason"] = "prior_unavailable"
    elif coverage_changed:
        d["reason"] = "coverage_changed"
    else:
        d["revenue_cents"] = cur["revenue_cents"] - prev["revenue_cents"]
        d["customers"] = cur["customers"] - prev["customers"]
        if prev["revenue_cents"] > 0:
            d["revenue_pct"] = round(100 * d["revenue_cents"] / prev["revenue_cents"], 1)
        else:
            d["reason"] = "prior_zero"
    return d


def enterprise(markets):
    included = [m for m in MARKETPLACES if markets[m]["status"] == "ok"]
    ent = {n: sum(markets[m][n] for m in included) for n in NUMBERS}
    bases = {markets[m]["customer_basis"] for m in included}
    ent["customer_basis"] = None if not bases else bases.pop() if len(bases) == 1 else "mixed"
    ent["included"] = included
    ent["excluded"] = [{"marketplace": m, "status": markets[m]["status"]} for m in MARKETPLACES
                       if markets[m]["status"] in ("missing", "stale", "unknown")]
    ent["status"] = "ok" if included else "missing"  # internal, for delta(); removed below
    return ent


def count_duplicates(inbox):
    """Identical sale/refund lines across the inbox's CSVs (what dedupe would drop)."""
    seen, dups = set(), 0
    for f in sorted(inbox.glob("*.csv")):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if not any(t in line for t in ('"Order"', '"Refund"')):
                continue
            dups += line in seen
            seen.add(line)
    return dups


def build_day(key, scenario, bd):
    prior_date = (date.fromisoformat(bd) - timedelta(days=1)).isoformat()
    today, prior = key["days"][bd], key["days"].get(prior_date)
    markets = {m: marketplace(today, m) for m in MARKETPLACES}
    prev = {m: marketplace(prior, m) for m in MARKETPLACES} if prior else None
    for m in MARKETPLACES:
        markets[m]["delta"] = delta(markets[m], prev and prev[m], prior_date)
    ent = enterprise(markets)
    prev_ent = enterprise(prev) if prev else None
    changed = bool(prev_ent) and ent["included"] != prev_ent["included"]
    ent["delta"] = delta(ent, prev_ent, prior_date, coverage_changed=changed)
    del ent["status"]
    dups = count_duplicates(SAMPLES / scenario / "inbox")
    return {
        "schema_version": 1,
        "mock": f"built from data/sample/{scenario}/expected.json",
        "business_date": bd,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "currency": "USD",
        "marketplaces": markets,
        "enterprise": ent,
        "data_quality": {"warnings_total": dups, "by_kind": {"duplicate": dups} if dups else {}},
        "definitions": DEFINITIONS,
    }


def build(scenario):
    """One pulse for a day_* scenario, or one per day for clean_month."""
    key = json.loads((SAMPLES / scenario / "expected.json").read_text(encoding="utf-8"))
    days = [key["business_date"]] if key["business_date"] else sorted(key["days"])
    return [build_day(key, scenario, d) for d in days]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scenario", required=True, help="folder name under data/sample/")
    ap.add_argument("--out", default=str(ROOT / "out" / "pulse"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for pulse in build(args.scenario):
        path = out / f"{pulse['business_date']}.json"
        path.write_text(json.dumps(pulse, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    shutil.copyfile(path, out / "latest.json")


if __name__ == "__main__":
    main()
