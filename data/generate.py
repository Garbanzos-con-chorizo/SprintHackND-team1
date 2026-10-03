"""Generate synthetic marketplace exports for the nightly pulse (tasks O1, P-O1).

Everything here is invented. The eBay and Amazon layouts are modeled on their
public seller reports (eBay "Transaction report", Amazon "Date Range Report");
the ShopGoodwill layout is a guess. None are confirmed by Goodwill Michiana yet.

One synthetic world of orders (Sep 1 - Oct 4, 2026) is generated from a fixed
seed, then each scenario exports a slice of it the way staff would download it.
Each scenario also gets an `expected.json` answer key computed from exactly the
rows in its inbox, so parsers and the pulse can be tested against it.

    python data/generate.py          # rewrites data/sample/
"""
import csv
import io
import json
import random
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import log
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import Workbook

ET = ZoneInfo("America/New_York")  # business day (contract default)
PT = ZoneInfo("America/Los_Angeles")  # Amazon reports use Pacific time
SEED = 20261003
WORLD_START, WORLD_END = date(2026, 9, 1), date(2026, 10, 4)
OUT = Path(__file__).parent / "sample"
SOURCES = ["shopgoodwill", "ebay", "amazon"]

DAILY_MEAN = {"shopgoodwill": 38, "ebay": 24, "amazon": 14}
WEEKDAY_FACTOR = [0.9, 0.95, 1.0, 1.0, 1.05, 1.15, 1.25]  # Mon..Sun
# Hour-of-day weights (ET). Some late-night orders so day boundaries matter.
HOUR_WEIGHTS = [3, 2, 1, 1, 1, 1, 2, 3, 4, 5, 6, 6, 7, 7, 6, 6, 6, 7, 8, 9, 10, 10, 8, 5]
# (source, ET date issued) -> one full refund of an order placed 1-3 days earlier.
REFUNDS = [("ebay", date(2026, 9, 12)), ("amazon", date(2026, 9, 19)),
           ("ebay", date(2026, 9, 25)), ("ebay", date(2026, 10, 2)),
           ("amazon", date(2026, 10, 2))]

SG_ITEMS = [("Vintage Pyrex Mixing Bowl Set", "Kitchen"), ("Sterling Silver Charm Bracelet", "Jewelry"),
            ("Lot of 12 Hot Wheels Cars", "Toys"), ("Nikon D3100 Camera Body", "Electronics"),
            ("Pendleton Wool Blanket", "Home"), ("Coach Leather Handbag", "Fashion"),
            ("Lionel Train Set (Incomplete)", "Toys"), ("Gold Tone Costume Jewelry Lot 2 lb", "Jewelry"),
            ("Fiesta Ware Dinner Plates (4)", "Kitchen"), ("Vinyl Record Lot - Classic Rock (20)", "Media"),
            ("Brass Candlestick Pair", "Home"), ("Apple iPad 6th Gen 32GB", "Electronics")]
EBAY_ITEMS = ["Levi's 501 Jeans 34x32", "Patagonia Fleece Jacket M", "Nintendo DS Lite Pink",
              "Corningware Blue Cornflower Casserole", "LEGO Star Wars Minifigure Lot",
              "Nike Air Max Size 10", "Vera Bradley Tote", "Carhartt Work Jacket L",
              "Polaroid OneStep Camera", "Longaberger Basket with Liner"]
AMAZON_BOOKS = ["The Great Gatsby (Paperback)", "Where the Crawdads Sing", "Atomic Habits",
                "Harry Potter and the Sorcerer's Stone", "The Joy of Cooking (1997)",
                "Educated: A Memoir", "Calculus: Early Transcendentals 8th Ed",
                "The Very Hungry Caterpillar (Board Book)", "Becoming", "The Hobbit"]
STATES = ["IN", "MI", "OH", "IL", "TX", "CA", "NY", "FL", "PA", "WI"]
WORDS_A = ["blue", "lucky", "happy", "quiet", "retro", "swift", "golden", "rusty", "sunny", "north"]
WORDS_B = ["fox", "finds", "picker", "thrift", "owl", "deals", "maple", "river", "bear", "hound"]


