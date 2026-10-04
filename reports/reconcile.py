"""Month-end reconciliation from the raw inbox: bank deposits matched to marketplace payouts (B1-B2).

Runs the engine on one month's inbox and writes the close payload `reports.bc_export` takes
(docs/contracts/close-payload.md). Everything below comes from the files the engine writes from that
inbox (docs/contracts/close-inputs.md); this module parses no report itself:
  - month totals: sales, refunds and fees from the engine's transactions.csv (`python -m engine run`);
  - bank credits: the engine's bank.csv, each classified to a source by `Bank_Text` in bc_mapping.csv;
  - payouts: the engine's payouts.csv (eBay `Payout` rows, Amazon `Transfer` rows). ShopGoodwill has no
    payout report in our files, so each of its deposits is taken as a payout;
  - matching: a deposit pays one or more consecutive payouts of its source, paid at most 5 days before it;
  - payout windows: each payout is compared with what our files hold for the days it covers (the
    source's `Payout_Cutoff` and `Payout_Timezone` in bc_mapping.csv). A payout that paid more than the
    files hold, for a window with days no report covers, is a `payout_data_gap`; any other difference is
    a `payout_mismatch`; activity no payout covers yet is `not_yet_paid_out`, with its exact amount.
    Nothing is netted: the month's open balance is the sum of those lines and the payouts in transit;
  - other exceptions: unmatched deposits, payouts in transit, days no report covers (from the file
    names), refunds of orders sold before the month, rows the engine rejected or de-duplicated;
  - cross-check: when the inbox also holds the Cash Monkey Orders report for a marketplace that has its
    own report (`Cross_Check_Source` in bc_mapping.csv), its rows are compared with the report order by
    order and never added to it: the same sales are in both.
Everything here comes from the engine's files and the bank file; nothing is read from an answer key.
Shipping and handling are the engine's `shipping_cents` and `handling_cents` columns
(`docs/contracts/transaction.md` v0.4). Payout windows need the day each row counts toward in its
marketplace's own calendar: the order's time (`occurred_at`, v0.5), or the Eastern `business_date` for a
marketplace that pays by Eastern days (eBay). A source whose rows have neither (Amazon and ShopGoodwill
pay by Pacific days) keeps the older check of its open balance as one figure, and the output says so
(`no_order_times`); it switches to payout windows by itself once the engine writes the column.
Not modeled: last month's open items are not carried over, so the month starts with no opening balance.

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
from zoneinfo import ZoneInfo

from reports.bc_export import load_mapping, net

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "close"
WINDOW_DAYS = 5
EASTERN = "America/New_York"  # the zone of the engine's business_date
WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


def money(c):
    return f"{'-' if c < 0 else ''}${abs(c) / 100:,.2f}"


# ---------------------------------------------------------------- inputs

def run_engine(inbox, out, month_end):
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([sys.executable, "-m", "engine", "run", "--inbox", str(inbox), "--out", str(out),
                             "--date", month_end.isoformat()], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"engine run failed:\n{result.stdout}{result.stderr}")
    rows = list(csv.DictReader(open(out / "transactions.csv", encoding="utf-8")))
    warnings = json.loads((out / "warnings.json").read_text(encoding="utf-8"))
    return rows, warnings


def engine_csv(out, name):
    """Rows of one of the files the engine writes for the close (docs/contracts/close-inputs.md)."""
    path = out / name
    if not path.exists():
        raise SystemExit(f"{path} is missing: the engine writes it since close-inputs.md v0.1 (is engine/ up to date?)")
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def bank_credits(out, mapping):
    """The bank's credits from the engine's bank.csv, each classified to a source by `Bank_Text` in
    bc_mapping.csv (None when no rule matches). Debits (payroll, fees, carriers) are not marketplace money."""
    credits = []
    for r in engine_csv(out, "bank.csv"):
        amount = int(r["amount_cents"])
        if amount <= 0:
            continue
        text = r["description"].upper()
        source = next((s for s, m in mapping.items() if m.get("Bank_Text") and m["Bank_Text"].upper() in text), None)
        credits.append({"date": date.fromisoformat(r["posting_date"]), "description": r["description"],
                        "amount_cents": amount, "source": source})
    return credits


def reported_payouts(out):
    """The payouts the marketplaces report, from the engine's payouts.csv (one per marketplace and day,
    already de-duplicated across overlapping downloads). A payout whose report states the period it
    pays for keeps it (`period_from`, `period_to`)."""
    payouts = []
    for r in sorted(engine_csv(out, "payouts.csv"), key=lambda r: (r["paid_date"], r["marketplace"], r["payout_id"])):
        again = r["payout_id"].partition("#")[2]  # a second payout on the same day is `...#2`
        p = {"id": f"{r['marketplace'].upper()}-PAID-{r['paid_date'][5:7]}{r['paid_date'][8:]}" + (f"-{again}" if again else ""),
             "source": r["marketplace"], "paid": date.fromisoformat(r["paid_date"]), "amount_cents": int(r["amount_cents"])}
        if r.get("period_from") and r.get("period_to"):
            p.update(period_from=date.fromisoformat(r["period_from"]), period_to=date.fromisoformat(r["period_to"]))
        payouts.append(p)
    return payouts


def covered_days(inbox, prefix):
    """Days covered by a source's reports, from their file names (both date styles we receive)."""
    days = set()
    for f in inbox.glob(f"{prefix}*"):
        found = re.findall(r"(\d{4})-(\d{2})-(\d{2})", f.name) or [(y, m, d) for m, d, y in re.findall(r"(\d{2})-(\d{2})-(\d{4})", f.name)]
        if len(found) >= 2:
            a, b = (date(int(y), int(m), int(d)) for y, m, d in found[:2])
            days.update(a + timedelta(days=i) for i in range((b - a).days + 1))
    return days


