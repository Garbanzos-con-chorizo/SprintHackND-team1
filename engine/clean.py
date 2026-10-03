"""Cell-level cleaning shared by all parsers: money to cents, dates to the Eastern business date.

These implement the "messy becomes clean" table in docs/contracts/transaction.md.
"""
import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from .contract import TIMEZONE


def parse_money(value) -> int:
    """'$1,234.50', '1234.5', '(12.00)', '12.00-', 'USD 3.10', 5, 5.1 -> integer cents. Raises ValueError."""
    if isinstance(value, bool):
        raise ValueError(f"not an amount: {value!r}")
    if isinstance(value, (int, float, Decimal)):
        dec = Decimal(str(value))
    else:
        text = str(value).strip()
        if text == "":
            raise ValueError("empty amount")
        negative = text.startswith("(") and text.endswith(")") or text.endswith("-") or text.startswith("-")
        digits = re.sub(r"[^0-9.,]", "", text)
        if "," in digits and "." in digits:
            digits = digits.replace(",", "")  # 1,234.50
        elif "," in digits:
            # '5,00' is a decimal comma; '1,234' is a thousands separator
            head, _, tail = digits.rpartition(",")
            digits = f"{head.replace(',', '')}.{tail}" if len(tail) in (1, 2) and "," not in head else digits.replace(",", "")
        if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", digits):
            raise ValueError(f"not an amount: {value!r}")
        dec = Decimal(digits)
        dec = -dec if negative else dec
    try:
        return int((dec * 100).quantize(Decimal("1")))
    except InvalidOperation as exc:
        raise ValueError(f"not an amount: {value!r}") from exc


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_business_date(value, tz: str = TIMEZONE) -> str:
    """Any common date/datetime text or object -> 'YYYY-MM-DD' in the business timezone. Raises ValueError.

    Datetimes with an offset are converted to the business timezone; naive ones are taken as already
    local. Slash dates are read US-style (month first), the way Goodwill's exports are written.
    """
    zone = ZoneInfo(tz)
    if isinstance(value, datetime):
        dt = value.astimezone(zone) if value.tzinfo else value
        return dt.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        raise ValueError("empty date")

    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ](.*))?$", text)
    if m:
        y, mo, d, rest = int(m[1]), int(m[2]), int(m[3]), m[4]
        if rest and re.search(r"(Z|[+-]\d{2}:?\d{2})$", rest.strip()):
            dt = datetime.fromisoformat(text.replace("Z", "+00:00").replace(" ", "T", 1))
            return dt.astimezone(zone).date().isoformat()
        return date(y, mo, d).isoformat()

    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})(?:\s|$)", text)
    if m:
        y = int(m[3])
        y += 2000 if y < 100 else 0
        return date(y, int(m[1]), int(m[2])).isoformat()

    m = re.match(r"^([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", text)  # Oct 2, 2026
    if m and m[1].lower() in _MONTHS:
        return date(int(m[3]), _MONTHS[m[1].lower()], int(m[2])).isoformat()

    m = re.match(r"^(\d{1,2})[- ]([A-Za-z]{3})[a-z]*[- ,]+(\d{2}|\d{4})", text)  # 2-Oct-26
    if m and m[2].lower() in _MONTHS:
        y = int(m[3])
        y += 2000 if y < 100 else 0
        return date(y, _MONTHS[m[2].lower()], int(m[1])).isoformat()

    raise ValueError(f"unrecognized date: {value!r}")


def buyer_key(value: str) -> str:
    """Buyer id for the customer_id column. Emails are hashed: the contract forbids raw emails."""
    value = value.strip()
    if "@" in value:
        return "h_" + hashlib.sha256(value.lower().encode()).hexdigest()[:12]
    return value
