"""Cell-level cleaning shared by all parsers: money to cents, dates to the Eastern business date.

These implement the "messy becomes clean" table in docs/contracts/transaction.md.
"""
import hashlib
import re
from datetime import date, datetime, timedelta, timezone
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


# US zone abbreviations as they appear in export text (hours from UTC, summer or standard as named).
_ZONE_OFFSETS = {"PDT": -7, "PST": -8, "MDT": -6, "MST": -7, "CDT": -5, "CST": -6,
                 "EDT": -4, "EST": -5, "UTC": 0, "GMT": 0}

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _finish(y, mo, d, clock, tzinfo, zone, assume_tz):
    """Turn parsed pieces into the business date. `clock` is (h, m, s) or None."""
    if clock is None:
        return date(y, mo, d).isoformat()
    dt = datetime(y, mo, d, *clock)
    if tzinfo is not None:
        dt = dt.replace(tzinfo=tzinfo)
    elif assume_tz:
        dt = dt.replace(tzinfo=ZoneInfo(assume_tz))
    else:
        return dt.date().isoformat()  # naive time: already in business-local terms
    return dt.astimezone(zone).date().isoformat()


def _clock(h, m, s, ampm):
    if h is None:
        return None
    h = int(h)
    if ampm:
        h = h % 12 + (12 if ampm.lower() == "pm" else 0)
    return (h, int(m), int(s or 0))


def _zone_abbr(abbr: str, value):
    if not abbr:
        return None
    abbr = abbr.upper()
    if abbr not in _ZONE_OFFSETS:
        raise ValueError(f"unknown time zone {abbr!r} in {value!r}")
    return timezone(timedelta(hours=_ZONE_OFFSETS[abbr]))


def parse_business_date(value, tz: str = TIMEZONE, assume_tz: str | None = None) -> str:
    """Any common date/datetime text or object -> 'YYYY-MM-DD' in the business timezone. Raises ValueError.

    A time with an explicit offset or zone name is converted to the business timezone. A time with none
    is taken as already local, unless the source is known to write another zone: pass that as
    `assume_tz` (Cash Monkey writes UTC). Slash dates are read US-style (month first).
    """
    zone = ZoneInfo(tz)
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.astimezone(zone).date().isoformat()
        return _finish(value.year, value.month, value.day, (value.hour, value.minute, value.second),
                       None, zone, assume_tz)
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        raise ValueError("empty date")

    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ]+(\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?\s*"
                 r"(Z|[+-]\d{2}:?\d{2}|[A-Za-z]{2,4})?)?$", text)
    if m:
        tzinfo = None
        if m[7]:
            if m[7] == "Z":
                tzinfo = timezone.utc
            elif m[7][0] in "+-":
                sign = -1 if m[7][0] == "-" else 1
                digits = m[7][1:].replace(":", "")
                tzinfo = timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))
            else:
                tzinfo = _zone_abbr(m[7], value)
        return _finish(int(m[1]), int(m[2]), int(m[3]), _clock(m[4], m[5], m[6], None), tzinfo, zone, assume_tz)

    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?\s*([A-Za-z]{2,4})?)?$", text)
    if m:
        y = int(m[3])
        y += 2000 if y < 100 else 0
        return _finish(y, int(m[1]), int(m[2]), _clock(m[4], m[5], m[6], m[7]), _zone_abbr(m[8], value), zone, assume_tz)

    # Oct 2, 2026   or   Oct 2, 2026 9:33:00 PM PDT
    m = re.match(r"^([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})"
                 r"(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?\s*([A-Za-z]{2,4})?)?\s*$", text)
    if m and m[1].lower() in _MONTHS:
        return _finish(int(m[3]), _MONTHS[m[1].lower()], int(m[2]), _clock(m[4], m[5], m[6], m[7]),
                       _zone_abbr(m[8], value), zone, assume_tz)

    m = re.match(r"^(\d{1,2})[- ]([A-Za-z]{3})[a-z]*[- ,]+(\d{2}|\d{4})$", text)  # 2-Oct-26
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
