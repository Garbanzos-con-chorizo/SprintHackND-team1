"""Generate synthetic exports shaped like the real ones, plus an answer key, and check the pipeline.

    python -m engine.tools.make_sample --scenario messy_day --check
    python -m engine.tools.make_sample --scenario clean_day --out some/dir --seed 7

Why this exists: we have no real Goodwill files yet. This builds a ground truth of orders first, then
renders it into the formats the deck shows (docs/contracts/source-formats.md), so the expected numbers
come from the truth and not from the engine. `--check` runs the files through the real pipeline and
compares. Everything here is SYNTHETIC. Anything in those formats marked "guess" there is a guess here too.

Scenarios
  clean_day  two Eastern days (D-1 and D), all sources present, no faults.
  messy_day  the same, plus: a re-downloaded duplicate file, refunds, a missing Upright file for D,
             rows of another Upright channel, UTC rows that cross the Eastern midnight, a bad amount,
             a bad date and a blank line.
"""
import argparse
import csv
import io
import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
UTC = timezone.utc


# --- the ground truth ---------------------------------------------------------------------------

@dataclass
class Order:
    marketplace: str            # shopgoodwill | ebay | amazon | other (Goodwillbooks)
    order_id: str
    buyer: str                  # "" when the source exposes none
    placed: datetime            # Eastern, timezone-aware
    unit_cents: int             # merchandise price of one unit
    units: int
    fee_unit_cents: int         # marketplace fee per unit (pro-rated, as Cash Monkey does)
    upright_id: str = ""
    refunded_at: datetime | None = None

    @property
    def subtotal(self) -> int:
        return self.unit_cents * self.units

    @property
    def fee(self) -> int:
        return self.fee_unit_cents * self.units


def _money(cents: int) -> str:
    return f"{cents / 100:.2f}"


def make_orders(rng: random.Random, days: list[date], per_day: dict[str, int]) -> list[Order]:
    names = ["happy", "swift", "quiet", "lucky", "rusty", "sunny", "blue", "retro", "bright", "calm"]
    things = ["owl", "fox", "bear", "hound", "picker", "finds", "thrift", "deals", "cat", "wolf"]
    out: list[Order] = []
    seq = 0
    for day in days:
        for mk, n in per_day.items():
            for _ in range(n):
                seq += 1
                # spread across the Eastern day, with an evening bump (those cross UTC midnight)
                hour = rng.choice([rng.randint(0, 23), rng.randint(0, 23), rng.randint(20, 23)])
                placed = datetime.combine(day, time(hour, rng.randint(0, 59), rng.randint(0, 59)), tzinfo=EASTERN)
                units = rng.choice([1, 1, 1, 2, 3]) if mk != "shopgoodwill" else 1
                if mk == "shopgoodwill":
                    unit = rng.randint(500, 15000)
                    fee_unit = 0
                    buyer = f"{rng.choice(names)}{rng.choice(things)}{rng.randint(10, 999)}"
                    oid = str(65700000 + seq)
                elif mk == "ebay":
                    unit = rng.randint(800, 6000)
                    fee_unit = round(unit * 0.1325) + 30
                    buyer = ""  # Cash Monkey exposes no buyer id (assumption): customers = orders
                    oid = f"{rng.randint(10, 29)}-{rng.randint(10000, 99999)}-{rng.randint(10000, 99999)}"
                elif mk == "amazon":
                    unit = rng.randint(700, 4500)
                    fee_unit = round(unit * 0.15)
                    buyer = ""
                    oid = f"11{rng.randint(1, 4)}-{rng.randint(1000000, 9999999)}-{rng.randint(1000000, 9999999)}"
                else:
                    unit = rng.randint(400, 2500)
                    fee_unit = round(unit * 0.15)
                    buyer = ""
                    oid = f"GB-{rng.randint(10000, 99999)}"
                out.append(Order(mk, oid, buyer, placed, unit, units, fee_unit, upright_id=str(24220000 + seq)))
    return out


def eastern_day(dt: datetime) -> str:
    return dt.astimezone(EASTERN).date().isoformat()


def truth(orders: list[Order], days: list[date], missing: set[tuple[str, str]]) -> dict:
    """Expected numbers per Eastern day and marketplace, straight from the orders."""
    buckets: dict[tuple[str, str], dict] = defaultdict(lambda: dict(
        sales_cents=0, refunds_cents=0, fees_cents=0, orders=set(), customers=set()))
    for o in orders:
        b = buckets[(eastern_day(o.placed), o.marketplace)]
        b["sales_cents"] += o.subtotal
        b["fees_cents"] += o.fee
        b["orders"].add(o.order_id)
        b["customers"].add(o.buyer or f"order:{o.order_id}")
        if o.refunded_at:
            buckets[(eastern_day(o.refunded_at), o.marketplace)]["refunds_cents"] -= o.subtotal
    result: dict[str, dict] = {}
    for d in days:
        iso = d.isoformat()
        result[iso] = {}
        for mk in ("shopgoodwill", "ebay", "amazon", "other"):
            if (iso, mk) in missing:
                result[iso][mk] = {"status": "missing"}
                continue
            b = buckets.get((iso, mk))
            if b is None:
                continue
            result[iso][mk] = {"status": "ok", "sales_cents": b["sales_cents"], "refunds_cents": b["refunds_cents"],
                               "fees_cents": b["fees_cents"], "orders": len(b["orders"]),
                               "customers": len(b["customers"])}
    return result


