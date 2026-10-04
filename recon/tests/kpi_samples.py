"""Test databases for the KPI calculator, and the example files of docs/contracts/kpi.md.

    python -m recon.tests.kpi_samples                         # rewrite the contract examples from the calculator
    python -m recon.tests.kpi_samples --db out/store/ecom.db  # or write the sample database, to try recon.kpi on

Both build the store from Victor's engine/store/schema.sql (only the file is read; nothing of
engine.store is imported). `make_db` fills it with hand-made rows. `build_sample_db` fills it
with the scenario behind the contract examples, September and October 1 to 4: its pulse rows
are the answer keys of data/sample (real), while every internal number and the buyers are invented.
"""
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from recon.kpi import cli, store

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "engine" / "store" / "schema.sql"
EXAMPLES = ROOT / "docs" / "contracts" / "examples"
ANSWERS = ROOT / "data" / "sample"
# (example file, period type, period id, generated_at)
SAMPLES = (
    ("kpi.sample.month.json", "month", "2026-09", "2026-10-01T00:20:00-04:00"),
    ("kpi.sample.month.partial.json", "month", "2026-10", "2026-10-05T00:20:00-04:00"),
    ("kpi.sample.week.json", "week", "2026-W40", "2026-10-05T00:20:00-04:00"),
    ("kpi.sample.day.json", "day", "2026-10-04", "2026-10-05T00:20:00-04:00"),
)
# Units of the internal metrics (docs/contracts/internal-api.md).
UNITS = {
    "labor_hours": "hours", "labor_cost_cents": "cents", "employees": "fte", "listings_created": "listings",
    "donation_to_listing_days": "items", "unlisted_backlog": "items", "active_listings_by_age": "listings",
    "shipping_net_cost_cents": "cents", "category_sales_cents": "cents", "category_cogs_cents": "cents",
}

# (category, share of internal sales, cost of goods as a share of its sales): invented
CATEGORIES = (
    ("Collectibles", 0.17, 0.22), ("Jewelry & Watches", 0.15, 0.18), ("Electronics", 0.13, 0.38),
    ("Clothing & Shoes", 0.12, 0.30), ("Books & Media", 0.11, 0.42), ("Home & Kitchen", 0.09, 0.34),
    ("Toys & Games", 0.07, 0.33), ("Art & Antiques", 0.05, 0.20), ("Musical Instruments", 0.04, 0.28),
    ("Sporting Goods", 0.03, 0.35), ("Cameras & Photo", 0.025, 0.31), ("Crafts & Sewing", 0.015, 0.40),
)
# Invented internal totals per block of days. `ages` is items listed by days since donation;
# `buyers` is how many orders each ShopGoodwill buyer places (a 3 is a repeat buyer with three orders).
BLOCKS = (
    {"days": ("2026-09-01", "2026-09-04"), "labor_hours": 201.8, "labor_cost_cents": 353150,
     "shipping_net_cost_cents": 40300, "internal_sales_cents": 884200,
     "listings": {"shopgoodwill": 246, "amazon": 80, "ebay": 129},
     "ages": {5: 100, 6: 100, 7: 100, 8: 100, 9: 55},
     "active": {"0-30": 1540, "31-60": 541, "61-90": 150, "91+": 52},
     "buyers": [2] * 4 + [3] * 3 + [1] * 130},
    {"days": ("2026-09-05", "2026-09-30"), "labor_hours": 1345.1, "labor_cost_cents": 2353925,
     "shipping_net_cost_cents": 278100, "internal_sales_cents": 6128200,
     "listings": {"shopgoodwill": 1657, "amazon": 545, "ebay": 877},
     "ages": {3: 500, 4: 500, 5: 550, 6: 700, 7: 400, 8: 300, 9: 129},
     "active": {"0-30": 1570, "31-60": 520, "61-90": 160, "91+": 60},
     "buyers": [3] * 164 + [2] * 43 + [1] * 486},
    {"days": ("2026-10-01", "2026-10-04"), "labor_hours": 206.3, "labor_cost_cents": 361025,
     "shipping_net_cost_cents": 44100, "internal_sales_cents": 1021300,
     "listings": {"shopgoodwill": 254, "amazon": 83, "ebay": 134},
     "ages": {},  # the internal API returned no donation dates: shows an internal no_data
     "active": {"0-30": 1602, "31-60": 498, "61-90": 171, "91+": 64},
     "buyers": [3] * 7 + [2] * 2 + [1] * 162},
)
NO_BACKLOG = "2026-10-04"  # the backlog snapshot of that night is missing: shows an old snapshot
# Listings still active on August 31, the night before the scenario starts (the real backfill pulls it too).
OPENING = ("2026-08-31", {"0-30": 1490, "31-60": 560, "61-90": 170, "91+": 80})
# How long before its sale a unit had been listed: (days, share of the day's units). Invented.
SALE_AGES = ((0, 0.05), (2, 0.15), (5, 0.30), (9, 0.30), (16, 0.20))


