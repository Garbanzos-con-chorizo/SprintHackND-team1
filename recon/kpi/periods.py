"""Day, ISO week and month periods, and the window each one is compared with (Period in kpi.md)."""
import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

TYPES = ("day", "week", "month")
_ID = {"day": r"(\d{4})-(\d{2})-(\d{2})", "week": r"(\d{4})-W(\d{2})", "month": r"(\d{4})-(\d{2})"}
_EXAMPLE = {"day": "2026-10-02", "week": "2026-W38", "month": "2026-09"}


@dataclass(frozen=True)
class Period:
    type: str
    id: str
    start: date
    end: date


@dataclass(frozen=True)
class Window:
    """The part of a period that is reported: `start` to `through`."""

    period: Period
    through: date

    @property
    def start(self):
        return self.period.start

    @property
    def days(self):
        return (self.through - self.period.start).days + 1

    @property
    def complete(self):
        return self.through == self.period.end

    def dates(self):
        return [self.start + timedelta(days=i) for i in range(self.days)]


def containing(type_, day):
    """The period of that type which contains `day`."""
    if type_ == "day":
        return Period("day", day.isoformat(), day, day)
    if type_ == "week":
        year, week, weekday = day.isocalendar()
        monday = day - timedelta(days=weekday - 1)
        return Period("week", f"{year}-W{week:02d}", monday, monday + timedelta(days=6))
    if type_ == "month":
        last = calendar.monthrange(day.year, day.month)[1]
        return Period("month", f"{day:%Y-%m}", day.replace(day=1), day.replace(day=last))
    raise ValueError(f"unknown period type {type_!r}")


def parse(type_, text):
    """Period from its id: 2026-10-02, 2026-W38 or 2026-09. ValueError on anything else."""
    if type_ not in TYPES:
        raise ValueError(f"unknown period type {type_!r}")
    m = re.fullmatch(_ID[type_], text)
    if not m:
        raise ValueError(f"a {type_} must look like {_EXAMPLE[type_]}, got {text!r}")
    a, b = int(m[1]), int(m[2])
    if type_ == "day":
        return containing("day", date(a, b, int(m[3])))
    if type_ == "week":
        return containing("week", date.fromisocalendar(a, b, 1))
    return containing("month", date(a, b, 1))


def previous(period):
    return containing(period.type, period.start - timedelta(days=1))


def window(period, latest_stored, through=None):
    """What to report of `period`, given the latest business date stored.

    A finished period is reported whole. An unfinished one is reported to date. If nothing
    is stored on or after its first day, the window is that first day (and has no data).
    """
    if through is not None:
        if not period.start <= through <= period.end:
            raise ValueError(f"--through {through} is outside {period.id} ({period.start} to {period.end})")
        return Window(period, through)
    if latest_stored is None or latest_stored < period.start:
        return Window(period, period.start)
    return Window(period, min(period.end, latest_stored))


def prior_window(win):
    """The window `win` is compared with: the whole period before when `win` is complete,
    otherwise the first `win.days` days of it."""
    before = previous(win.period)
    if win.complete:
        return Window(before, before.end)
    return Window(before, min(before.end, before.start + timedelta(days=win.days - 1)))


def _day(d):
    return f"{d:%B} {d.day}, {d.year}"


def _span(a, b):
    if a == b:
        return _day(a)
    if (a.year, a.month) == (b.year, b.month):
        return f"{a:%B} {a.day} to {b.day}, {a.year}"
    if a.year == b.year:
        return f"{a:%b} {a.day} to {b:%b} {b.day}, {a.year}"
    return f"{a:%b} {a.day}, {a.year} to {b:%b} {b.day}, {b.year}"


def _name(period):
    if period.type == "day":
        return _day(period.start)
    if period.type == "week":
        return f"Week {int(period.id[-2:])}, {period.id[:4]}"
    return f"{period.start:%B %Y}"


def label(win):
    """Title of the reported window: the period's name, marked when it is not finished."""
    return _name(win.period) + ("" if win.complete else " (to date)")


def comparison_label(win):
    """Name of a comparison window: the period's name when whole, otherwise its dates."""
    return _name(win.period) if win.complete else _span(win.start, win.through)