# ---------------------------------------------------------------- cross-check

SOURCE_LABELS = {"cashmonkey": "Cash Monkey"}


def split_cross_checks(rows, mapping):
    """Set aside the rows a marketplace gets from its `Cross_Check_Source` (the Cash Monkey Orders report,
    for eBay and Amazon) when the marketplace also has rows from its own report: the same sales are in
    both, and adding them would count the revenue twice. With no report of its own (the nightly run),
    those rows are all we have and they stay. Returns (rows for the close, {marketplace: rows set aside})."""
    check = {src: m.get("Cross_Check_Source") for src, m in mapping.items() if m.get("Cross_Check_Source")}
    has_own = {r["marketplace"] for r in rows if r.get("source") != check.get(r["marketplace"])}
    journal, aside = [], defaultdict(list)
    for r in rows:
        src = r["marketplace"]
        if src in check and r.get("source") == check[src] and src in has_own:
            aside[src].append(r)
        else:
            journal.append(r)
    return journal, aside


def cross_check(src, m, ours, theirs):
    """Compare a marketplace's own report with the same month in its cross-check source, order by order.
    Sales only: the Cash Monkey Orders report lists orders, not refunds. Returns the summary and the
    exceptions (none when both hold the same orders at the same amounts)."""
    label, other = m["Label"], SOURCE_LABELS.get(m["Cross_Check_Source"], m["Cross_Check_Source"])
    a = {r["order_id"]: r for r in ours if r["type"] == "sale"}
    b = {r["order_id"]: r for r in theirs if r["type"] == "sale"}
    only_theirs = [b[k] for k in sorted(b.keys() - a.keys())]
    only_ours = [a[k] for k in sorted(a.keys() - b.keys())]
    changed = sorted(k for k in a.keys() & b.keys() if a[k]["gross_cents"] != b[k]["gross_cents"])
    total = lambda rs: sum(int(r["gross_cents"]) for r in rs)
    dated = lambda rs: day_ranges(date.fromisoformat(r["business_date"]) for r in rs)
    orders = lambda n: f"{n} order" + ("" if n == 1 else "s")
    summary = {"source": src, "against": m["Cross_Check_Source"], "report_sales_cents": total(a.values()),
               "against_sales_cents": total(b.values()), "difference_cents": total(b.values()) - total(a.values()),
               "orders_only_in_against": len(only_theirs), "orders_only_in_report": len(only_ours),
               "orders_with_another_amount": len(changed)}
    parts = []
    if only_theirs:
        parts.append(f"{other} holds {orders(len(only_theirs))} from {label} ({money(total(only_theirs))} of sales) "
                     f"that the {label} reports do not, dated {dated(only_theirs)}")
    if only_ours:
        parts.append(f"the {label} reports hold {orders(len(only_ours))} ({money(total(only_ours))} of sales) that "
                     f"{other} does not, dated {dated(only_ours)}")
    if changed:
        parts.append(f"{orders(len(changed))} with another amount in {other} (first: {changed[0]})")
    if not parts:
        return summary, []
    return summary, [{"kind": "cross_check_difference", "source": src, "amount_cents": summary["difference_cents"],
                      "effect": "info",
                      "detail": "; ".join(parts) + f". The journal posts the {label} reports only: if those sales "
                                                   f"are real, a report is missing"}]


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


