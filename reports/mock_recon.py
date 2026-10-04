"""Close payload from a sample month's answer key: stand-in for reconciliation (D2-D5).

Reads data/sample/<scenario>/expected.json ("close" section) and writes the payload that
`reports.bc_export` takes (docs/contracts/close-payload.md): month totals per source from the
files, bank deposits matched to their source, and the exceptions with what each one does to the
close. Real reconciliation builds the same payload from the bank file and the payout rows.

    python -m reports.mock_recon --scenario messy_month [--out out/close]
    python -m reports.bc_export --payload out/close/2026-09/close_payload_2026-09.json
"""
import argparse
import calendar
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample"
PAYOUT_SOURCE = {"EBAY": "ebay", "AMZN": "amazon", "SGW": "shopgoodwill"}
LABEL = {"ebay": "eBay", "amazon": "Amazon", "shopgoodwill": "ShopGoodwill"}


def money(cents):
    return f"{'-' if cents < 0 else ''}${abs(cents) / 100:,.2f}"


def build(key):
    close = key["close"]
    month = close["month"]
    last = date(int(month[:4]), int(month[5:]), calendar.monthrange(int(month[:4]), int(month[5:]))[1])
    totals = close["marketplace_totals_from_files"]
    sources = {src: {"sales_cents": t["sales_cents"], "refunds_cents": -t["refunds_cents"],
                     "shipping_cents": t["shipping_cents"], "handling_cents": t["handling_cents"],
                     "fees_cents": t["fees_cents"]} for src, t in totals.items()}

    deposits, exceptions = [], []
    for d in close["bank_deposits"]:
        if d["matches"]:
            deposits.append({"date": d["date"], "source": PAYOUT_SOURCE[d["matches"][0].split("-")[0]],
                             "amount_cents": d["amount_cents"],
                             "reference": f"{d['description']} ({', '.join(d['matches'])})"})
        else:
            exceptions.append({"kind": "unmatched_deposit", "source": "", "amount_cents": d["amount_cents"],
                               "effect": "not_posted",
                               "detail": f"{d['date']} {d['description']}: no payout matches it; held out of the "
                                         f"journal until someone identifies it"})

    for p in close["payouts"]:
        src, label = p["source"], LABEL[p["source"]]
        window = p["activity_from"] if p["activity_from"] == p["activity_to"] else f"{p['activity_from']} to {p['activity_to']}"
        if p["status"] == "in_transit":
            paid_in_month = date.fromisoformat(p["paid_date"]) <= last
            exceptions.append({
                "kind": "in_transit" if paid_in_month else "payout_after_month_end", "source": src,
                "amount_cents": p["net_in_files_cents"], "effect": "open_balance",
                "detail": (f"{p['id']} for {window}: paid {p['paid_date']}, reaches the bank after month end"
                           if paid_in_month else
                           f"{p['id']} for {window}: paid {p['paid_date']}, after month end")})
            if p["data_gap_cents"]:
                exceptions.append({"kind": "missing_file", "source": src, "amount_cents": p["data_gap_cents"],
                                   "effect": "info",
                                   "detail": f"{p['id']} will pay {money(p['data_gap_cents'])} for activity missing "
                                             f"from our files ({window}); download the missing report before closing"})
        elif p["data_gap_cents"]:
            exceptions.append({"kind": "missing_file", "source": src, "amount_cents": -p["data_gap_cents"],
                               "effect": "open_balance",
                               "detail": f"{p['id']} paid {money(p['data_gap_cents'])} for activity missing from "
                                         f"our files ({window}); download the missing report and re-run"})
    for src, t in totals.items():
        if t["unpaid_activity_cents"]:
            exceptions.append({"kind": "unpaid_at_month_end", "source": src, "amount_cents": t["unpaid_activity_cents"],
                               "effect": "open_balance",
                               "detail": f"{LABEL[src]} activity at the end of {last:%B} that settles in the next "
                                         f"payout cycle"})

    for e in close["exceptions"]:  # the answer key's planted exceptions not already covered above
        if e["kind"] == "refund_without_order":
            src = "ebay" if e["detail"].startswith("eBay") else "amazon"
            exceptions.append({"kind": "prior_month_refund", "source": src, "amount_cents": None, "effect": "info",
                               "detail": e["detail"] + "; posted as a September refund, review August revenue"})
        elif e["kind"] in ("malformed_row", "duplicate_file", "overlapping_download"):
            exceptions.append({"kind": e["kind"], "source": "", "amount_cents": None, "effect": "info",
                               "detail": e["detail"] + ("; row left out of the totals" if e["kind"] == "malformed_row"
                                                        else "; counted once")})
    return {"month": month, "posting_date": last.isoformat(),
            "mock": f"payload from the {key['scenario']} answer key (stand-in for reconciliation)",
            "sources": sources, "deposits": deposits, "exceptions": exceptions}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scenario", default="messy_month")
    ap.add_argument("--out", default=str(ROOT / "out" / "close"))
    args = ap.parse_args(argv)
    key = json.loads((SAMPLES / args.scenario / "expected.json").read_text(encoding="utf-8"))
    payload = build(key)
    folder = Path(args.out) / payload["month"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"close_payload_{payload['month']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}: {len(payload['deposits'])} deposits, {len(payload['exceptions'])} exceptions")


if __name__ == "__main__":
    main()