# --- rendering to the real-looking formats -------------------------------------------------------

UPRIGHT_HEADER = ["Upright Order ID", "Channel", "Channel Order ID", "Secondary Channel Order ID", "Channel Buyer",
                  "Order Items", "Payment ID", "Payment Type", "Total", "Subtotal", "Shipping Charged",
                  "Shipping Cost", "Handling", "Tax Total", "Donation", "Currency", "Final Value Fee", "Payment Fee"]

CM_HEADER = ["Order ID", "Line ID", "Order Date (UTC)", "Account", "Channel", "SKU", "Title", "Quantity", "Item Price",
             "Shipping Price", "Net Revenue", "Marketplace Fees", "Shipping Cost", "Profit", "Currency"]
CM_CHANNEL = {"ebay": "eBay", "amazon": "Amazon-MF", "other": "Goodwillbooks"}


def _csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def render_upright(rng: random.Random, orders: list[Order], day: date, noise_rows: bool) -> str:
    rows = []
    for o in (x for x in orders if x.marketplace == "shopgoodwill" and eastern_day(x.placed) == day.isoformat()):
        shipping, handling = rng.choice([1099, 1499, 1129, 999]), 200
        tax = round(o.subtotal * 0.06)
        rows.append([o.upright_id, "Shopgoodwill", o.order_id, "", o.buyer, rng.choice([1, 1, 1, 2, 3, 10]),
                     rng.randint(10 ** 7, 10 ** 8), rng.choice(["ApplePay", "CreditCard", "PayPal"]),
                     _money(o.subtotal + shipping + handling + tax), _money(o.subtotal), _money(shipping),
                     _money(shipping - 100), _money(handling), _money(tax), "0", "USD", "0",
                     _money(round(o.subtotal * 0.029))])
    if noise_rows:  # another channel in the same export: must be ignored, not counted twice
        for i in range(3):
            rows.append([str(24299000 + i), "Goodwillfinds", str(80000 + i), "", f"finder{i}", 1, 5000 + i,
                         "CreditCard", "21.00", "15.00", "4.00", "3.00", "2.00", "0.00", "0", "USD", "0", "0.50"])
    return _csv(UPRIGHT_HEADER, rows)


def render_cashmonkey(rng: random.Random, orders: list[Order], utc_from: date, utc_to: date, faults: bool) -> str:
    rows: list[list] = []
    n = 0
    for o in orders:
        if o.marketplace == "shopgoodwill":
            continue
        for _ in range(o.units):  # one line per unit
            n += 1
            when = o.placed.astimezone(UTC)
            if utc_from <= when.date() <= utc_to:
                rows.append([o.order_id, f"L{o.order_id}-{n}", when.strftime("%Y-%m-%d %H:%M:%S"),
                             "276 - Goodwill Michiana", CM_CHANNEL[o.marketplace], f"SKU-{rng.randint(1000, 9999)}",
                             "Synthetic item", 1, _money(o.unit_cents), "0.00",
                             _money(o.unit_cents - o.fee_unit_cents), _money(o.fee_unit_cents), "0.00",
                             _money(o.unit_cents - o.fee_unit_cents), "USD"])
        if o.refunded_at:
            when = o.refunded_at.astimezone(UTC)
            if utc_from <= when.date() <= utc_to:
                n += 1
                rows.append([o.order_id, f"R{o.order_id}-{n}", when.strftime("%Y-%m-%d %H:%M:%S"),
                             "276 - Goodwill Michiana", CM_CHANNEL[o.marketplace], "SKU-REFUND", "Refund", 1,
                             _money(-o.subtotal), "0.00", _money(-o.subtotal), "0.00", "0.00", _money(-o.subtotal),
                             "USD"])
    if faults:
        rows.insert(3, ["BAD-1", "Lx1", "2026-10-02 12:00:00", "276 - Goodwill Michiana", "eBay", "S", "t", 1, "n/a",
                        "0.00", "0", "0", "0", "0", "USD"])
        rows.insert(7, ["BAD-2", "Lx2", "not a date", "276 - Goodwill Michiana", "Amazon-MF", "S", "t", 1, "10.00",
                        "0.00", "0", "0", "0", "0", "USD"])
        rows.insert(11, [])  # blank line
    return _csv(CM_HEADER, rows)


# --- scenarios -----------------------------------------------------------------------------------

