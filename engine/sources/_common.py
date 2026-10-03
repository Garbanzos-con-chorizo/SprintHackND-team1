"""Shared parser for sources that export one row per order (or order line): the common case.

A new order-report source is then just a declaration of column names (see ebay.py). Anything that
doesn't fit this shape subclasses Parser directly and implements parse() itself.
"""
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
    row_type: tuple[str, ...] = ()       # a column saying what the row is (e.g. Order / Refund)
    refund_words: tuple[str, ...] = ("refund", "return", "reversal")
    skip_types: tuple[str, ...] = ()     # row_type values to ignore silently (e.g. payout, transfer)
    currency: tuple[str, ...] = ()       # optional; anything but USD is rejected

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        missing = [name for name, aliases in (("order id", self.order_id), ("date", self.date), ("amount", self.gross))
                   if not any(norm(a) in table.norm_header for a in aliases)]
        if missing:
            result.warn(table, 0, "missing_column", f"{self.source}: no column found for {', '.join(missing)}")
            return result

        seen: set[tuple] = set()
        grouped: dict[tuple[str, str, str], dict] = {}
        for row_no, row in table.rows:
            identity = tuple(str(v) for v in row.values())
            if identity in seen:
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
                day = parse_business_date(table.get(row, *self.date))
            except ValueError as exc:
                result.warn(table, row_no, "bad_date", str(exc))
                continue
            try:
                gross = parse_money(table.get(row, *self.gross))
                fee = sum(abs(parse_money(v)) for v in (table.get(row, f) for f in self.fees) if v)
                refunded = parse_money(table.get(row, *self.refund_amount)) if self.refund_amount and table.get(row, *self.refund_amount) else 0
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue

            is_refund_row = any(w in kind_text for w in self.refund_words) or gross < 0
            events = []
            if is_refund_row:
                events.append(("refund", -abs(gross), 0))   # refunds are always negative; fees stay on the sale
            else:
                events.append(("sale", gross, fee))
            if refunded:
                events.append(("refund", -abs(refunded), 0))

            buyer = table.get(row, *self.buyer)
            for typ, amount, event_fee in events:
                key = (order_id, typ, day)
                if key in grouped:  # several lines of one order in one file: one row per order
                    grouped[key]["gross_cents"] += amount
                    grouped[key]["fee_cents"] += event_fee
                    continue
                grouped[key] = {
                    "txn_id": f"{self.source}:{order_id}:{typ}",
                    "source": self.source,
                    "marketplace": self.marketplace,
                    "type": typ,
                    "business_date": day,
                    "order_id": order_id,
                    "customer_id": buyer_key(buyer) if buyer else "",
                    "customer_basis": "buyer" if buyer else "order",
                    "gross_cents": amount,
                    "fee_cents": event_fee,
                    "source_file": table.name,
                    "source_row": row_no,
                }
        for item in grouped.values():
            result.add(item)
        return result
