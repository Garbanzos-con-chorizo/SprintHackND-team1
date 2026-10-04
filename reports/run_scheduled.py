"""Scheduler stand-in: what the nightly job does, night by night (decision 005: just after midnight ET).

For business date D (the day that just ended; the job runs on D+1 at 00:15 Eastern):
  1. Nightly pulse for D: the real pipeline (engine + recon.pulse) on the sample inbox whose business
     date is D. Without one, the pulse already in the history (out/pulse/D.json) is re-rendered.
  2. Weekly dashboard if D+1 is a Monday (the Monday-Sunday week that ended on D).
  3. On the 1st (the month that ended on D): Dani's KPIs from the store (`recon.kpi`), the COO
     scorecard page, and the month-end close. The close is three steps: the month-end sources nobody
     has shown us are written by SIMULATORS standing in for the Controller's manual download (decision 012;
     `engine fetch --simulate --close-month`: synthetic files, labelled as such), the one-command close runs on the month's sample inbox plus
     those files (`python -m reports.close`: import files and a page, nothing posted), and the store
     logs the run (`engine.store log-close`).
  4. Emails to the active subscribers of each report built (reports/config/subscribers.csv): the
     pulse, the weekly dashboard, the scorecard and the close. Written as drafts, never sent.
Each night is also loaded into the store by run_nightly (V2.11), which the KPIs read. The first run
seeds September: mock pulse history for the weekly page, and the real engine into the store.
In production Windows Task Scheduler or cron starts this once a night; nothing here waits for a clock.

    python -m reports.run_scheduled --date 2026-10-04
    python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04    # a run of nights
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from reports import email_gen, hub, mock_pulse, monthly, pulse, run_nightly, weekly

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample"
OUT = ROOT / "out"
REPORTS = ROOT / "reports"
HISTORY = ROOT / "out" / "pulse"
STORE = ROOT / "out" / "store" / "ecom.db"


def scenario_for(day):
    """The sample inbox for that business date, preferring Goodwill's own report formats (gw_*)."""
    found = []
    for key in sorted(SAMPLES.glob("*/expected.json")):
        if json.loads(key.read_text(encoding="utf-8")).get("business_date") == day.isoformat():
            found.append(key.parent.name)
    return sorted(found, key=lambda n: (not n.startswith("gw_"), n))[0] if found else None


def month_inbox(month):
    """The sample inbox holding a whole month for the close (its answer key has close.month)."""
    for key in sorted(SAMPLES.glob("*/expected.json")):
        if (json.loads(key.read_text(encoding="utf-8")).get("close") or {}).get("month") == month:
            return key.parent / "inbox"
    return None


def sh(*args, tail=6):
    """Run `python -m <args>` from the repo root, indent its output, return the exit code."""
    r = subprocess.run([sys.executable, "-m", *args], cwd=ROOT, capture_output=True, text=True)
    for line in (r.stdout + r.stderr).strip().splitlines()[-tail:]:
        print(f"      | {line}")
    return r.returncode


def rel(path):
    """A path as the log prints it: relative to the repo when inside it."""
    path = Path(path)
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def run_close(month, inbox):
    """The month-end close of `month` on the 1st (V3.4). Returns True when the close wrote its files.

    Inboxes: the month's sample inbox; its `periodic/` folder when the sample has one (ShopGoodwill's
    periodic report, which states each payout's period); and the month-end sources written by their
    SIMULATORS (FedEx ledger, carriers' bank feed, Goodwill Books statement, Jewelry Report), which stand in
    for the Controller's manual download (decision 012). The simulated ShopGoodwill periodic report is not
    asked for: the sample months bring their own."""
    sources = OUT / "close_sources" / month
    print(f"    close: {month}: month-end sources from their simulators (synthetic, in place of the Controller's "
          f"download) into {rel(sources / 'inbox')}")
    if sh("engine", "fetch", "--simulate", "--close-month", month, "--inbox", str(sources / "inbox"),
          "--out", str(sources)):
        print("    close: a simulated source failed (see above); the close runs on what arrived")
    inboxes = [inbox] + [p for p in (inbox.parent / "periodic", sources / "inbox") if p.is_dir() and any(p.iterdir())]
    return close_from(month, inboxes)


def close_from(month, inboxes):
    """Run the close of `month` on these inboxes, log it in the store and put its status beside the page.
    Also what the portal's "add missing reports" runs, with the folder of added files as one more inbox."""
    print(f"    close: {month} from {', '.join(rel(p) for p in inboxes)}")
    args = [a for p in inboxes for a in ("--inbox", str(p))]
    code = sh("reports.close", *args, "--month", month, "--out", str(OUT / "close"),
              "--archive", str(OUT / "archive"), "--dest", str(REPORTS / "close"), tail=10)
    sh("engine.store", "log-close", "--month", month, "--exit-code", str(code), "--close-dir", str(OUT / "close"))
    if code:
        print(f"    close: not built (exit {code}, see above); nothing posted")
        return False
    # The status file and the run history beside the page's CSVs, so the portal can link them.
    for name in (f"close_status_{month}.json", "runs.csv"):
        if (OUT / "close" / month / name).exists():
            shutil.copy(OUT / "close" / month / name, REPORTS / "close" / month / name)
    print(f"    close page: {rel(REPORTS / 'close' / f'{month}.html')}")
    return True


