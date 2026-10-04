"""Jewelry Report and the supplier lookup that fills it in (deck slide 38: "Request report; Co-Pivot
populates Supplier"). Two files, joined by the engine into jewelry.csv (engine/enrich.py).

BOTH LAYOUTS ARE OURS: nobody has shown us the Jewelry Report or what "Co-Pivot" is. We read "Supplier" as
the Goodwill store that supplied the item (docs/ASSUMPTIONS.md 2c.3). They match the files the simulated
API writes (engine/scrapers/close_simulation.py):
  - the report: Item ID, Order ID, Sold Date, Description, Sale Amount, with no supplier;
  - the lookup: Item ID, Supplier.
A report that already carries a Supplier column keeps it; the lookup only fills the empty ones.
Correct the column names below when real files arrive.
"""
from ..clean import parse_business_date, parse_money
from ..parsers import ParseResult, Parser, register
from ..table import Table, norm


@register
class JewelryReport(Parser):
    source = "jewelry_report"
    filename_patterns = (r"jewelry",)
    required_columns = ("item id", "sold date", "sale amount")

    @property
    def feeds(self) -> tuple[str, ...]:
        return ()  # no marketplace: these sales are already in the marketplaces' own reports

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        for row_no, row in table.rows:
            item_id = table.get(row, "Item ID")
            if not item_id:
                result.warn(table, row_no, "unparseable", "empty item id")
                continue
            try:
                sold = parse_business_date(table.get(row, "Sold Date"))
            except ValueError as exc:
                result.warn(table, row_no, "bad_date", str(exc))
                continue
            try:
                amount = parse_money(table.get(row, "Sale Amount"))
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue
            result.table("jewelry").append({
                "item_id": item_id, "order_id": table.get(row, "Order ID"), "sold_date": sold, "amount_cents": amount,
                "supplier": table.get(row, "Supplier"), "source_file": table.name, "source_row": row_no,
            })
        return result


@register
class JewelrySuppliers(Parser):
    source = "jewelry_suppliers"
    filename_patterns = (r"supplier",)
    required_columns = ("item id", "supplier")
    daily = False  # a lookup, not a day-by-day report

    def detect(self, table: Table) -> int:
        # A Jewelry Report that already has a Supplier column is still the report, not the lookup.
        return 0 if norm("Sale Amount") in table.norm_header else super().detect(table)

    @property
    def feeds(self) -> tuple[str, ...]:
        return ()

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        for row_no, row in table.rows:
            item_id, supplier = table.get(row, "Item ID"), table.get(row, "Supplier")
            if not item_id or not supplier:
                result.warn(table, row_no, "unparseable", "a lookup row needs an item id and a supplier")
                continue
            result.table("jewelry_suppliers").append({"item_id": item_id, "supplier": supplier,
                                                      "source_file": table.name, "source_row": row_no})
        return result
