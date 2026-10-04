"""store backfill (V2.4): engine, pulse and load for every day of a range, from one inbox.

The inbox is read once (the engine output holds every row it found, whatever the date), then
for each day the engine's files are written for that date, Dani's pulse command runs on them,
and the day is loaded. A day that fails is reported and skipped; the others still load.
The internal API pull joins each day here once it exists (V2.6).
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

from ..cli import write_day
from ..ingest import EmailAttachmentAdapter, ingest
from .load import LoadError, load_day
from .status import days_between

ROOT = Path(__file__).resolve().parents[2]


def backfill(conn: sqlite3.Connection, inbox: Path, out: Path, start: str, end: str, on_day=None) -> list[dict]:
    """Returns one result per day: {"date", "result": "ok" | "failed", "message", ...load summary}."""
    out = out.resolve()
    batch = ingest([EmailAttachmentAdapter(inbox)])
    results = []
    for day in days_between(start, end):
        try:
            write_day(batch, out, day)
            run_pulse(out, day)
            result = {"date": day, "result": "ok", "message": "", **load_day(conn, out, day)}
        except (LoadError, PulseError, OSError) as e:
            result = {"date": day, "result": "failed", "message": str(e)}
        results.append(result)
        if on_day:
            on_day(result)
    return results


class PulseError(Exception):
    pass


def run_pulse(out: Path, day: str) -> None:
    """Dani's command, called as the nightly run calls it (decoupled from recon's Python)."""
    done = subprocess.run([sys.executable, "-m", "recon.pulse", "--date", day, "--in-dir", str(out)],
                          cwd=ROOT, capture_output=True, text=True)
    if done.returncode:
        raise PulseError(f"recon.pulse failed (exit {done.returncode}): {done.stderr.strip() or done.stdout.strip()}")
