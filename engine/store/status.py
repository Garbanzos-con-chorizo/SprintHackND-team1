"""store status (V2.3): which days of a period are in the store, per marketplace."""
import sqlite3
from datetime import date, timedelta

from ..contract import EXPECTED_MARKETPLACES

NO_DATA = ("missing", "stale", "unknown")


def days_between(start: str, end: str) -> list[str]:
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


def month_bounds(month: str) -> tuple[str, str]:
    first = date.fromisoformat(f"{month}-01")
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first.isoformat(), (nxt - timedelta(days=1)).isoformat()


def latest_month(conn: sqlite3.Connection) -> str | None:
    last = conn.execute("SELECT MAX(business_date) FROM pulse_daily").fetchone()[0]
    return last[:7] if last else None


def store_status(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """Per day and marketplace, what the store holds between `start` and `end` (inclusive).
    A day is complete when every expected marketplace is ok, partial when it is loaded but one is
    missing, stale or unknown, and not loaded when the store has no pulse rows for it."""
    days = days_between(start, end)
    loaded: dict[str, dict[str, tuple]] = {}
    for day, mk, status, revenue in conn.execute(
            "SELECT business_date, marketplace, status, revenue_cents FROM pulse_daily "
            "WHERE business_date BETWEEN ? AND ?", (start, end)):
        loaded.setdefault(day, {})[mk] = (status, revenue)

    shown = list(EXPECTED_MARKETPLACES)
    if any(d.get("other", ("",))[0] == "ok" for d in loaded.values()):
        shown.append("other")
    marketplaces = {}
    for mk in shown:
        counts = {"ok": 0, "missing": 0, "stale": 0, "unknown": 0, "not_loaded": 0}
        revenue = None
        for day in days:
            status, cents = loaded.get(day, {}).get(mk, ("not_loaded", None))
            counts[status if status in counts else "unknown"] += 1
            if status == "ok":
                revenue = (revenue or 0) + (cents or 0)
        marketplaces[mk] = {**counts, "revenue_cents": revenue}

    partial = {}
    for day in days:
        if day in loaded:
            gaps = [f"{mk} {loaded[day].get(mk, ('unknown',))[0]}" for mk in EXPECTED_MARKETPLACES
                    if loaded[day].get(mk, ("unknown",))[0] != "ok"]
            if gaps:
                partial[day] = gaps
    last_run = conn.execute("SELECT run_id, command, business_date, finished_at, result, message FROM runs "
                            "ORDER BY started_at DESC, rowid DESC LIMIT 1").fetchone()
    return {
        "start": start, "end": end, "days_expected": len(days),
        "days_loaded": sum(day in loaded for day in days),
        "complete": [d for d in days if d in loaded and d not in partial],
        "partial": partial,
        "not_loaded": [d for d in days if d not in loaded],
        "marketplaces": marketplaces,
        "last_run": dict(zip(("run_id", "command", "business_date", "finished_at", "result", "message"),
                             last_run)) if last_run else None,
    }


def format_status(s: dict) -> str:
    lines = [f"{s['start']} to {s['end']}: {s['days_loaded']} of {s['days_expected']} days loaded, "
             f"{len(s['complete'])} complete, {len(s['partial'])} partial, {len(s['not_loaded'])} not loaded",
             f"  {'marketplace':<14}{'ok':>5}{'missing':>9}{'stale':>7}{'unknown':>9}{'not loaded':>12}{'revenue':>15}"]
    for mk, m in s["marketplaces"].items():
        revenue = "no data" if m["revenue_cents"] is None else f"${m['revenue_cents'] / 100:,.2f}"
        lines.append(f"  {mk:<14}{m['ok']:>5}{m['missing']:>9}{m['stale']:>7}{m['unknown']:>9}"
                     f"{m['not_loaded']:>12}{revenue:>15}")
    if s["partial"]:
        lines.append("  partial: " + "; ".join(f"{d} ({', '.join(g)})" for d, g in s["partial"].items()))
    if s["not_loaded"]:
        lines.append("  not loaded: " + compress(s["not_loaded"]))
    if s["last_run"]:
        r = s["last_run"]
        lines.append(f"  last run: {r['command']} {r['business_date'] or ''} {r['result']} at {r['finished_at']}"
                     + (f" ({r['message']})" if r["message"] else ""))
    return "\n".join(lines)


def compress(days: list[str]) -> str:
    """'2026-09-01..2026-09-03, 2026-09-07' instead of every date."""
    runs, prev = [], None
    for d in days:
        if prev and date.fromisoformat(d) - date.fromisoformat(prev) == timedelta(days=1):
            runs[-1][1] = d
        else:
            runs.append([d, d])
        prev = d
    return ", ".join(a if a == b else f"{a}..{b}" for a, b in runs)
