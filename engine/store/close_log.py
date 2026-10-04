"""store log-close (V3.4): one `runs` row for a month-end close, so the store remembers it ran.

The close itself writes nothing to the store. This only reads what `python -m reports.close` left behind
(docs/contracts/close-outputs.md: its exit code and `close_status_<month>.json`) and records the run in the
same log as the loads, pulls and KPI runs. `business_date` is the last day of the month closed.
"""
import calendar
import json
import sqlite3
import uuid
from pathlib import Path

from ..writer import now_local
from .load import record_run


def log_close(conn: sqlite3.Connection, month: str, exit_code: int, close_dir: Path) -> dict:
    """Record the close of `month` (YYYY-MM) that just exited with `exit_code`. Returns the row's summary."""
    month_end = f"{month}-{calendar.monthrange(int(month[:4]), int(month[5:7]))[1]:02d}"
    status_file = Path(close_dir) / month / f"close_status_{month}.json"
    status = None
    if exit_code in (0, 2):  # a refused run (exit 1) leaves no status file of its own: never read an older one
        try:
            status = json.loads(status_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            status = None
    if status:
        sources = "; ".join(f"{name}={s['status']}" for name, s in status["sources"].items())
        posting = status["posting"]["status"].replace("_", " ")
        row = {"run_id": f"close-{month}-{status['run_id']}", "started": status["run_at"], "files": status["inboxes"],
               "rows": status["journal"]["lines"] + status["invoices"]["lines"],
               "warnings": status["exceptions"]["total"], "result": "ok" if exit_code == 0 else "failed",
               "message": f"{sources}; {status['exceptions']['total']} exceptions"
                          + ("; needs review" if status["needs_review"] else "") + f"; {posting}"
                          + ("; files failed the read-back check" if exit_code == 2 else "")}
    else:
        row = {"run_id": f"close-{month}-{uuid.uuid4().hex[:8]}", "started": now_local().isoformat(), "files": [],
               "rows": 0, "warnings": 0, "result": "failed",
               "message": f"close exited {exit_code}: " + ("refused, nothing written" if exit_code == 1
                                                           else f"no status file at {status_file}")}
    try:
        with conn:
            record_run(conn, "close", row["run_id"], month_end, row["started"], row["files"], row["rows"],
                       row["warnings"], row["result"], row["message"])
    except sqlite3.IntegrityError:
        row["already_logged"] = True  # the same close run, logged twice
    return row