def build(scenario: str, day: date, seed: int, out_dir: Path) -> dict:
    messy = scenario == "messy_day"
    rng = random.Random(seed)
    days = [day - timedelta(days=1), day]
    orders = make_orders(rng, days, {"shopgoodwill": 24, "ebay": 16, "amazon": 14, "other": 4})
    missing: set[tuple[str, str]] = set()

    if messy:  # three single-unit orders get refunded on day D
        eligible = [o for o in orders if o.marketplace in ("ebay", "amazon") and o.units == 1]
        for o in rng.sample(eligible, 3):
            o.refunded_at = datetime.combine(day, time(rng.randint(8, 18), 5, 0), tzinfo=EASTERN)

    inbox = out_dir / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    for f in inbox.glob("*"):
        f.unlink()

    def write(name: str, text: str):
        (inbox / name).write_bytes(text.encode("utf-8"))

    for d in days:
        if messy and d == day:
            missing.add((d.isoformat(), "shopgoodwill"))  # today's Upright download never happened
            continue
        stamp = f"{d.month:02d}-{d.day:02d}-{d.year}"
        text = render_upright(rng, orders, d, noise_rows=messy)
        write(f"paid_orders_{stamp}_{stamp}.csv", text)
        if messy and d == days[0]:
            write(f"paid_orders_{stamp}_{stamp} (1).csv", text)  # re-downloaded: identical duplicate

    utc_from, utc_to = days[0], day + timedelta(days=1)
    write(f"orders2023-{day:%Y%m%d}-132256-96170.csv", render_cashmonkey(rng, orders, utc_from, utc_to, faults=messy))
    if messy:  # a second pull that overlaps the first (a staff member re-ran it)
        write(f"orders2023-{day:%Y%m%d}-141500-96171.csv", render_cashmonkey(rng, orders, day, day, faults=False))

    if messy:  # no Upright file for D, so those orders are not in any file: drop them from the truth
        orders = [o for o in orders if not (o.marketplace == "shopgoodwill" and eastern_day(o.placed) == day.isoformat())]
    key = {
        "scenario": scenario, "synthetic": True, "business_date": day.isoformat(), "seed": seed,
        "note": "Computed from the generated orders, not from the engine. 'missing' = no file was written.",
        "days": truth(orders, days, missing),
    }
    (out_dir / "expected.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return key


# --- checking the pipeline ------------------------------------------------------------------------

def check(out_dir: Path, key: dict) -> tuple[bool, list[str]]:
    from engine.ingest import EmailAttachmentAdapter, ingest

    batch = ingest([EmailAttachmentAdapter(out_dir / "inbox")])
    got: dict[tuple[str, str], dict] = defaultdict(lambda: dict(
        sales_cents=0, refunds_cents=0, fees_cents=0, orders=set(), customers=set()))
    for r in batch.rows:
        b = got[(r["business_date"], r["marketplace"])]
        if r["type"] == "sale":
            b["sales_cents"] += int(r["gross_cents"])
            b["fees_cents"] += int(r["fee_cents"])
            b["orders"].add(r["order_id"])
            b["customers"].add(r["customer_id"] or f"order:{r['order_id']}")
        else:
            b["refunds_cents"] += int(r["gross_cents"])
    lines, ok = [], True
    for day, markets in key["days"].items():
        for mk, want in markets.items():
            have = got.get((day, mk))
            if want["status"] == "missing":
                good = have is None
                ok &= good
                lines.append(f"{'ok  ' if good else 'FAIL'} {day} {mk:<13} no file written; "
                             f"pipeline shows {'no rows' if have is None else 'ROWS (should be none)'}")
                continue
            have_n = None if have is None else dict(
                sales_cents=have["sales_cents"], refunds_cents=have["refunds_cents"], fees_cents=have["fees_cents"],
                orders=len(have["orders"]), customers=len(have["customers"]))
            want_n = {k: want[k] for k in ("sales_cents", "refunds_cents", "fees_cents", "orders", "customers")}
            good = have_n == want_n
            ok &= good
            lines.append(f"{'ok  ' if good else 'FAIL'} {day} {mk:<13} sales ${want['sales_cents'] / 100:>9,.2f} "
                         f"refunds ${want['refunds_cents'] / 100:>8,.2f} orders {want['orders']:>3}"
                         + ("" if good else f"\n       expected {want_n}\n       got      {have_n}"))
    kinds: dict[str, int] = defaultdict(int)
    for w in batch.warnings:
        kinds[w["kind"]] += 1
    lines.append(f"warnings logged by the pipeline: {dict(kinds) or 'none'}")
    return ok, lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=["clean_day", "messy_day"], default="clean_day")
    ap.add_argument("--date", default="2026-10-02", help="the business day D (the file set also covers D-1)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None, help="default: out/sample/<scenario>")
    ap.add_argument("--check", action="store_true", help="run the generated files through the pipeline and compare")
    args = ap.parse_args(argv)

    out_dir = args.out or Path("out") / "sample" / args.scenario
    key = build(args.scenario, date.fromisoformat(args.date), args.seed, out_dir)
    files = sorted(p.name for p in (out_dir / "inbox").glob("*"))
    print(f"wrote {len(files)} files to {out_dir / 'inbox'} (SYNTHETIC) and {out_dir / 'expected.json'}")
    for f in files:
        print("  ", f)
    if not args.check:
        return 0
    ok, lines = check(out_dir, key)
    print()
    print("\n".join(lines))
    print("\nPIPELINE MATCHES THE ANSWER KEY" if ok else "\nPIPELINE DOES NOT MATCH THE ANSWER KEY")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