# ---------------------------------------------------------------- payout windows

def row_net(r):
    """What the marketplace owes for one engine row (bc_export.net, per row)."""
    return int(r["gross_cents"]) + int(r["shipping_cents"]) + int(r["handling_cents"]) - int(r["fee_cents"])


def payout_day(row, tz):
    """The day a row counts toward in its marketplace's payout calendar, and whether that is exact.

    Payout cycles run on the marketplace's own days (Amazon and ShopGoodwill: Pacific); the engine's
    `business_date` is Eastern. With `occurred_at` the day is exact. Without it we use `business_date`,
    which is exact only for a marketplace that pays by Eastern days."""
    stamp = (row.get("occurred_at") or "").strip()
    if stamp:
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            when = None
        if when is not None and when.tzinfo is not None:
            return when.astimezone(ZoneInfo(tz)).date(), True
    return date.fromisoformat(row["business_date"]), tz == EASTERN


def set_windows(payouts, rule, first):
    """Give each payout of one source the days of activity it covers (`activity_from`, `activity_to`).

    A payout that states its own period (`period_from`, `period_to`) keeps it. Otherwise the source's
    `Payout_Cutoff` rule applies to the day it was paid:
      daily         paid on D for the activity of D-1 (eBay)
      previous_day  paid on D for everything since the previous payout, through D-1 (Amazon)
      weekly:SUN    covers everything since the previous payout, through the last Sunday before D
                    (ShopGoodwill; any of MON..SUN)
    The first payout starts on the 1st: last month's open items are not carried over."""
    prev_to = None
    for p in sorted(payouts, key=lambda p: p["paid"]):
        paid = p["paid"]
        if p.get("period_from") and p.get("period_to"):
            start, end = p["period_from"], p["period_to"]
        elif rule == "daily":
            start = end = paid - timedelta(days=1)
        elif rule == "previous_day":
            end = paid - timedelta(days=1)
            start = prev_to + timedelta(days=1) if prev_to else min(first, end)
        elif rule.startswith("weekly:") and rule[7:] in WEEKDAYS:
            end = paid - timedelta(days=(paid.weekday() - WEEKDAYS[rule[7:]] - 1) % 7 + 1)
            start = prev_to + timedelta(days=1) if prev_to else min(first, end)
        else:
            raise SystemExit(f"bc_mapping.csv: Payout_Cutoff '{rule}' is not daily, previous_day or weekly:<MON..SUN>")
        p["activity_from"], p["activity_to"] = start, end
        prev_to = end
    return payouts


def zone_label(tz):
    return {"America/New_York": "Eastern", "America/Los_Angeles": "Pacific"}.get(tz, tz)


def day_ranges(days):
    """Sorted days as text, runs joined: '2026-09-21 to 2026-09-22, 2026-09-30'."""
    days, out = sorted(set(days)), []
    for d in days:
        if out and d - out[-1][1] == timedelta(days=1):
            out[-1][1] = d
        else:
            out.append([d, d])
    return ", ".join(a.isoformat() if a == b else f"{a} to {b}" for a, b in out)


