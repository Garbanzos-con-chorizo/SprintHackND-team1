"""source_coverage.json (V3.3, docs/contracts/close-inputs.md): for each source, the files read, the days each
file says it covers, whether a simulator wrote it, and the days of the month that no file covers.

A file's days come from its name when the name states them (`amazon_daterange_2026-09-01_2026-09-20`,
`paid_orders_09-07-2026_09-07-2026`, `bank_activity_2026-09` for a whole month); otherwise from the first and
last date of its rows (`basis: rows`). Sources are keyed like source_status.json: by marketplace, plus the
parser's own name for files that feed no marketplace (`bank`). The expected marketplaces are always listed.

Which files are simulated: `engine fetch --simulate` lists every file it writes in `<inbox>/_simulated.json`
(SIMULATED_MANIFEST), which the inbox reader skips because it is not a report.
"""
import calendar
import json
import re
from datetime import date, timedelta
from pathlib import Path

from .contract import EXPECTED_MARKETPLACES

SIMULATED_MANIFEST = "_simulated.json"


def read_manifest(inbox: Path) -> dict:
    try:
        return json.loads((Path(inbox) / SIMULATED_MANIFEST).read_text(encoding="utf-8")).get("files", {})
    except (OSError, ValueError, AttributeError):
        return {}


def update_manifest(inbox: Path, simulated: dict[str, dict], real: list[str] = ()) -> None:
    """Record files a simulator wrote ({name: details}); forget names a real fetch has since overwritten."""
    files = read_manifest(inbox)
    files.update(simulated)
    for name in real:
        files.pop(name, None)
    path = Path(inbox) / SIMULATED_MANIFEST
    if not files:
        path.unlink(missing_ok=True)
        return
    note = "Files written by `engine fetch --simulate`: synthetic data, no real API. Read by the engine."
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"note": note, "files": dict(sorted(files.items()))}, f, indent=2)
        f.write("\n")


def summarize(file: dict, result) -> dict:
    """Add to a batch's file entry what coverage needs: rows and first/last date per source key."""
    rows: dict[str, int] = {}
    dates: dict[str, list[str]] = {}
    items = ([(r["marketplace"], r["business_date"]) for r in result.rows]
             + [(p["marketplace"], p["paid_date"]) for p in result.payouts]
             + [(file["source"], b["posting_date"]) for b in result.bank])
    for key, day in items:
        rows[key] = rows.get(key, 0) + 1
        span = dates.setdefault(key, [day, day])
        span[0], span[1] = min(span[0], day), max(span[1], day)
    return {**file, "rows": rows, "dates": dates}


def named_range(name: str) -> tuple[str, str] | None:
    """The days a file name states: two dates, one date, or a month. None if it states none."""
    iso = re.findall(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", name)
    us = [(y, m, d) for m, d, y in re.findall(r"(?<!\d)(\d{2})-(\d{2})-(\d{4})(?!\d)", name)]
    try:
        found = [date(int(y), int(m), int(d)) for y, m, d in (iso or us)[:2]]
        if found:
            a, b = min(found), max(found)
            return a.isoformat(), b.isoformat()
        m = re.search(r"(?<!\d)(\d{4})-(\d{2})(?![\d-])", name)
        if m:
            y, mo = int(m[1]), int(m[2])
            return date(y, mo, 1).isoformat(), date(y, mo, calendar.monthrange(y, mo)[1]).isoformat()
    except ValueError:
        return None
    return None


def build_source_coverage(through: str, files: list[dict]) -> dict:
    """Coverage of the month of `through` (YYYY-MM-DD), from its 1st up to `through`."""
    first = date.fromisoformat(through[:8] + "01")
    last = date.fromisoformat(through)
    month_days = [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]

    def keys_of(f: dict) -> list[str]:
        # A file that can feed several marketplaces (Cash Monkey) covers only those it has rows for: its
        # eBay-channel export says nothing about Amazon. A single-source file covers its days even when quiet.
        feeds = f["feeds"] or [f["source"]]
        return feeds if len(feeds) == 1 else [k for k in feeds if f.get("rows", {}).get(k)]

    keys = list(EXPECTED_MARKETPLACES)
    for f in files:
        keys += [k for k in keys_of(f) if k not in keys]
    sources = {}
    for key in keys:
        entries, covered = [], set()
        for f in files:
            if key not in keys_of(f):
                continue
            span, basis = named_range(f["file"]), "file_name"
            if span is None:
                span, basis = tuple(f.get("dates", {}).get(key, ("", ""))), "rows"
            entries.append({"name": f["file"], "from": span[0], "to": span[1], "basis": basis,
                            "rows": f.get("rows", {}).get(key, 0), "simulated": bool(f.get("simulated"))})
            if span[0]:
                a, b = date.fromisoformat(span[0]), date.fromisoformat(span[1])
                covered.update((a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1))
        sources[key] = {"files": entries, "days_missing": [d for d in month_days if d not in covered]}
    return {"month": through[:7], "through": through, "sources": sources}
