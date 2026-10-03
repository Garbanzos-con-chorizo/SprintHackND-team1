"""Export schema shared by the daily pulse and the monthly rollup, so both CSVs have one layout."""
import csv

MARKETPLACES = ["shopgoodwill", "amazon", "ebay", "other"]
METRICS = ["revenue_cents", "refunds_cents", "fees_cents", "orders", "customers"]
LABELS = {"shopgoodwill": "ShopGoodwill", "amazon": "Amazon", "ebay": "eBay", "other": "Other"}
CSV_COLUMNS = ["Date", "Marketplace", "Status", "Revenue", "Refunds", "Fees", "Orders", "Customers",
               "Customer Basis"]


def day_record(p):
    """Flatten one pulse JSON into the per-day record used by the CSV and the monthly JSON."""
    markets = {}
    for mk in MARKETPLACES:
        m = p["marketplaces"].get(mk, {"status": "missing"})
        ok = m["status"] == "ok"
        markets[mk] = {"label": m.get("label") or LABELS[mk], "status": m["status"],
                       "customer_basis": m.get("customer_basis") if ok else None,
                       **{k: m.get(k) if ok else None for k in METRICS}}
    ent = p["enterprise"]
    excluded = [x["marketplace"] if isinstance(x, dict) else x for x in ent.get("excluded") or []]
    return {"date": p["business_date"], "marketplaces": markets,
            "enterprise": {**{k: ent.get(k) for k in METRICS},
                           "complete": not excluded, "excluded": excluded}}


def dollars(cents):
    return "" if cents is None else f"{cents / 100:.2f}"


def blank(n):
    return "" if n is None else n


def write_csv(path, days):
    """One row per day and marketplace, dollars. Blank (not 0) when there is no data, so BI sums stay honest."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for d in days:
            for mk in MARKETPLACES:
                m = d["marketplaces"][mk]
                w.writerow([d["date"], m["label"], m["status"], dollars(m["revenue_cents"]),
                            dollars(m["refunds_cents"]), dollars(m["fees_cents"]), blank(m["orders"]),
                            blank(m["customers"]), m["customer_basis"] or ""])