def make_db(path, pulse=(), sales=(), internal=()):
    """A store (engine/store/schema.sql) with hand-made rows.

    pulse:    (day, marketplace, status, gross, refunds, fees, orders), numbers None unless ok
    sales:    (day, marketplace, order_id, customer_id), plus a unit count if there is one
    internal: (day, metric, dimension, value), source "mock" unless a fifth item says otherwise
    """
    con = sqlite3.connect(path)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.executemany(
        "INSERT INTO pulse_daily (business_date, marketplace, status, gross_cents, refunds_cents, revenue_cents,"
        " fees_cents, orders, run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'test')",
        [(day, m, status, gross, refunds, None if gross is None else gross + refunds, fees, orders)
         for day, m, status, gross, refunds, fees, orders in pulse],
    )
    # Amounts stay 0: the KPIs take money from pulse_daily and only count orders, buyers and units here.
    con.executemany(
        "INSERT INTO transactions (txn_id, source, marketplace, type, business_date, order_id, customer_id,"
        " customer_basis, gross_cents, fee_cents, units, source_file, source_row, run_id)"
        " VALUES (?, ?, ?, 'sale', ?, ?, ?, ?, 0, 0, ?, 'test.csv', ?, 'test')",
        [(f"{m}:{order}:sale", m, m, day, order, buyer, "buyer" if buyer else "order", units[0] if units else None, i)
         for i, (day, m, order, buyer, *units) in enumerate(sales, start=1)],
    )
    con.executemany(
        "INSERT INTO internal_daily (business_date, metric, dimension, value, unit, source, run_id)"
        " VALUES (?, ?, ?, ?, ?, ?, 'test')",
        [(day, metric, dimension, value, UNITS.get(metric, ""), source[0] if source else "mock")
         for day, metric, dimension, value, *source in internal],
    )
    con.commit()
    con.close()


def _days(block):
    first, last = (date.fromisoformat(d) for d in block["days"])
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]