@dataclass
class Item:
    sku: str
    title: str
    category: str
    price_cents: int
    fee_cents: int


@dataclass
class Order:
    source: str
    order_id: str
    placed: datetime  # aware, ET
    buyer: str | None
    items: list[Item]
    shipping_cents: int
    tax_cents: int
    state: str
    sg_item_no: str = ""

    @property
    def subtotal(self):
        return sum(i.price_cents for i in self.items)

    @property
    def fee(self):
        return sum(i.fee_cents for i in self.items)


@dataclass
class Refund:
    order: Order
    issued: datetime  # aware, ET

    @property
    def source(self):
        return self.order.source


def when(ev):
    return ev.issued if isinstance(ev, Refund) else ev.placed


# ---------------------------------------------------------------- world

def build_world(rng):
    pools = {s: [f"{rng.choice(WORDS_A)}{rng.choice(WORDS_B)}{rng.randint(1, 999)}"
                 for _ in range(n)] for s, n in (("shopgoodwill", 300), ("ebay", 900))}
    used, orders = set(), []
    sg_no = 883000

    def uid(make):
        while (v := make()) in used:
            pass
        used.add(v)
        return v

    day = WORLD_START
    while day <= WORLD_END:
        for src in SOURCES:
            mean = DAILY_MEAN[src] * WEEKDAY_FACTOR[day.weekday()]
            for _ in range(max(1, round(rng.gauss(mean, mean * 0.2)))):
                hour = rng.choices(range(24), HOUR_WEIGHTS)[0]
                placed = datetime(day.year, day.month, day.day, hour,
                                  rng.randint(0, 59), rng.randint(0, 59), tzinfo=ET)
                state = rng.choice(STATES)
                if src == "shopgoodwill":
                    sg_no += rng.randint(1, 4)
                    title, cat = rng.choice(SG_ITEMS)
                    price = max(5, round(rng.lognormvariate(log(25), 0.7))) * 100
                    orders.append(Order(src, f"SG-{sg_no}", placed, rng.choice(pools[src]),
                                        [Item("", title, cat, price, 0)],
                                        rng.choice([899, 1099, 1299, 1499]), 0, state,
                                        sg_item_no=str(uid(lambda: rng.randint(200_000_000, 299_999_999)))))
                elif src == "ebay":
                    price = max(4, round(rng.lognormvariate(log(22), 0.6))) * 100 - 1
                    ship = rng.choice([0, 0, 599])
                    fee = 30 + round(0.1325 * (price + ship))
                    oid = uid(lambda: f"{rng.randint(10, 27)}-{rng.randint(10000, 99999)}-{rng.randint(10000, 99999)}")
                    orders.append(Order(src, oid, placed, rng.choice(pools[src]),
                                        [Item(f"EB-{rng.randint(1000, 9999)}", rng.choice(EBAY_ITEMS), "", price, fee)],
                                        ship, round(price * 0.07), state))
                else:
                    items = []
                    for _ in range(2 if rng.random() < 0.12 else 1):
                        price = rng.randint(4, 34) * 100 + rng.choice([49, 99])
                        items.append(Item(f"BK-{rng.randint(1, 4999):04d}", rng.choice(AMAZON_BOOKS), "",
                                          price, round(0.15 * (price + 399)) + 180))
                    oid = uid(lambda: f"{rng.randint(111, 114)}-{rng.randint(1000000, 9999999)}-{rng.randint(1000000, 9999999)}")
                    orders.append(Order(src, oid, placed, None, items, 399 * len(items),
                                        round(sum(i.price_cents for i in items) * 0.07), state))
        day += timedelta(days=1)

    refunds = []
    for src, d in REFUNDS:
        candidates = [o for o in orders if o.source == src
                      and 1 <= (d - o.placed.date()).days <= 3 and not any(r.order is o for r in refunds)]
        o = rng.choice(candidates)
        refunds.append(Refund(o, datetime(d.year, d.month, d.day, rng.randint(10, 16), rng.randint(0, 59), 0, tzinfo=ET)))
    return orders, refunds


def window(events, source, start, end, tz):
    """Events a staff download for [start, end] in the report's own timezone would contain."""
    return sorted((e for e in events if e.source == source and start <= when(e).astimezone(tz).date() <= end),
                  key=when)


