"""Month-end reconciliation from the raw inbox: bank deposits matched to marketplace payouts (B1-B2).

Reads one month's inbox and writes the close payload `reports.bc_export` takes
(docs/contracts/close-payload.md). Everything below comes from the raw files:
  - month totals: sales, refunds and fees from the engine's transactions.csv (`python -m engine run`);
  - bank credits: bank_activity_*.csv, each classified to a source by `Bank_Text` in bc_mapping.csv;
  - payouts: eBay `Payout` rows and Amazon `Transfer` rows in their reports (ShopGoodwill has no payout
    report in our files, so its deposits are matched to the source only);
  - matching: a deposit pays one or more consecutive payouts of its source, paid at most 5 days before it;
  - exceptions: unmatched deposits, payouts in transit, days no report covers (from the file names),
    refunds of orders sold before the month, rows the engine rejected or de-duplicated, and whatever
    open balance is left ("not yet paid out"), accepted only if it fits the source's payout cycle.
Everything here comes from the engine's files and the bank file; nothing is read from an answer key.
Shipping and handling are the engine's `shipping_cents` and `handling_cents` columns
(`docs/contracts/transaction.md` v0.4).

    python -m reports.reconcile --inbox data/sample/messy_month/inbox --month 2026-09
    python -m reports.bc_export --payload out/close/2026-09/close_payload_2026-09.json
"""
import argparse
import calendar
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from reports.bc_export import load_mapping, net

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "close"
WINDOW_DAYS = 5


def cents(text):
    """'1,234.50', '-469.47', '$84.00' -> integer cents. Empty -> 0."""
    t = (text or "").replace(",", "").replace("$", "").strip()
    if not t or t == "--":
        return 0
    sign = -1 if t.startswith("-") else 1
    whole, _, frac = t.lstrip("-").partition(".")
    return sign * (int(whole or 0) * 100 + int((frac + "00")[:2]))


def money(c):
    return f"{'-' if c < 0 else ''}${abs(c) / 100:,.2f}"


def report_rows(path, first_header):
    """Rows of a marketplace report with preamble lines before its header (header starts with `first_header`)."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f'"{first_header}"') or line.startswith(first_header))
    return list(csv.DictReader(lines[start:]))


# ---------------------------------------------------------------- inputs

def read_bank(inbox, mapping):
    credits = []
    for f in sorted(inbox.glob("bank_activity_*.csv")):
        for r in csv.DictReader(f.read_text(encoding="utf-8-sig").splitlines()):
            amount = cents(r["Credit"])
            if amount <= 0:
                continue  # debits (payroll, fees) are not marketplace money
            text = r["Description"].upper()
            source = next((s for s, m in mapping.items() if m.get("Bank_Text") and m["Bank_Text"].upper() in text), None)
            credits.append({"date": datetime.strptime(r["Posting Date"], "%m/%d/%Y").date(), "description": r["Description"],
                            "amount_cents": amount, "source": source})
    return credits


def read_payouts(inbox):
    """Payouts the marketplaces report, de-duplicated across overlapping downloads (one per source and day)."""
    found = {}
    for f in sorted(inbox.glob("ebay_transactions_*.csv")):
        for r in report_rows(f, "Transaction creation date"):
            if r["Type"] == "Payout":
                d = datetime.strptime(r["Transaction creation date"], "%b %d, %Y").date()
                found[("ebay", d)] = -cents(r["Net amount"])
    for f in sorted(inbox.glob("amazon_daterange_*.csv")):
        for r in report_rows(f, "date/time"):
            if r["type"] == "Transfer":
                d = datetime.strptime(r["date/time"].rsplit(" ", 1)[0], "%b %d, %Y %I:%M:%S %p").date()
                found[("amazon", d)] = -cents(r["total"])
    return [{"id": f"{src.upper()}-PAID-{d:%m%d}", "source": src, "paid": d, "amount_cents": a}
            for (src, d), a in sorted(found.items(), key=lambda kv: (kv[0][1], kv[0][0]))]


def run_engine(inbox, out, month_end):
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([sys.executable, "-m", "engine", "run", "--inbox", str(inbox), "--out", str(out),
                             "--date", month_end.isoformat()], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"engine run failed:\n{result.stdout}{result.stderr}")
    rows = list(csv.DictReader(open(out / "transactions.csv", encoding="utf-8")))
    warnings = json.loads((out / "warnings.json").read_text(encoding="utf-8"))
    return rows, warnings


def covered_days(inbox, prefix):
    """Days covered by a source's reports, from their file names (both date styles we receive)."""
    days = set()
    for f in inbox.glob(f"{prefix}*"):
        found = re.findall(r"(\d{4})-(\d{2})-(\d{2})", f.name) or [(y, m, d) for m, d, y in re.findall(r"(\d{2})-(\d{2})-(\d{4})", f.name)]
        if len(found) >= 2:
            a, b = (date(int(y), int(m), int(d)) for y, m, d in found[:2])
            days.update(a + timedelta(days=i) for i in range((b - a).days + 1))
    return days