def _spread(total, n):
    """An integer split over n days as evenly as it goes."""
    return [total // n + (i < total % n) for i in range(n)]


def _by_weight(total, weights):
    """An integer split in proportion to the weights, adding up exactly."""
    exact = [total * w / sum(weights) for w in weights]
    parts = [int(x) for x in exact]
    for i in sorted(range(len(parts)), key=lambda i: (parts[i] - exact[i], i))[: total - sum(parts)]:
        parts[i] += 1
    return parts


def _employees(day):
    if day <= "2026-09-04":
        return 9.0
    return 10.0 if "2026-09-27" <= day <= "2026-09-30" else 9.5


def _backlog(day):
    d = int(day[-2:])
    if day.startswith("2026-10"):
        return 8420 + round(d * 95 / 4)
    return 8105 - (4 - d) * 10 if d <= 4 else 8105 + round((d - 4) * 315 / 26)


def answer_days():
    """{day: {marketplace: answer-key row}} for September (clean_month) and October 1 to 4 (the day_* scenarios)."""
    def key(scenario):
        return json.loads((ANSWERS / scenario / "expected.json").read_text(encoding="utf-8"))

    days = dict(key("clean_month")["days"])
    for scenario in ("day_clean", "day_refund", "day_ebay_missing", "day_duplicates"):
        answer = key(scenario)
        days[answer["business_date"]] = answer["days"][answer["business_date"]]
    return days


def build_sample_db(path):
    """The database behind the contract examples."""
    answers = answer_days()
    pulse, sales, internal = [], [], []
    internal.extend((OPENING[0], "active_listings_by_age", bucket, n) for bucket, n in OPENING[1].items())
    for block in BLOCKS:
        days = _days(block)
        working = [day for day in days if date.fromisoformat(day).weekday() != 6]  # nothing is produced on Sundays
        buyers = iter([f"sg-{days[0]}-{i}" for i, orders in enumerate(block["buyers"]) for _ in range(orders)])
        planned = sum(block["buyers"])
        actual = sum(answers[day]["shopgoodwill"].get("orders", 0) for day in days)
        if planned != actual:
            raise ValueError(f"data/sample changed: ShopGoodwill has {actual} orders in {block['days']}, "
                             f"the buyer plan in kpi_samples.BLOCKS covers {planned}")
        for day in days:
            for m in ("shopgoodwill", "amazon", "ebay"):
                row = answers[day][m]
                if row["status"] != "ok":
                    pulse.append((day, m, row["status"], None, None, None, None))
                    continue
                pulse.append((day, m, "ok", row["sales_cents"], row["refunds_cents"], row["fees_cents"], row["orders"]))
                for i in range(row["orders"]):
                    order = f"{m}-{day}-{i}"
                    buyer = next(buyers) if m == "shopgoodwill" else f"eb-{day}-{i}" if m == "ebay" else ""
                    sales.append((day, m, order, buyer, 2 if i % 8 == 0 else 1))  # one order in eight has two units

        def every_day(metric, dimension, values):
            internal.extend((day, metric, dimension, value) for day, value in zip(days, values))

        def produced(metric, dimension, total, scale=1):
            """A block total spread over the working days, with an explicit 0 on Sundays (a real zero)."""
            share = dict(zip(working, _spread(total, len(working))))
            every_day(metric, dimension, [share.get(day, 0) / scale for day in days])

        produced("labor_hours", "total", round(block["labor_hours"] * 10), scale=10)
        produced("labor_cost_cents", "total", block["labor_cost_cents"])
        for m, count in block["listings"].items():
            produced("listings_created", m, count)
        for age, count in block["ages"].items():  # a day without listed items has no rows at all
            internal.extend((day, "donation_to_listing_days", str(age), n)
                            for day, n in zip(working, _spread(count, len(working))) if n)
        every_day("shipping_net_cost_cents", "total", _spread(block["shipping_net_cost_cents"], len(days)))
        for day in days:  # the listing system's view of the day's sales: units sold by days since listing
            sold = sum(units for d, _, _, _, units in sales if d == day)
            internal.extend((day, "listing_to_sale_days", str(age), n)
                            for (age, _), n in zip(SALE_AGES, _by_weight(sold, [w for _, w in SALE_AGES])) if n)
        every_day("employees", "total", [_employees(day) for day in days])
        internal.extend((day, "unlisted_backlog", "total", _backlog(day)) for day in days if day != NO_BACKLOG)
        for bucket, count in block["active"].items():
            every_day("active_listings_by_age", bucket, [count] * len(days))
        for category, share, cost in CATEGORIES:
            sold = round(block["internal_sales_cents"] * share)
            every_day("category_sales_cents", category, _spread(sold, len(days)))
            every_day("category_cogs_cents", category, _spread(round(sold * cost), len(days)))
    make_db(path, pulse, sales, internal)


def sample_docs(db):
    """{example file name: KPI file} computed from the sample database."""
    con = store.connect(db)
    try:
        return {name: cli.report(con, kind, text, generated_at=at) for name, kind, text, at in SAMPLES}
    finally:
        con.close()


def main(argv=None):
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Rewrite the contract examples, or write the sample database.")
    parser.add_argument("--db", type=Path, help="write the sample database here instead (to try recon.kpi on)")
    args = parser.parse_args(argv)
    if args.db:
        if args.db.exists():
            raise SystemExit(f"{args.db} already exists; not overwritten")
        args.db.parent.mkdir(parents=True, exist_ok=True)
        build_sample_db(args.db)
        print(f"wrote {args.db} (synthetic: September and October 1 to 4)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "ecom.db"
        build_sample_db(db)
        for name, doc in sample_docs(db).items():
            (EXAMPLES / name).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(f"wrote {EXAMPLES / name}")


if __name__ == "__main__":
    main()