def explain_payouts(src, m, rows, payouts, covered, first, last):
    """Compare each payout of one source with what the files hold for its window.

    `rows` are the source's engine rows of the month, each with an exact payout day (see `payout_day`);
    `payouts` its payouts (windows are set here); `covered` the days its reports cover, or an empty set
    when the file names don't say. Returns the exceptions; each payout gains `files_net_cents`,
    `gap_cents` (paid minus files) and `days_missing`."""
    label, tz = m["Label"], m.get("Payout_Timezone") or EASTERN
    set_windows(payouts, m["Payout_Cutoff"], first)
    exceptions, by_day = [], defaultdict(int)
    for r in rows:
        by_day[payout_day(r, tz)[0]] += row_net(r)
    paid_days = set()
    for p in sorted(payouts, key=lambda p: p["paid"]):
        a, b = p["activity_from"], p["activity_to"]
        if b < first:  # last month's activity, paid this month
            exceptions.append({"kind": "prior_month_payout", "source": src, "amount_cents": -p["amount_cents"],
                               "effect": "open_balance",
                               "detail": f"{p['id']}: {money(p['amount_cents'])} for activity through {b}, before the "
                                         f"month; it belongs to last month's receivable, which is not carried over"})
            continue
        window = [a + timedelta(days=i) for i in range((b - a).days + 1)]
        paid_days.update(window)
        files = sum(by_day[d] for d in window)
        gap = p["amount_cents"] - files
        missing = [d for d in window if covered and d not in covered and first <= d <= last]
        p.update(files_net_cents=files, gap_cents=gap, days_missing=[d.isoformat() for d in missing])
        span = a.isoformat() if a == b else f"{a} to {b}"
        if gap > 0 and missing:
            exceptions.append({"kind": "payout_data_gap", "source": src, "amount_cents": -gap, "effect": "open_balance",
                               "detail": f"{p['id']} paid {money(p['amount_cents'])} for {span}; our files hold "
                                         f"{money(files)} for those days. No {label} report covers "
                                         f"{day_ranges(missing)}: download it and run the close again"})
        elif gap:
            exceptions.append({"kind": "payout_mismatch", "source": src, "amount_cents": gap, "effect": "info",
                               "detail": f"{p['id']} paid {money(p['amount_cents'])} for {span}; our files hold "
                                         f"{money(files)} for those days and no report is missing. Check the "
                                         f"payout report before closing"})
    unpaid_days = [d for d in by_day if d not in paid_days and by_day[d]]
    unpaid = sum(by_day[d] for d in unpaid_days)
    if unpaid:
        exceptions.append({"kind": "not_yet_paid_out", "source": src, "amount_cents": unpaid, "effect": "open_balance",
                           "detail": f"{label} activity no payout covers yet: {day_ranges(unpaid_days)} "
                                     f"({zone_label(tz)} days), {money(unpaid)}"})
    return exceptions


def check_whole_balance(src, m, s, rows, deposited, in_transit, last):
    """The rule before payout windows, kept as the fallback for a source whose rows carry no order time
    (and for one with no Payout_Cutoff): what is left after deposits and payouts in transit is accepted as
    "not yet paid out" only if it fits the last `Settles_Within_Days` of revenue. It checks one net figure,
    so two amounts that cancel pass unseen; delete it, with that mapping column, once the engine writes
    `occurred_at` for every source that pays by non-Eastern days."""
    residual = net(s) - deposited - in_transit
    if residual == 0:
        return []
    days = int(m.get("Settles_Within_Days") or 0)
    by_day = defaultdict(int)
    for r in rows:
        by_day[r["business_date"]] += int(r["gross_cents"])
    tail = sum(v for d, v in by_day.items() if d > (last - timedelta(days=days)).isoformat())
    ceiling = round(net(s) * tail / (sum(by_day.values()) or 1))
    if 0 < residual <= ceiling:
        return [{"kind": "not_yet_paid_out", "source": src, "amount_cents": residual, "effect": "open_balance",
                 "detail": f"{m['Label']} activity in the last {days} days of the month not paid out yet "
                           f"({money(residual)}, within the {money(ceiling)} that cycle covers)"}]
    why = ("more was paid than our files show" if residual < 0
           else f"more than the last {days} days of activity ({money(ceiling)})")
    return [{"kind": "residual_unexplained", "source": src, "amount_cents": residual, "effect": "info",
             "detail": f"{m['Label']}: {money(residual)} left after deposits and payouts in transit; "
                       f"{why}. Check the missing reports above before closing"}]


# ---------------------------------------------------------------- payload

