"""Bank account activity export: every line goes to bank.csv for the month-end close (close-inputs.md).

Checked against the team's synthetic `bank_activity_2026-09.csv` (Posting Date, Description, Debit,
Credit, Balance), not a real Goodwill file. Credits are positive, debits negative; the close decides
which lines are marketplace deposits. A file without an Account column is the operating account.
Correct the aliases below when a real export arrives.
"""
from ..clean import parse_business_date, parse_money
from ..parsers import ParseResult, Parser, register
from ..table import Table, norm


@register
class Bank(Parser):
    source = "bank"
    filename_patterns = (r"bank",)
    required_columns = (("posting date", "date"), "description", "debit", "credit")

    date = ("Posting Date", "Date")
    description = ("Description",)
    debit = ("Debit",)
    credit = ("Credit",)
    balance = ("Balance",)
    account = ("Account", "Account Number")
    default_account = "OPERATING"

    @property
    def feeds(self) -> tuple[str, ...]:
        return ()  # no marketplace: bank lines never change source_status.json

    def parse(self, table: Table) -> ParseResult:
        result = ParseResult()
        has_balance = any(norm(a) in table.norm_header for a in self.balance)
        for row_no, row in table.rows:
            try:
                posting = parse_business_date(table.get(row, *self.date))
            except ValueError as exc:
                result.warn(table, row_no, "bad_date", str(exc))
                continue
            debit, credit = table.get(row, *self.debit), table.get(row, *self.credit)
            try:
                amount = (abs(parse_money(credit)) if credit else 0) - (abs(parse_money(debit)) if debit else 0)
                balance_text = table.get(row, *self.balance) if has_balance else ""
                balance = parse_money(balance_text) if balance_text else ""
            except ValueError as exc:
                result.warn(table, row_no, "bad_amount", str(exc))
                continue
            if not debit and not credit:
                result.warn(table, row_no, "bad_amount", "neither debit nor credit")
                continue
            result.bank.append({
                "bank_txn_id": f"{table.name}:{row_no}",
                "account": table.get(row, *self.account) or self.default_account,
                "posting_date": posting,
                "description": table.get(row, *self.description),
                "amount_cents": amount,
                "balance_cents": balance,
                "source_file": table.name,
                "source_row": row_no,
            })
        return result
