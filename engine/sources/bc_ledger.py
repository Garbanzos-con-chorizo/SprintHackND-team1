"""Business Central G/L entries export: every row goes to ledger.csv for the month-end close (close-inputs.md).

THE LAYOUT IS OURS: nobody has shown us this export. It matches the file the simulated API writes
(engine/scrapers/close_simulation.py): Entry No., Posting Date, Document Type, Document No.,
G/L Account No., Department Code, Vendor No., Description, Amount (debit positive, credit negative).
The parser filters nothing: which rows are FedEx (G/L 40356, department 180, vendor V00122, net of the
BNKDEPOSIT refunds) is the close's rule. Correct the aliases below when a real export arrives.
"""
from ..clean import parse_business_date, parse_money
from ..parsers import ParseResult, Parser, register
from ..table import Table


@register
class BcLedger(Parser):
    source = "bc_ledger"
    filename_patterns = (r"gl.?entries", r"ledger")
    required_columns = (("g l account no", "g l account"), "document no", "posting date", "amount")

    @property
    def feeds(self) -> tuple[str, ...]:
        return ()  # no marketplace

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        for row_no, row in table.rows:
            try:
                posting = parse_business_date(table.get(row, "Posting Date"))
            except ValueError as exc:
                result.warn(table, row_no, "bad_date", str(exc))
                continue
            try:
                amount = parse_money(table.get(row, "Amount"))
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue
            result.table("ledger").append({
                "entry_no": table.get(row, "Entry No.", "Entry No"),
                "posting_date": posting,
                "document_type": table.get(row, "Document Type"),
                "document_no": table.get(row, "Document No.", "Document No"),
                "gl_account": table.get(row, "G/L Account No.", "G/L Account"),
                "department": table.get(row, "Department Code", "Department"),
                "vendor_no": table.get(row, "Vendor No.", "Vendor No"),
                "description": table.get(row, "Description"),
                "amount_cents": amount,
                "source_file": table.name,
                "source_row": row_no,
            })
        return result
