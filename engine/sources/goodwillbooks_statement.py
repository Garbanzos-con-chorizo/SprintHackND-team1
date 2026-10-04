"""Goodwill Books payment statement: one row per statement goes to statements.csv (close-inputs.md).

THE LAYOUT IS OURS: nobody has shown us a statement. It matches the file the simulated API writes
(engine/scrapers/close_simulation.py): Statement Period Start, Statement Period End, Gross Sales, Fees,
Net Payment, Payment Date, Payment Reference. What the close does with it is the close's rule.
Correct the column names below when a real statement arrives.
"""
from ..clean import parse_business_date, parse_money
from ..parsers import ParseResult, Parser, register
from ..table import Table


@register
class GoodwillBooksStatement(Parser):
    source = "goodwillbooks_statement"
    filename_patterns = (r"statement",)
    required_columns = ("statement period start", "statement period end", "net payment")
    daily = False  # one statement a month, not a day-by-day report

    @property
    def feeds(self) -> tuple[str, ...]:
        return ()  # no marketplace: the statement never changes the pulse

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        for row_no, row in table.rows:
            try:
                start = parse_business_date(table.get(row, "Statement Period Start"))
                end = parse_business_date(table.get(row, "Statement Period End"))
                paid = table.get(row, "Payment Date")
                paid = parse_business_date(paid) if paid else ""
            except ValueError as exc:
                result.warn(table, row_no, "bad_date", str(exc))
                continue
            try:
                sales, fees, net = (parse_money(table.get(row, c)) for c in ("Gross Sales", "Fees", "Net Payment"))
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue
            result.table("statements").append({
                "source": "goodwillbooks", "period_from": start, "period_to": end,
                "sales_cents": sales, "fees_cents": abs(fees), "net_cents": net, "paid_date": paid,
                "reference": table.get(row, "Payment Reference", "Reference"),
                "source_file": table.name, "source_row": row_no,
            })
        return result