def say(text):
    print(f"\n>>> {text}", flush=True)


def night(day):
    run_day = day + timedelta(days=1)
    say(f"Night of {day:%a %b} {day.day}: job runs {run_day:%a %b} {run_day.day} 00:15 ET")
    built = {}

    sc = scenario_for(day)
    if sc:
        run_nightly.main(["--scenario", sc])
        built["daily"] = day.isoformat()  # run_nightly also loads the store and computes the KPIs (V2.11)
    elif (HISTORY / f"{day}.json").exists():
        p = json.loads((HISTORY / f"{day}.json").read_text(encoding="utf-8"))
        pulse.render(p, ROOT / "reports" / "pulse")
        print(f"    nightly: no sample inbox for {day}; re-rendered out/pulse/{day}.json"
              f"{' (mock history)' if p.get('mock') else ''}")
        built["daily"] = day.isoformat()
    else:
        print(f"    nightly: no inbox and no pulse for {day}; daily email skipped")

    if run_day.weekday() == 0:
        year, wk, _ = day.isocalendar()
        try:
            weekly.main(["--date", day.isoformat()])
            built["weekly"] = f"{year}-W{wk:02d}"
        except SystemExit as e:
            print(f"    weekly: skipped ({e})")
    else:
        print(f"    weekly: not due ({run_day:%A})")

    if run_day.day == 1:
        month = f"{day:%Y-%m}"
        print(f"    kpi: {month} from the store")
        sh("recon.kpi", "--month", month)
        try:
            monthly.main(["--month", month])
            if (ROOT / "reports" / "scorecard" / f"month-{month}.html").exists():
                built["monthly"] = month
                # the same KPI file as one CSV for Excel / Power BI, next to the page (V2.8)
                sh("engine.export", "kpi-csv", "--kpi-file", f"out/kpi/month-{month}.json")
                # and printed to a one-page PDF for the email (V2.9); without a browser it says how to print by hand
                sh("engine.export", "pdf", "--kpi-file", f"out/kpi/month-{month}.json")
        except SystemExit as e:
            print(f"    monthly: skipped ({e})")
        inbox = month_inbox(month)
        if inbox:
            if run_close(month, inbox):
                built["close"] = month
        else:
            print(f"    close: no month inbox for {month}")
    else:
        print("    monthly: not due (not the 1st)")

    written, problems = email_gen.distribute(run_day, built.get("daily"), built.get("weekly"), built.get("monthly"),
                                             close=built.get("close"))
    for row in written:
        print(f"    email: {row['Report_Type']:<8} -> {row['Email']}")
    for p in problems:
        print(f"    email skipped: {p}")
    print(f"    outbox: out/outbox/{run_day}/ ({len(written)} email(s), not sent)")
    hub.build()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", type=date.fromisoformat, help="business date D (the day that just ended)")
    ap.add_argument("--from", dest="start", type=date.fromisoformat, help="first business date of a run of nights")
    ap.add_argument("--to", dest="end", type=date.fromisoformat, help="last business date of a run of nights")
    args = ap.parse_args(argv)
    if args.date:
        days = [args.date]
    elif args.start and args.end:
        days = [args.start + timedelta(days=i) for i in range((args.end - args.start).days + 1)]
    else:
        ap.error("give --date, or --from and --to")
    if not any(HISTORY.glob("2026-09-*.json")):
        say("Seeding history: September pulses from the clean_month sample (mock)")
        mock_pulse.main(["--scenario", "clean_month", "--out", str(HISTORY)])
    if not STORE.exists():
        say("Seeding the store: September from the clean_month sample (real engine + pulse)")
        sh("engine.store", "init")
        sh("engine.store", "backfill", "--inbox", "data/sample/clean_month/inbox", "--from", "2026-09-01",
           "--to", "2026-09-30", "--out", "out/backfill")
        # September's growth needs a month to compare with. There is no August sample, so the provider
        # simulators write one (SIMULATED, with their own daily volumes) and the store loads it like any other.
        say("Seeding the store: August from the provider simulators (synthetic; gives September its Revenue Growth)")
        sh("engine", "fetch", "--simulate", "--from", "2026-08-01", "--to", "2026-08-31",
           "--inbox", "out/aug_inbox", "--out", "out/aug_fetch")
        sh("engine.store", "backfill", "--inbox", "out/aug_inbox", "--from", "2026-08-01", "--to", "2026-08-31",
           "--out", "out/backfill_aug")
    for d in days:
        night(d)


if __name__ == "__main__":
    main()