# ---------------------------------------------------------------- formats

def money(cents, commas=False):
    s = f"{abs(cents) / 100:,.2f}" if commas else f"{abs(cents) / 100:.2f}"
    return ("-" if cents < 0 else "") + s


def us_date(d):
    return f"{d:%b} {d.day}, {d.year}"


def clock(dt):
    return f"{dt.hour % 12 or 12}:{dt:%M:%S} {'AM' if dt.hour < 12 else 'PM'}"


def write_ebay(path, events, start, end, rng):
    cols = ["Transaction creation date", "Type", "Order number", "Legacy order ID", "Buyer username",
            "Item ID", "Item title", "Custom label", "Quantity", "Item subtotal", "Shipping and handling",
            "Seller collected tax", "eBay collected tax", "Final Value Fee - fixed",
            "Final Value Fee - variable", "Gross transaction amount", "Net amount", "Payout currency",
            "Description"]
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    w.writerow(["Transaction report"])
    w.writerow([f"Date range: {us_date(start)} - {us_date(end)}"])
    w.writerow(["All amounts in USD"])
    w.writerow([])
    w.writerow(cols)
    for e in events:
        o, it = e.order if isinstance(e, Refund) else e, (e.order if isinstance(e, Refund) else e).items[0]
        per_order = random.Random(o.order_id)  # same order -> same legacy id in every download
        legacy = f"{per_order.randint(100000000000, 399999999999)}-{per_order.randint(1000000000000, 2999999999999)}"
        if isinstance(e, Refund):
            w.writerow([us_date(e.issued.date()), "Refund", o.order_id, legacy, o.buyer, it.sku[3:], it.title,
                        it.sku, "1", money(-o.subtotal), money(-o.shipping_cents), "--", money(-o.tax_cents),
                        "--", "--", money(-(o.subtotal + o.shipping_cents + o.tax_cents)),
                        money(-(o.subtotal + o.shipping_cents)), "USD", "Buyer return: item not as described"])
        else:
            w.writerow([us_date(o.placed.date()), "Order", o.order_id, legacy, o.buyer, it.sku[3:], it.title,
                        it.sku, "1", money(o.subtotal), money(o.shipping_cents), "--", money(o.tax_cents),
                        "-0.30", money(-(o.fee - 30)), money(o.subtotal + o.shipping_cents + o.tax_cents),
                        money(o.subtotal + o.shipping_cents - o.fee), "USD", "--"])
    # eBay pays out daily; payout rows are not sales and must be skipped by the parser.
    d = start
    while d <= end:
        w.writerow([us_date(d), "Payout", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--",
                    "--", "--", "--", money(-rng.randint(30000, 90000)), "USD", "Payout to bank ending 4417"])
        d += timedelta(days=1)
    path.write_text(buf.getvalue(), encoding="utf-8-sig", newline="")
    return events


