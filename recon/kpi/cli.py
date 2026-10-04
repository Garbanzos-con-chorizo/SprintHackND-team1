"""python -m recon.kpi --month YYYY-MM | --week YYYY-Www | --date YYYY-MM-DD | --period day|week|month (the latest)"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from . import calc, io, periods, store


def report(con, kind, text=None, through=None, generated_at=None):
    """The KPI file for a period of the open database.

    `text` is the period's id; without it the period is the one of that `kind` that contains
    the latest stored business date. ValueError if there is no such date or the id is bad.
    """
    latest = store.latest_business_date(con)
    if text is None and latest is None:
        raise ValueError("the database has no pulse rows yet, so there is no latest period")
    period = periods.parse(kind, text) if text else periods.containing(kind, latest)
    win = periods.window(period, latest, through)
    prior = periods.prior_window(win)
    windows = (win, prior, periods.prior_window(prior))
    return calc.build(win, *(store.load(con, w.start, w.through) for w in windows), generated_at=generated_at)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kpi",
                                     description="Write the scorecard KPI file for a day, a week or a month.")
    parser.add_argument("--period", choices=periods.TYPES,
                        help="alone: the period of this type that contains the latest stored business date")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--date", help="a day, YYYY-MM-DD")
    which.add_argument("--week", help="an ISO week, YYYY-Www (Monday to Sunday)")
    which.add_argument("--month", help="a month, YYYY-MM")
    parser.add_argument("--through", type=date.fromisoformat,
                        help="last day to cover (default: the period's end, or the latest stored day if earlier)")
    parser.add_argument("--db", type=Path, default=None, help="database (default: $ECOM_DB, else out/store/ecom.db)")
    parser.add_argument("--out-dir", type=Path, default=Path("out") / "kpi", help="where to write (default: out/kpi)")
    args = parser.parse_args(argv)

    given = [(kind, text) for kind, text in (("day", args.date), ("week", args.week), ("month", args.month)) if text]
    kind, text = given[0] if given else (args.period, None)
    if kind is None:
        return _fail("give --period, or one of --date, --week, --month", 2)
    if args.period and args.period != kind:
        return _fail(f"--period {args.period} does not go with --{'date' if kind == 'day' else kind}", 2)

    db = args.db or store.default_path()
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        con = store.connect(db)
        try:
            doc = report(con, kind, text, args.through, generated_at)
        finally:
            con.close()
    except store.StoreError as e:
        return _fail(str(e), 1)
    except ValueError as e:
        return _fail(str(e), 2)

    target = io.write_kpis(args.out_dir, doc)
    try:
        store.save_kpis(db, doc)
    except store.StoreError as e:  # the file is the deliverable; the history in the store is not worth a failure
        print(f"kpi: {e}", file=sys.stderr)
    count = {s: sum(k["status"] == s for k in doc["kpis"]) for s in ("ok", "partial", "no_data")}
    print(f"kpi: wrote {target} ({doc['period']['label']}: {count['ok']} ok, {count['partial']} partial, "
          f"{count['no_data']} no data)")
    return 0


def _fail(message, code):
    print(f"kpi: {message}", file=sys.stderr)
    return code