# ---------------------------------------------------------------- matching

def match_deposits(deposits, payouts, window_days=WINDOW_DAYS):
    """Assign each bank credit to the payouts it pays. One deposit may cover several payouts of the
    same source (eBay batches weekend and holiday payouts): try runs of consecutive unmatched payouts,
    paid on or before the deposit date and at most `window_days` earlier, that sum exactly to it."""
    for dep in sorted(deposits, key=lambda d: d["date"]):
        dep["matches"] = []
        if dep["source"] is None:
            continue
        cands = sorted((p for p in payouts if p["source"] == dep["source"] and "deposit" not in p
                        and dep["date"] - timedelta(days=window_days) <= p["paid"] <= dep["date"]),
                       key=lambda p: p["paid"])
        for i in range(len(cands)):
            total = 0
            for j in range(i, len(cands)):
                total += cands[j]["amount_cents"]
                if total == dep["amount_cents"]:
                    for p in cands[i:j + 1]:
                        p["deposit"] = dep["date"]
                    dep["matches"] = [p["id"] for p in cands[i:j + 1]]
                    break
                if total > dep["amount_cents"]:
                    break
            if dep["matches"]:
                break
    return deposits, payouts


# ---------------------------------------------------------------- payload

def build(inbox, month, mapping, engine_out):
    y, m = map(int, month.split("-"))
    first, last = date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
    in_month = lambda iso: first.isoformat() <= iso <= last.isoformat()
    rows, warnings = run_engine(inbox, engine_out, last)
    deposits, payouts = match_deposits(read_bank(inbox, mapping), read_payouts(inbox))
    exceptions, stopgaps = [], []

    # Month totals per source from the engine (marketplace column).
    sources, revenue_by_day = {}, defaultdict(lambda: defaultdict(int))
    for src in mapping:
        mine = [r for r in rows if r["marketplace"] == src and in_month(r["business_date"])]
        if not mine:
            continue
        sales = sum(int(r["gross_cents"]) for r in mine if r["type"] == "sale")
        refunds = -sum(int(r["gross_cents"]) for r in mine if r["type"] == "refund")
        for r in mine:
            revenue_by_day[src][r["business_date"]] += int(r["gross_cents"])
        sources[src] = {"sales_cents": sales, "refunds_cents": refunds,
                        "fees_cents": sum(int(r["fee_cents"]) for r in mine),
                        "shipping_cents": sum(int(r["shipping_cents"]) for r in mine),
                        "handling_cents": sum(int(r["handling_cents"]) for r in mine)}

    payload_deposits = []
    for d in deposits:
        label = mapping[d["source"]]["Label"] if d["source"] else None
        if d["source"] is None:
            exceptions.append({"kind": "unmatched_deposit", "source": "", "amount_cents": d["amount_cents"],
                               "effect": "not_posted",
                               "detail": f"{d['date']} {d['description']}: matches no bank rule; held out of the journal"})
            continue
        payload_deposits.append({"date": d["date"].isoformat(), "source": d["source"], "amount_cents": d["amount_cents"],
                                 "reference": f"{d['description']}" + (f" ({', '.join(d['matches'])})" if d["matches"] else ""),
                                 "matches": d["matches"]})
        has_payouts = any(p["source"] == d["source"] for p in payouts)
        if has_payouts and not d["matches"]:
            exceptions.append({"kind": "deposit_payout_mismatch", "source": d["source"], "amount_cents": d["amount_cents"],
                               "effect": "info",
                               "detail": f"{d['date']} {label} deposit {money(d['amount_cents'])} matches no run of "
                                         f"{label} payouts; posted to {label}, check the payout report"})

    in_transit = defaultdict(int)
    for p in payouts:
        if "deposit" not in p and first <= p["paid"] <= last:
            in_transit[p["source"]] += p["amount_cents"]
            exceptions.append({"kind": "in_transit", "source": p["source"], "amount_cents": p["amount_cents"],
                               "effect": "open_balance",
                               "detail": f"{p['id']}: paid {p['paid']}, not in the bank by {last}"})

    for src, m in mapping.items():
        if src not in sources or not m.get("Report_Prefix"):
            continue
        covered = covered_days(inbox, m["Report_Prefix"])
        if covered:
            gaps = [d for d in (first + timedelta(days=i) for i in range((last - first).days + 1)) if d not in covered]
            if gaps:
                exceptions.append({"kind": "missing_report", "source": src, "amount_cents": None, "effect": "info",
                                   "detail": f"no {m['Label']} report covers {', '.join(g.isoformat() for g in gaps)}; "
                                             f"totals and payouts for those days can't be checked"})

    sold = {r["order_id"] for r in rows if r["type"] == "sale"}
    for r in rows:
        if r["type"] == "refund" and in_month(r["business_date"]) and r["order_id"] not in sold:
            exceptions.append({"kind": "prior_month_refund", "source": r["marketplace"],
                               "amount_cents": int(r["gross_cents"]), "effect": "info",
                               "detail": f"{r['order_id']} refunded {r['business_date']}, sale not in this month's files; "
                                         f"posted as a refund this month, review the prior month's revenue"})

    by_kind = defaultdict(list)
    for w in warnings:
        by_kind[w["kind"]].append(w)
    for kind, ws in sorted(by_kind.items()):
        if kind == "unparseable":
            ws = [w for w in ws if not w["source_file"].startswith("bank_activity")]  # read here, not by the engine
        if kind == "duplicate":
            files = sorted({w["source_file"] for w in ws})
            exceptions.append({"kind": "duplicate_rows", "source": "", "amount_cents": None, "effect": "info",
                               "detail": f"{len(ws)} duplicate rows counted once ({len(files)} files)"})
            continue
        for w in ws:
            exceptions.append({"kind": kind, "source": "", "amount_cents": None, "effect": "info",
                               "detail": f"{w['source_file']} row {w['source_row']}: {w['reason']}; left out of the totals"})

    # What is left open after deposits and payouts in transit: activity not paid out yet. Accept it
    # only if it fits the source's payout cycle (between 0 and the last Settles_Within_Days of revenue).
    for src, s in sources.items():
        m = mapping[src]
        open_balance = net(s) - sum(d["amount_cents"] for d in payload_deposits if d["source"] == src)
        residual = open_balance - in_transit[src]
        days = int(m.get("Settles_Within_Days") or 0)
        tail = sum(v for d, v in revenue_by_day[src].items() if d > (last - timedelta(days=days)).isoformat())
        total = sum(revenue_by_day[src].values()) or 1
        ceiling = round(net(s) * tail / total)
        if residual == 0:
            continue
        if 0 < residual <= ceiling:
            exceptions.append({"kind": "not_yet_paid_out", "source": src, "amount_cents": residual, "effect": "open_balance",
                               "detail": f"{m['Label']} activity in the last {days} days of the month not paid out yet "
                                         f"({money(residual)}, within the {money(ceiling)} that cycle covers)"})
        else:
            why = ("more was paid than our files show" if residual < 0
                   else f"more than the last {days} days of activity ({money(ceiling)})")
            exceptions.append({"kind": "residual_unexplained", "source": src, "amount_cents": residual, "effect": "info",
                               "detail": f"{m['Label']}: {money(residual)} left after deposits and payouts in transit; "
                                         f"{why}. Check the missing reports above before closing"})

    return {"month": month, "posting_date": last.isoformat(),
            "mock": "reconciled from the raw inbox" + (" (shipping/handling stopgap from the answer key)" if stopgaps else ""),
            "inbox": str(inbox), "stopgaps": stopgaps,
            "sources": sources, "deposits": payload_deposits, "exceptions": exceptions,
            "payouts": [{**p, "paid": p["paid"].isoformat(), "deposit": p.get("deposit") and p["deposit"].isoformat()}
                        for p in payouts]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inbox", required=True)
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    inbox = Path(args.inbox)
    folder = Path(args.out) / args.month
    payload = build(inbox, args.month, load_mapping(), folder / "engine")
    path = folder / f"close_payload_{args.month}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    matched = sum(bool(d["matches"]) for d in payload["deposits"])
    print(f"wrote {path}")
    print(f"  {len(payload['deposits'])} deposits classified ({matched} matched to payouts), "
          f"{len(payload['payouts'])} payouts read, {len(payload['exceptions'])} exceptions")
    for s in payload["stopgaps"]:
        print(f"  STOPGAP {s}")


if __name__ == "__main__":
    main()
