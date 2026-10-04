"""Add the reports that were missing at month end, from the portal, and run the close again (decision 010).

A month-end close that says INCOMPLETE is missing a report for some days. Staff download that report from the
marketplace and need a place to hand it over. This module is that place's back room: it keeps the added files in
`out/uploads/<month>/` (never in the sample folders), and runs the same close again on the inboxes of the last
run plus that folder. It computes nothing itself: the engine reads the files and `python -m reports.close`
decides what they change. Nothing is posted.

`server.py` exposes it (PUT a file, POST "run", DELETE to start over); the panel is on reports/close/index.html.

    python -m reports.close_upload --month 2026-09 --add FILE [FILE ...]    # the same, by hand
    python -m reports.close_upload --month 2026-09 --clear                  # take them away and run again
"""
import argparse
import contextlib
import io
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "out" / "uploads"
ALLOWED = {".csv", ".xlsx"}             # what the engine's inbox reads and the marketplaces export
MAX_BYTES = 10 * 1024 * 1024
MAX_FILES = 40


class Rejected(ValueError):
    """The file or the month is not acceptable; the message is for the person who added it."""


def check_month(month):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month or ""):
        raise Rejected("the month must look like 2026-09")
    return month


def safe_name(name):
    """The file's own name with no folder in front, or Rejected. Only the two report formats are taken."""
    name = re.split(r"[\\/]", name or "")[-1].strip()
    if not name or name.startswith((".", "~")) or not re.fullmatch(r"[\w .()\-]+", name):
        raise Rejected(f"file name not accepted: {name or '(empty)'}")
    if Path(name).suffix.lower() not in ALLOWED:
        raise Rejected(f"{name}: only .csv and .xlsx reports are read")
    return name


def added(month, uploads=None):
    """The files added for `month` so far, by name."""
    folder = Path(uploads or UPLOADS) / check_month(month)
    return sorted(p.name for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []


def save(month, name, data, uploads=None):
    """Keep one added file. A second file of the same name replaces the first."""
    name = safe_name(name)
    if not data:
        raise Rejected(f"{name} is empty")
    if len(data) > MAX_BYTES:
        raise Rejected(f"{name} is larger than {MAX_BYTES // (1024 * 1024)} MB")
    if name not in added(month, uploads) and len(added(month, uploads)) >= MAX_FILES:
        raise Rejected(f"{MAX_FILES} files are already added for {month}")
    folder = Path(uploads or UPLOADS) / check_month(month)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return folder / name


def clear(month, uploads=None):
    """Take the added files of `month` away again (to start the month over). The sample folders are never touched."""
    folder = Path(uploads or UPLOADS) / check_month(month)
    if folder.is_dir():
        shutil.rmtree(folder)


def last_inboxes(month, out):
    """The inboxes the month's last close read, from its status file."""
    status = Path(out) / "close" / month / f"close_status_{month}.json"
    if not status.exists():
        raise Rejected(f"no close has run for {month} yet: run the month-end close first")
    return [(ROOT / p) if not Path(p).is_absolute() else Path(p) for p in json.loads(status.read_text(encoding="utf-8"))["inboxes"]]


def rerun(month, uploads=None):
    """Run the month's close again on the inboxes of its last run plus the added files, then rebuild the portal.
    Returns (it wrote its files, the lines it printed)."""
    from reports import hub, run_scheduled
    folder = (Path(uploads or UPLOADS) / check_month(month)).resolve()
    inboxes = [p for p in last_inboxes(month, run_scheduled.OUT) if p.resolve() != folder]
    if added(month, uploads):
        inboxes.append(folder)
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        ok = run_scheduled.close_from(month, inboxes)
        hub.build(run_scheduled.REPORTS)
    return ok, log.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--add", nargs="*", default=[], help="report files to add")
    ap.add_argument("--clear", action="store_true", help="take the added files away first")
    args = ap.parse_args(argv)
    try:
        if args.clear:
            clear(args.month)
        for path in args.add:
            print(f"added {save(args.month, Path(path).name, Path(path).read_bytes()).name}")
        ok, log = rerun(args.month)
    except Rejected as e:
        raise SystemExit(f"close_upload: {e}")
    print(log, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
