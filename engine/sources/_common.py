"""Shared parser for sources that export one row per order (or order line): the common case.

A new order-report source is then just a declaration of column names (see ebay.py). Anything that
doesn't fit this shape subclasses Parser directly and implements parse() itself.
"""
import re

from ..clean import buyer_key, parse_business_date, parse_money
from ..parsers import ParseResult, Parser
from ..table import Table, norm


class OrderReportParser(Parser):
    # Column-name aliases, tried in order, compared normalized (case, spaces, '_' and '-' ignored).
    order_id: tuple[str, ...] = ()
    date: tuple[str, ...] = ()
    gross: tuple[str, ...] = ()          # merchandise amount, excluding shipping and tax
    fees: tuple[str, ...] = ()           # every fee column found is summed; stored as a positive cost
    buyer: tuple[str, ...] = ()
    # What the buyer was charged for shipping and for handling, as the report writes it (first column found).
    # Reported separately and never part of `gross_cents`. Sale rows are positive, refund rows negative.
    shipping: tuple[str, ...] = ()
    handling: tuple[str, ...] = ()
    refund_amount: tuple[str, ...] = ()  # a column holding the refunded amount, if the report has one
    row_type: tuple[str, ...] = ()       # a column saying what the row is (e.g. Order / Refund)
    refund_words: tuple[str, ...] = ("refund", "return", "reversal")
    skip_types: tuple[str, ...] = ()     # row_type values to ignore silently (e.g. payout, transfer)
    currency: tuple[str, ...] = ()       # optional; anything but USD is rejected
    # Sources that list several marketplaces in one file (Upright, Cash Monkey): the column holding the
    # channel name and a {normalized channel name: marketplace} map. Unknown channels use `marketplace`.
    channel: tuple[str, ...] = ()
    channel_marketplaces: dict[str, str] = {}
    # True when staff count customers as rows (Upright, slide 26) even though a buyer column exists:
    # the buyer id is kept in customer_id but customer_basis is "order", so the pulse counts orders.
    customers_are_orders: bool = False
    # An export with one line per unit can repeat an identical line for 2 units of the same item, so for
    # those sources identical rows in one file are NOT duplicates. (Cross-file dedupe still applies.)
    identical_rows_are_duplicates: bool = True
    strict_channels: bool = False        # True: rows of channels not in the map belong to another source; skip them
    date_assume_tz: str | None = None    # zone of timestamps that carry none (Cash Monkey writes UTC)
    # Regex with three groups (month, day, year) for a date in the file name, used when the file has no
    # date column (Upright's report is per day and its rows carry no date).
    filename_date: str = ""

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        file_day = self._filename_day(table.name)
        needed = [("order id", self.order_id), ("amount", self.gross)]
        if file_day is None:
            needed.append(("date", self.date))
        missing = [name for name, aliases in needed if not any(norm(a) in table.norm_header for a in aliases)]
        if missing:
            result.warn(table, 0, "missing_column", f"{self.source}: no column found for {', '.join(missing)}")
            return result

        seen: set[tuple] = set()
        grouped: dict[tuple[str, str, str], dict] = {}
        for row_no, row in table.rows:
            identity = tuple(str(v) for v in row.values())
            if self.identical_rows_are_duplicates and identity in seen:
                result.warn(table, row_no, "duplicate", "identical to an earlier row in this file")
                continue
            seen.add(identity)

            kind_text = table.get(row, *self.row_type).lower() if self.row_type else ""
            if any(w in kind_text for w in self.skip_types):
                continue  # payouts, transfers: money movement, not sales (the close uses them, the pulse doesn't)

            order_id = table.get(row, *self.order_id)
            if not order_id:
                result.warn(table, row_no, "unparseable", "empty order id")
                continue
            if self.currency:
                cur = table.get(row, *self.currency)
                if cur and cur.upper() != "USD":
                    result.warn(table, row_no, "unsupported_currency", f"currency {cur}")
                    continue
            try:
                date_text = table.get(row, *self.date) if any(norm(a) in table.norm_header for a in self.date) else ""
                day = parse_business_date(date_text, assume_tz=self.date_assume_tz) if date_text or file_day is None else file_day
            except ValueError as exc:
                result.warn(table, row_no, "bad_date", str(exc))
                continue
            try:
                gross = parse_money(table.get(row, *self.gross))
                fee = sum(abs(parse_money(v)) for v in (table.get(row, f) for f in self.fees) if v)
                refunded = parse_money(table.get(row, *self.refund_amount)) if self.refund_amount and table.get(row, *self.refund_amount) else 0
                ship_text, hand_text = table.get(row, *self.shipping), table.get(row, *self.handling)
                shipping = abs(parse_money(ship_text)) if ship_text else 0
                handling = abs(parse_money(hand_text)) if hand_text else 0
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue

            is_refund_row = any(w in kind_text for w in self.refund_words) or gross < 0
            events = []
            if is_refund_row:
                # refunds are always negative, and so is the shipping and handling given back; fees stay on the sale
                events.append(("refund", -abs(gross), 0, -shipping, -handling))
            else:
                events.append(("sale", gross, fee, shipping, handling))
            if refunded:
                events.append(("refund", -abs(refunded), 0, 0, 0))   # a refund column carries no shipping detail

            buyer = table.get(row, *self.buyer)
            marketplace = self.marketplace
            if self.channel:
                channel_name = norm(table.get(row, *self.channel))
                if self.strict_channels and channel_name not in self.channel_marketplaces:
                    continue
                marketplace = self.channel_marketplaces.get(channel_name, self.marketplace)
            for typ, amount, event_fee, event_ship, event_hand in events:
                key = (order_id, typ, day, marketplace)
                if key in grouped:  # several lines of one order in one file: one row per order
                    grouped[key]["gross_cents"] += amount
                    grouped[key]["fee_cents"] += event_fee
                    grouped[key]["shipping_cents"] += event_ship
                    grouped[key]["handling_cents"] += event_hand
                    continue
                grouped[key] = {
                    "txn_id": f"{self.source}:{order_id}:{typ}",
                    "source": self.source,
                    "marketplace": marketplace,
                    "type": typ,
                    "business_date": day,
                    "order_id": order_id,
                    "customer_id": buyer_key(buyer) if buyer else "",
                    "customer_basis": "buyer" if buyer and not self.customers_are_orders else "order",
                    "gross_cents": amount,
                    "fee_cents": event_fee,
                    "shipping_cents": event_ship,
                    "handling_cents": event_hand,
                    "source_file": table.name,
                    "source_row": row_no,
                }
        for item in grouped.values():
            result.add(item)
        return result

    @property
    def feeds(self) -> tuple[str, ...]:
        if not self.channel:
            return (self.marketplace,)
        mapped = set(self.channel_marketplaces.values())
        return tuple(sorted(mapped if self.strict_channels else mapped | {self.marketplace}))

    def _filename_day(self, name: str) -> str | None:
        """The day in the file name (e.g. paid_orders_09-30-2026_09-30-2026), if configured and present."""
        if not self.filename_date:
            return None
        m = re.search(self.filename_date, name, re.IGNORECASE)
        if not m:
            return None
        try:
            return parse_business_date(f"{m[1]}/{m[2]}/{m[3]}")
        except ValueError:
            return None