def write_amazon(path, events, start, end, rng, dup_row=False):
    cols = ["date/time", "settlement id", "type", "order id", "sku", "description", "quantity",
            "marketplace", "fulfillment", "order state", "product sales", "product sales tax",
            "shipping credits", "promotional rebates", "marketplace withheld tax", "selling fees",
            "fba fees", "other transaction fees", "other", "total"]
    rows = []
    for e in events:
        o = e.order if isinstance(e, Refund) else e
        sign = -1 if isinstance(e, Refund) else 1
        t = when(e).astimezone(PT)
        stamp = f"{us_date(t.date())} {clock(t)} {t.tzname()}"
        for it in o.items:
            tax = round(it.price_cents * 0.07)
            fee = 0 if sign < 0 else -it.fee_cents  # simplification: no fee reimbursement on refunds
            total = sign * (it.price_cents + 399) + fee
            rows.append([stamp, "11843920571", "Refund" if sign < 0 else "Order", o.order_id, it.sku, it.title,
                         "1", "amazon.com", "Seller", o.state, money(sign * it.price_cents, True),
                         money(sign * tax, True), money(sign * 399, True), "0", money(-sign * tax, True),
                         money(fee, True), "0", "0", "0", money(total, True)])
    t = datetime(end.year, end.month, end.day, 9, 12, 44, tzinfo=PT)
    transfer = money(-rng.randint(100000, 300000), True)  # payout to bank: not a sale, parser must skip
    rows.append([f"{us_date(end)} {clock(t)} {t.tzname()}", "11843920571", "Transfer", "", "", "To account ending in: 4417",
                 "", "", "", "", "0", "0", "0", "0", "0", "0", "0", "0", transfer, transfer])
    if dup_row:
        sales = [i for i, r in enumerate(rows) if r[2] == "Order"]
        i = sales[len(sales) // 2]
        rows.insert(i + 1, list(rows[i]))  # same line pasted twice: a true duplicate
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(["Includes Amazon Marketplace, Fulfillment by Amazon (FBA), and Amazon Webstore transactions"])
    w.writerow(["All amounts in USD, unless specified"])
    w.writerow(["Definitions:"])
    w.writerow(["Sales tax collected: Includes sales tax collected from buyers for product sales, shipping, and gift wrap."])
    w.writerow(["Selling fees: Includes variable closing fees and referral fees."])
    w.writerow([f"Date range: {us_date(start)} 12:00:00 AM PDT - {us_date(end)} 11:59:59 PM PDT"])
    w.writerow([])
    w.writerow(cols)
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")
    return events


def save_xlsx(wb, path):
    """Save with pinned timestamps so reruns give byte-identical files."""
    fixed = datetime(2026, 10, 3, 6, 0, 0)
    wb.properties.created = wb.properties.modified = fixed
    wb.properties.creator = "synthetic"
    buf = io.BytesIO()
    wb.save(buf)
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as src, zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":  # openpyxl overwrites "modified" with now() on save
                data = re.sub(rb"(<dcterms:modified[^>]*>)[^<]*", rb"\g<1>2026-10-03T06:00:00Z", data)
            dst.writestr(zipfile.ZipInfo(info.filename, fixed.timetuple()[:6]), data,
                         compress_type=zipfile.ZIP_DEFLATED)


def write_shopgoodwill(path, events, generated, rng):
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(["ShopGoodwill.com - Seller Order Export"])
    ws.append([f"Generated: {generated.month}/{generated.day}/{generated.year} {clock(generated)[:-6]}{clock(generated)[-3:]}"])
    ws.append([])
    ws.append(["Order #", "Item #", "Item Title", "Category", "Buyer", "Close Date", "Winning Bid",
               "Shipping", "Handling Fee", "Order Total", "Payment Status", "Shipped"])
    for n, o in enumerate(events):
        it = o.items[0]
        naive = o.placed.replace(tzinfo=None)
        # Mostly real Excel dates; some rows were typed or pasted as text.
        close = naive if rng.random() > 0.12 else \
            f"{naive.month}/{naive.day}/{naive:%y} {naive.hour % 12 or 12}:{naive:%M} {'AM' if naive.hour < 12 else 'PM'}"
        bid = it.price_cents / 100 if n % 17 != 5 else f"${it.price_cents / 100:,.2f}"
        ws.append([o.order_id, o.sg_item_no, it.title, it.category, o.buyer, close, bid,
                   o.shipping_cents / 100, 2.0, (it.price_cents + o.shipping_cents + 200) / 100, "Paid",
                   "Y" if (generated.date() - o.placed.date()).days >= 2 else "N"])
        row = ws.max_row
        if isinstance(close, datetime):
            ws.cell(row, 6).number_format = "m/d/yyyy h:mm AM/PM"
        for c in (7, 8, 9, 10):
            ws.cell(row, c).number_format = '"$"#,##0.00'
    save_xlsx(wb, path)
    return events


# ---------------------------------------------------------------- Goodwill's real report tools
# Layouts from docs/contracts/source-formats.md (read off the SprintHack deck). Upright columns are
# the ones visible in the slide 26 screenshot; names marked GUESS were truncated or not shown.
# Cash Monkey's columns are never shown in the deck: every one of them is a GUESS.
UTC = ZoneInfo("UTC")
UPRIGHT_COLS = ["Upright Order ID", "Channel", "Channel Order ID", "Secondary Order ID",  # GUESS: truncated
                "Channel Buyer", "Order Items", "Payment Date",  # GUESS: truncated "Payment ..."
                "Payment Type", "Total", "Subtotal", "Shipping Charged", "Shipping Discount",  # GUESS
                "Handling", "Tax Total", "Donation", "Currency", "Final Value Fee"]
CASHMONKEY_COLS = ["Order Date", "Account", "Channel", "Order ID", "SKU", "Title", "Quantity",  # all GUESS
                   "Item Price", "Shipping", "Market Fees", "Net Revenue", "Cost", "Profit", "Currency"]
CM_CHANNEL = {"ebay": "eBay", "amazon": "Amazon-MF"}


def asof_window(events, sources, start, end, tz, asof):
    """Orders a report run at `asof` for report-timezone dates [start, end] would contain (no refunds)."""
    return sorted((e for e in events if isinstance(e, Order) and e.source in sources
                   and start <= e.placed.astimezone(tz).date() <= end and e.placed <= asof), key=when)


def write_upright(path, orders):
    """Upright "Paid orders": one row per order, header in row 1, times in the report's zone (Pacific)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(UPRIGHT_COLS)
    for o in orders:
        r = random.Random(o.order_id)  # same order -> same values in every download
        handling, tax = 300, round(o.subtotal * 0.07)
        ws.append([24224000 + int(o.order_id[3:]) % 100000, "Shopgoodwill", int(o.order_id[3:]), None,
                   o.buyer, len(o.items), o.placed.astimezone(PT).replace(tzinfo=None),
                   r.choice(["CreditCard", "CreditCard", "PayPal", "ApplePay"]),
                   (o.subtotal + o.shipping_cents + handling + tax) / 100, o.subtotal / 100,
                   o.shipping_cents / 100, 0.0, handling / 100, tax / 100, 0.0, "USD", 0.0])
        ws.cell(ws.max_row, 7).number_format = "m/d/yyyy h:mm:ss AM/PM"
        for c in (9, 10, 11, 12, 13, 14, 15, 17):
            ws.cell(ws.max_row, c).number_format = "0.00"
    save_xlsx(wb, path)
    return orders


def write_cashmonkey(path, orders):
    """Cash Monkey "Orders Report": one line per unit, fees and shipping pro-rated per unit, UTC dates."""
    wb = Workbook()
    ws = wb.active
    ws.title = "orders"
    ws.append(CASHMONKEY_COLS)
    for o in orders:
        ship_each = o.shipping_cents // len(o.items)
        for it in o.items:
            ws.append([o.placed.astimezone(UTC).replace(tzinfo=None), "276 - Goodwill Michiana",
                       CM_CHANNEL[o.source], o.order_id, it.sku, it.title, 1, it.price_cents / 100,
                       ship_each / 100, it.fee_cents / 100, (it.price_cents + ship_each - it.fee_cents) / 100,
                       None, None, "USD"])  # cost and profit: "where available", not for donated goods
            ws.cell(ws.max_row, 1).number_format = "yyyy-mm-dd hh:mm:ss"
    save_xlsx(wb, path)
    return orders


# ---------------------------------------------------------------- answer key

def expected(scenario, exported, business_date, dates, basis=None):
    """What a correct pipeline should report, computed from exactly the rows exported."""
    days = {}
    for d in dates:
        day, total = {}, {"sales_cents": 0, "refunds_cents": 0, "revenue_cents": 0, "fees_cents": 0,
                          "orders": 0, "customers": 0}
        for src in SOURCES:
            if src not in exported:
                day[src] = {"status": "missing"}
                continue
            by_order = (basis or {}).get(src, "order" if src == "amazon" else "buyer") == "order"
            sales_ids, cust, m = set(), set(), {"sales_cents": 0, "refunds_cents": 0, "fees_cents": 0}
            for e in exported[src]:
                if when(e).date() != d:  # business day = ET date
                    continue
                if isinstance(e, Refund):
                    m["refunds_cents"] -= e.order.subtotal
                else:
                    m["sales_cents"] += e.subtotal
                    m["fees_cents"] += e.fee
                    sales_ids.add(e.order_id)
                    cust.add(e.order_id if by_order else e.buyer or e.order_id)
            rows = m["sales_cents"] or m["refunds_cents"] or sales_ids
            day[src] = {"status": "ok" if rows else "stale", **m,
                        "revenue_cents": m["sales_cents"] + m["refunds_cents"], "orders": len(sales_ids),
                        "customers": len(cust), "customer_basis": "order" if by_order else "buyer"}
            for k in total:
                total[k] += day[src][k]
        day["enterprise"] = total
        days[d.isoformat()] = day
    return {
        "scenario": scenario,
        "business_date": business_date and business_date.isoformat(),
        "definitions": {
            "business_date": "order (or refund) timestamp converted to America/New_York, date part",
            "revenue_cents": "item subtotal of sales minus refunds; excludes shipping, tax and fees",
            "fees_cents": "marketplace fees on sales, reported separately (refunds carry no fee in this data)",
            "orders": "distinct order ids among sales",
            "customers": "distinct buyer usernames; Amazon has no buyer id so it counts orders",
            "enterprise.customers": "sum of per-marketplace counts (buyers can't be matched across marketplaces)",
            "status": "ok = rows for that day, stale = file present but no rows that day, missing = no file",
        },
        "days": days,
    }


# ---------------------------------------------------------------- scenarios

def scenario(name, start, end, business_date, rng, events, skip=(), ebay_redownload=None,
             amazon_dup_row=False, note=""):
    inbox = OUT / name / "inbox"
    inbox.mkdir(parents=True)
    tag = business_date.isoformat() if business_date else f"{start:%Y-%m}"
    generated = datetime.combine(end + timedelta(days=1), datetime.min.time()).replace(hour=6, minute=5)
    exported = {}
    if "shopgoodwill" not in skip:
        exported["shopgoodwill"] = write_shopgoodwill(
            inbox / f"ShopGoodwill_Orders_{tag}.xlsx",
            [e for e in window(events, "shopgoodwill", start, end, ET) if isinstance(e, Order)], generated, rng)
    if "ebay" not in skip:
        exported["ebay"] = write_ebay(inbox / f"ebay_transactions_{tag}.csv",
                                      window(events, "ebay", start, end, ET), start, end, rng)
        if ebay_redownload:
            s2, e2 = ebay_redownload
            again = write_ebay(inbox / f"ebay_transactions_{tag} (1).csv",
                               window(events, "ebay", s2, e2, ET), s2, e2, rng)
            exported["ebay"] = sorted({id(e): e for e in exported["ebay"] + again}.values(), key=when)
    if "amazon" not in skip:
        exported["amazon"] = write_amazon(inbox / f"amazon_daterange_{tag}.csv",
                                          window(events, "amazon", start, end, PT), start, end, rng,
                                          dup_row=amazon_dup_row)
    dates = sorted({when(e).date() for evs in exported.values() for e in evs})
    if business_date:
        dates = [business_date - timedelta(days=1), business_date]
    key = expected(name, exported, business_date, dates)
    key["mess"] = note
    (OUT / name / "expected.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return key


def goodwill_scenario(name, business_date, events, skip=(), upright_twice=False, note=""):
    """Nightly inbox as Goodwill receives it: Upright (ShopGoodwill) + Cash Monkey (eBay, Amazon), .xlsx.

    Reports are pulled at 00:15 Eastern, after e-commerce closes (9 PM Pacific). Upright is filtered by
    Pacific dates, Cash Monkey by UTC dates; both ranges are wide enough to cover the two Eastern days.
    """
    d = business_date
    asof = datetime(d.year, d.month, d.day, tzinfo=ET) + timedelta(days=1, minutes=15)
    inbox = OUT / name / "inbox"
    inbox.mkdir(parents=True)
    exported = {}
    if "upright" not in skip:
        s, e = d - timedelta(days=2), d
        fname = f"paid_orders_{s:%m-%d-%Y}_{e:%m-%d-%Y}"
        orders = write_upright(inbox / f"{fname}.xlsx", asof_window(events, {"shopgoodwill"}, s, e, PT, asof))
        if upright_twice:  # the deck's title bar shows "paid_orders_... (4)": the same report saved again
            write_upright(inbox / f"{fname} (4).xlsx", orders)
        exported["shopgoodwill"] = orders
    if "cashmonkey" not in skip:
        orders = write_cashmonkey(inbox / f"orders2023-{asof:%Y%m%d}-001512-96170.xlsx",
                                  asof_window(events, {"ebay", "amazon"}, d - timedelta(days=1), d + timedelta(days=1), UTC, asof))
        exported["ebay"] = [o for o in orders if o.source == "ebay"]
        exported["amazon"] = [o for o in orders if o.source == "amazon"]
    # Staff count Upright rows (orders); Cash Monkey shows no buyer column, so orders there too.
    key = expected(name, exported, d, [d - timedelta(days=1), d],
                   basis={"shopgoodwill": "order", "ebay": "order", "amazon": "order"})
    key["mess"] = note
    key["formats"] = "Upright Paid orders (.xlsx, Pacific, one row per order) and Cash Monkey Orders Report " \
                     "(.xlsx, UTC, one line per unit); see data/README.md"
    (OUT / name / "expected.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return key


def main():
    rng = random.Random(SEED)
    orders, refunds = build_world(rng)
    events = orders + refunds
    for old in OUT.glob("*/"):  # keep data/sample/.gitattributes
        shutil.rmtree(old)
    d = date
    keys = [
        scenario("clean_month", d(2026, 9, 1), d(2026, 9, 30), None, rng, events,
                 note="Clean month: one export per source for September. Format quirks only (preambles, BOM, "
                      "Pacific-time Amazon stamps, text dates in ShopGoodwill). 3 refunds. 23 Amazon rows are stamped "
                      "late evening PDT but belong to the next ET business day."),
        scenario("day_clean", d(2026, 9, 30), d(2026, 10, 1), d(2026, 10, 1), rng, events,
                 note="Normal nightly download covering yesterday and today. No refunds."),
        scenario("day_refund", d(2026, 10, 1), d(2026, 10, 2), d(2026, 10, 2), rng, events,
                 note="One eBay refund (order from Oct 1) and one Amazon refund (order from Sep 30) issued Oct 2. "
                      "The Amazon refund's original sale is outside this inbox."),
        scenario("day_ebay_missing", d(2026, 10, 2), d(2026, 10, 3), d(2026, 10, 3), rng, events,
                 skip={"ebay"}, note="No eBay file. eBay must show as missing (no data), never $0."),
        scenario("day_duplicates", d(2026, 10, 3), d(2026, 10, 4), d(2026, 10, 4), rng, events,
                 ebay_redownload=(d(2026, 10, 2), d(2026, 10, 4)), amazon_dup_row=True,
                 note="eBay downloaded twice with overlapping ranges (second file 'ebay_transactions_2026-10-04 (1).csv'"
                      " covers Oct 2-4). One Amazon line pasted twice. Amazon also has multi-item orders "
                      "(several rows, same order id) that are NOT duplicates."),
    ]
    keys += [
        goodwill_scenario("gw_day_clean", d(2026, 10, 1), events,
                          note="Goodwill's two nightly files: Upright (ShopGoodwill) and Cash Monkey (eBay, Amazon). "
                               "Plain timestamps: Upright in Pacific, Cash Monkey in UTC."),
        goodwill_scenario("gw_day_cashmonkey_missing", d(2026, 10, 3), events, skip={"cashmonkey"},
                          note="No Cash Monkey file: eBay and Amazon must both show as missing, never $0."),
        goodwill_scenario("gw_day_duplicates", d(2026, 10, 4), events, upright_twice=True,
                          note="The Upright report saved twice ('... (4).xlsx'): every ShopGoodwill order appears twice. "
                               "Cash Monkey multi-unit orders repeat the order id on purpose and are NOT duplicates."),
    ]
    for k in keys:
        bd = k["business_date"]
        if bd:
            ent = k["days"][bd]["enterprise"]
            print(f"{k['scenario']:<18} {bd}  revenue ${ent['revenue_cents'] / 100:>9,.2f}  orders {ent['orders']:>3}")
        else:
            print(f"{k['scenario']:<18} {len(k['days'])} days")


if __name__ == "__main__":
    main()
