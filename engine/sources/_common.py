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
    refund_amount: tuple[str, ...] = ()  # a column holding the refunded amount, if the report has one
    # What the buyer was charged for shipping and handling (not revenue; the close posts them). A source
    # with one combined "shipping and handling" column puts it in `shipping`. A missing column reads 0.
    shipping: tuple[str, ...] = ()
    shipping_discount: tuple[str, ...] = ()  # subtracted from shipping (Upright's "Shipping Discount")
    handling: tuple[str, ...] = ()
    # Units sold: a quantity column, or a fixed count per row for exports with one item per row.
    # Neither known -> units stay empty (unknown), and the KPIs fall back to per-order figures.
    units: tuple[str, ...] = ()
    units_per_row: int | None = None
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
                shipping = self._money(table, row, self.shipping) - abs(self._money(table, row, self.shipping_discount))
                handling = self._money(table, row, self.handling)
                units = self._units(table, row)
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue

            is_refund_row = any(w in kind_text for w in self.refund_words) or gross < 0
            # (type, gross, fee, shipping, handling, units). Refunds are always negative, with the shipping
            # and handling refunded with them; fees stay on the sale; units count on sales only.
            no_units = None if units is None else 0
            events = []
            if is_refund_row:
                events.append(("refund", -abs(gross), 0, -abs(shipping), -abs(handling), no_units))
            else:
                events.append(("sale", gross, fee, shipping, handling, units))
            if refunded:
                events.append(("refund", -abs(refunded), 0, 0, 0, no_units))

            buyer = table.get(row, *self.buyer)
            marketplace = self.marketplace
            if self.channel:
                channel_name = norm(table.get(row, *self.channel))
                if self.strict_channels and channel_name not in self.channel_marketplaces:
                    continue
                marketplace = self.channel_marketplaces.get(channel_name, self.marketplace)
            for typ, amount, event_fee, ship, hand, n in events:
                key = (order_id, typ, day, marketplace)
                if key in grouped:  # several lines of one order in one file: one row per order
                    g = grouped[key]
                    g["gross_cents"] += amount
                    g["fee_cents"] += event_fee
                    g["shipping_cents"] += ship
                    g["handling_cents"] += hand
                    g["units"] = None if g["units"] is None or n is None else g["units"] + n
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
                    "source_file": table.name,
                    "source_row": row_no,
                    "shipping_cents": ship,
                    "handling_cents": hand,
                    "units": n,
                }
        for item in grouped.values():
            if item["units"] is None:
                item["units"] = ""  # unknown: an empty cell, never 0
            result.add(item)
        return result

    @staticmethod
    def _money(table: Table, row: dict, aliases: tuple[str, ...]) -> int:
        text = table.get(row, *aliases) if aliases else ""
        return parse_money(text) if text else 0

    def _units(self, table: Table, row: dict) -> int | None:
        if self.units and any(norm(a) in table.norm_header for a in self.units):
            text = table.get(row, *self.units).replace(",", "").strip()
            if not text:
                return None
            value = float(text)
            if value != int(value):
                raise ValueError(f"units {text!r} is not a whole number")
            return abs(int(value))
        return self.units_per_row

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
