"""Simulated provider APIs: what a provider would email us, built from synthetic orders.

We have not seen any provider's API (Amanda: assume one exists, reports arrive as emailed Excel). A
simulator stands in for it: `python -m engine fetch --simulate` asks each provider's simulator for one
business day, and it drops the report it would have emailed into the inbox as an `.xlsx`. From there the
normal pipeline runs unchanged: parser, cleaning, dedupe, source status, pulse.

Assumption (decision 005 / docs/ASSUMPTIONS.md): Cash Monkey, Amazon and eBay all deliver in the Cash
Monkey report layout (header in row 1, one line per unit, a Channel column, UTC order dates), and each
simulator covers its own channel, so the four providers never overlap. Everything here is SYNTHETIC and
the data is the same for the same date (seeded by the date), so re-running a day rewrites the same files.
"""
import csv
import io
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import Workbook

from ..tools.make_sample import Order, eastern_day, make_orders, render_cashmonkey

PACIFIC = ZoneInfo("America/Los_Angeles")

# Orders per Eastern day, per marketplace (the same mix as the sample generator).
PER_DAY = {"shopgoodwill": 24, "ebay": 16, "amazon": 14, "other": 4}

# Columns of the Cash Monkey layout that hold numbers, written as real numbers in the Excel file.
_CM_NUMBERS = {"Quantity", "Item Price", "Shipping Price", "Net Revenue", "Marketplace Fees", "Shipping Cost", "Profit"}

UPRIGHT_HEADER = ["Upright Order ID", "Channel", "Channel Order ID", "Secondary Order ID", "Channel Buyer",
                  "Order Items", "Payment Date", "Payment Type", "Total", "Subtotal", "Shipping Charged",
                  "Shipping Discount", "Handling", "Tax Total", "Donation", "Currency", "Final Value Fee"]


def day_orders(business_date: str) -> tuple[list[Order], random.Random]:
    """The synthetic orders of one Eastern day. Deterministic: the same date always gives the same orders."""
    day = date.fromisoformat(business_date)
    rng = random.Random(int(day.strftime("%Y%m%d")))
    orders = make_orders(rng, [day], PER_DAY)
    # make_orders numbers ShopGoodwill orders from 1 on every call; a real provider never reuses a number on
    # another day, and the dedupe would (rightly) drop a second day as repeats. Give each date its own range.
    offset = (day - date(2026, 1, 1)).days * 1000
    for o in orders:
        if o.marketplace == "shopgoodwill":
            o.order_id = str(int(o.order_id) + offset)
            o.upright_id = str(int(o.upright_id) + offset)
    # Plant the boundary cases every day so the simulated data always exercises the timezone logic: Upright
    # stamps Pacific, so an order just after Eastern midnight is still the previous day on its own clock.
    # (An evening Eastern sale crossing UTC midnight is already common in the random data.)
    early = [o for o in orders if o.marketplace == "shopgoodwill"][:2]
    for o, (hour, minute) in zip(early, [(0, 30), (2, 45)]):
        o.placed = o.placed.replace(hour=hour, minute=minute, second=0)
    return orders, rng


def _write_xlsx(path: Path, header: list[str], rows: list[list]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(header)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def upright_rows(business_date: str) -> list[list]:
    """The rows of the simulated Upright "Paid orders" report for one Eastern day (columns: UPRIGHT_HEADER)."""
    orders, rng = day_orders(business_date)
    rows = []
    for o in (x for x in orders if x.marketplace == "shopgoodwill"):
        shipping = rng.choice([10.99, 14.99, 11.29, 9.99])
        handling = 2.0
        tax = round(o.subtotal / 100 * 0.06, 2)
        subtotal = o.subtotal / 100
        rows.append([int(o.upright_id), "Shopgoodwill", int(o.order_id), None, o.buyer, rng.choice([1, 1, 1, 2, 3]),
                     o.placed.astimezone(PACIFIC).replace(tzinfo=None), rng.choice(["ApplePay", "CreditCard", "PayPal"]),
                     round(subtotal + shipping + handling + tax, 2), subtotal, shipping, 0, handling, tax, 0, "USD", 0])
    rows.sort(key=lambda r: r[6])
    return rows


def simulate_upright(business_date: str, dest_dir: Path) -> list[Path]:
    """Upright "Paid orders": one row per order, `Payment Date` as a plain Pacific timestamp (the report
    form's default zone), saved the way the deck's title bar shows: paid_orders_<MM-DD-YYYY>_<MM-DD-YYYY>."""
    day = date.fromisoformat(business_date)
    rows = upright_rows(business_date)
    stamp = f"{day.month:02d}-{day.day:02d}-{day.year}"
    return [_write_xlsx(dest_dir / f"paid_orders_{stamp}_{stamp}.xlsx", UPRIGHT_HEADER, rows)]


def _cash_monkey_layout(business_date: str, dest: Path, channels: set[str]) -> list[Path]:
    """A report in the Cash Monkey layout limited to some marketplaces (one line per unit, UTC dates)."""
    day = date.fromisoformat(business_date)
    orders, rng = day_orders(business_date)
    # Eastern day D spans UTC dates D and D+1 (an evening sale is already tomorrow in UTC)
    text = render_cashmonkey(rng, orders, day, day + timedelta(days=1), faults=False, only=channels)
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    rows = []
    for raw in reader:
        if not raw:
            continue
        row = []
        for name, value in zip(header, raw):
            if name == "Order Date (UTC)":
                row.append(datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))
            elif name in _CM_NUMBERS:
                row.append(float(value))
            else:
                row.append(value)
        rows.append(row)
    return [_write_xlsx(dest, header, rows)]


def simulate_cashmonkey(business_date: str, dest_dir: Path) -> list[Path]:
    """Cash Monkey's own channel (Goodwillbooks, which becomes the `other` row). The file is named the way
    the deck shows (orders2023-<date>-<time>-<n>) and stamped just after midnight Eastern the next day."""
    day = date.fromisoformat(business_date)
    name = f"orders2023-{(day + timedelta(days=1)):%Y%m%d}-001500-96170.xlsx"
    return _cash_monkey_layout(business_date, dest_dir / name, {"other"})


def simulate_amazon(business_date: str, dest_dir: Path) -> list[Path]:
    return _cash_monkey_layout(business_date, dest_dir / f"amazon_orders_{business_date}.xlsx", {"amazon"})


def simulate_ebay(business_date: str, dest_dir: Path) -> list[Path]:
    return _cash_monkey_layout(business_date, dest_dir / f"ebay_orders_{business_date}.xlsx", {"ebay"})


def expected_for(business_date: str) -> dict:
    """The answer key for the simulated day, computed from the orders, not from the engine."""
    from ..tools.make_sample import truth

    orders, _ = day_orders(business_date)
    return {"business_date": business_date, "days": truth(orders, [date.fromisoformat(business_date)], {})}


__all__ = ["simulate_upright", "simulate_cashmonkey", "simulate_amazon", "simulate_ebay", "expected_for",
           "day_orders", "eastern_day"]
