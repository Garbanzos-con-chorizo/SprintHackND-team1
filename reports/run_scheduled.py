"""Scheduler stand-in: what the nightly job does, night by night (decision 005: just after midnight ET).

For business date D (the day that just ended; the job runs on D+1 at 00:15 Eastern):
  1. Nightly pulse for D: the real pipeline (engine + recon.pulse) on the sample inbox whose business
     date is D. Without one, the pulse already in the history (out/pulse/D.json) is re-rendered.
  2. Weekly dashboard if D+1 is a Monday (the Monday-Sunday week that ended on D).
  3. Monthly COO scorecard if D+1 is the 1st (the month that ended on D).
  4. Emails to the active subscribers of each report built (reports/config/subscribers.csv).
In production Windows Task Scheduler or cron starts this once a night; nothing here waits for a clock.

    python -m reports.run_scheduled --date 2026-10-04
    python -m reports.run_scheduled --from 2026-09-27 --to 2026-10-04    # a run of nights
"""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from reports import email_gen, hub, mock_pulse, monthly, pulse, run_nightly, weekly

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample"
HISTORY = ROOT / "out" / "pulse"


def scenario_for(day):
    """The sample inbox for that business date, preferring Goodwill's own report formats (gw_*)."""
    found = []
    for key in sorted(SAMPLES.glob("*/expected.json")):
        if json.loads(key.read_text(encoding="utf-8")).get("business_date") == day.isoformat():
            found.append(key.parent.name)
    return sorted(found, key=lambda n: (not n.startswith("gw_"), n))[0] if found else None


def say(text):
    print(f"\n>>> {text}", flush=True)


def night(day):
    run_day = day + timedelta(days=1)
    say(f"Night of {day:%a %b} {day.day}: job runs {run_day:%a %b} {run_day.day} 00:15 ET")
    built = {}

    sc = scenario_for(day)
    if sc:
        run_nightly.main(["--scenario", sc])
        built["daily"] = day.isoformat()
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
        try:
            monthly.main(["--month", f"{day:%Y-%m}"])
            built["monthly"] = f"{day:%Y-%m}"
        except SystemExit as e:
            print(f"    monthly: skipped ({e})")
    else:
        print("    monthly: not due (not the 1st)")

    written, problems = email_gen.distribute(run_day, built.get("daily"), built.get("weekly"), built.get("monthly"))
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
    for d in days:
        night(d)


if __name__ == "__main__":
    main()
