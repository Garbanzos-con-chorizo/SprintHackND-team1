"""ShopGoodwill periodic report: each period becomes a payout row that states the days it pays for.

THE LAYOUT IS OURS (Dani's generator, data/README.md): the deck names "periodic marketplace reports"
(slide 38) and shows none. One row per payout: Period Start, Period End, Paid Date, Payout Amount,
Reference, with periods in Pacific days. What the deck calls "Period 1" and "Period 3" is not known and
not modeled. The rows go to payouts.csv with `period_from` and `period_to` filled, so the close checks
each payout against the files for exactly those days instead of inferring a weekly cycle from the deposits.
Correct the column names below when a real report arrives.
"""
from ..clean import parse_business_date, parse_money
from ..parsers import ParseResult, Parser, register
from ..table import Table


@register
class ShopGoodwillPeriodic(Parser):
    source = "shopgoodwill_periodic"
    marketplace = "shopgoodwill"
    filename_patterns = (r"periodic",)
    required_columns = ("period start", "period end", "paid date", "payout amount")
    daily = False  # a list of payouts, not a day-by-day sales report

    @property
    def feeds(self) -> tuple[str, ...]:
        # No marketplace: this is not a sales report, so it must never make ShopGoodwill's day look covered
        # in source_status.json or source_coverage.json.
        return ()

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        for row_no, row in table.rows:
            try:
                start = parse_business_date(table.get(row, "Period Start"))
                end = parse_business_date(table.get(row, "Period End"))
                paid = parse_business_date(table.get(row, "Paid Date"))
            except ValueError as exc:
                result.warn(table, row_no, "bad_date", str(exc))
                continue
            try:
                amount = parse_money(table.get(row, "Payout Amount"))
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue
            if end < start:
                result.warn(table, row_no, "bad_date", f"period ends {end} before it starts {start}")
                continue
            result.payouts.append({
                "payout_id": f"{self.marketplace}:{paid}", "marketplace": self.marketplace, "paid_date": paid,
                "amount_cents": amount, "period_from": start, "period_to": end,
                "source_file": table.name, "source_row": row_no,
            })
        return result