def build(inbox, month, mapping, engine_out):
    y, m = map(int, month.split("-"))
    first, last = date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
    in_month = lambda iso: first.isoformat() <= iso <= last.isoformat()
    rows, warnings = run_engine(inbox, engine_out, last)
    rows, set_aside = split_cross_checks(rows, mapping)
    deposits, payouts = match_deposits(bank_credits(engine_out, mapping), reported_payouts(engine_out))
    exceptions, stopgaps = [], []

    # Month totals per source from the engine (marketplace column). A marketplace with rows but no row in
    # bc_mapping.csv goes into the payload too: the export then lists it as `unmapped_source` and posts
    # nothing for it, so it is never left out in silence.
    sources, month_rows = {}, {}
    in_files = sorted({r["marketplace"] for r in rows if in_month(r["business_date"])} - set(mapping))
    for src in [*mapping, *in_files]:
        mine = [r for r in rows if r["marketplace"] == src and in_month(r["business_date"])]
        if not mine:
            continue
        month_rows[src] = mine
        sales = sum(int(r["gross_cents"]) for r in mine if r["type"] == "sale")
        refunds = -sum(int(r["gross_cents"]) for r in mine if r["type"] == "refund")
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

    covered_by = {src: covered_days(inbox, m["Report_Prefix"]) if m.get("Report_Prefix") else set()
                  for src, m in mapping.items()}
    for src, m in mapping.items():
        covered = covered_by[src]
        if src not in sources:
            continue
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
        if kind == "duplicate":
            files = sorted({w["source_file"] for w in ws})
            exceptions.append({"kind": "duplicate_rows", "source": "", "amount_cents": None, "effect": "info",
                               "detail": f"{len(ws)} duplicate rows counted once ({len(files)} files)"})
            continue
        for w in ws:
            exceptions.append({"kind": kind, "source": "", "amount_cents": None, "effect": "info",
                               "detail": f"{w['source_file']} row {w['source_row']}: {w['reason']}; left out of the totals"})

    cross_checks = []
    for src, theirs in set_aside.items():
        summary, found = cross_check(src, mapping[src], month_rows.get(src, []),
                                     [r for r in theirs if in_month(r["business_date"])])
        cross_checks.append(summary)
        exceptions += found

    # What is left open after the deposits: explained payout by payout, never as one net figure.
    for src, s in sources.items():
        if src not in mapping:
            continue  # unmapped: the export reports it and posts nothing
        m = mapping[src]
        tz = m.get("Payout_Timezone") or EASTERN
        no_time = sum(not payout_day(r, tz)[1] for r in month_rows[src])
        if not m.get("Payout_Cutoff") or no_time:
            deposited = sum(d["amount_cents"] for d in payload_deposits if d["source"] == src)
            exceptions += check_whole_balance(src, m, s, month_rows[src], deposited, in_transit[src], last)
            if no_time:
                exceptions.append({"kind": "no_order_times", "source": src, "amount_cents": None, "effect": "info",
                                   "detail": f"{no_time} {m['Label']} rows carry no order time (occurred_at). "
                                             f"{m['Label']} pays by {zone_label(tz)} days and "
                                             f"the engine's day is Eastern, so its payouts cannot be checked one by "
                                             f"one: the open balance is checked as one figure instead"})
            continue
        mine = [p for p in payouts if p["source"] == src]
        if not mine:  # no payout report in the files (ShopGoodwill): each of its deposits is a payout
            mine = [{"id": f"{src.upper()}-DEP-{d['date']:%m%d}", "source": src, "paid": d["date"], "deposit": d["date"],
                     "amount_cents": d["amount_cents"], "inferred": True} for d in deposits if d["source"] == src]
            payouts.extend(mine)
        exceptions += explain_payouts(src, m, month_rows[src], mine, covered_by[src], first, last)

    iso = lambda v: v.isoformat() if isinstance(v, date) else v
    return {"month": month, "posting_date": last.isoformat(),
            "origin": "reconciled from the raw inbox", "inbox": str(inbox), "stopgaps": stopgaps,
            "sources": sources, "deposits": payload_deposits, "exceptions": exceptions, "cross_checks": cross_checks,
            "payouts": [{**{k: iso(v) for k, v in p.items()}, "deposit": iso(p.get("deposit"))} for p in payouts]}


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
    read = sum(not p.get("inferred") for p in payload["payouts"])
    print(f"wrote {path}")
    print(f"  {len(payload['deposits'])} deposits classified ({matched} matched to payouts), "
          f"{read} payouts read, {len(payload['exceptions'])} exceptions")
    for c in payload["cross_checks"]:
        other = SOURCE_LABELS.get(c["against"], c["against"])
        print(f"  cross-check, {c['source']} sales: its reports {money(c['report_sales_cents'])}, {other} "
              f"{money(c['against_sales_cents'])}, difference {money(c['difference_cents'])} "
              f"({c['orders_only_in_against']} orders only in {other}, {c['orders_only_in_report']} only in the reports)")
    for s in payload["stopgaps"]:
        print(f"  STOPGAP {s}")


if __name__ == "__main__":
    main()
