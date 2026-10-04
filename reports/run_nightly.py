"""Nightly run, end to end, with step-by-step logging (task P-O4; store and KPI steps V2.11).

Stand-in for a scheduler: it runs once when called. In production, Windows Task Scheduler
or cron would call it after staff drop the day's exports into the inbox.

    python -m reports.run_nightly --scenario day_ebay_missing [--open] [--pace 0.5]

Steps: check the inbox -> engine (parse, clean) -> pulse (calculate) -> store (load the night)
-> internal API (snapshot into the store) -> KPIs (day, week to date, month to date)
-> render (HTML, CSV, email).
Runs the real pipeline: `python -m engine run` (Victor), `python -m recon.pulse` (Dani),
`python -m engine.store load` and `python -m engine.internal_api pull` (Victor), `python -m recon.kpi`
(Dani). Each scenario runs in its own folder `out/<scenario>/`, emptied first, so one scenario's pulse
files never serve as another's "prior day"; the store (`ECOM_DB`, default out/store/ecom.db) keeps
every night. A failure in the store, internal or KPI step is logged and the night goes on, because the
pulse page doesn't depend on them; the command then exits 1. --simulated is a fallback for a live demo
if something breaks: it builds the pulse from the scenario's answer key instead, skips the store and
KPI steps (there are no transactions to store), and the log says SIMULATED.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from datetime import date, datetime
from pathlib import Path

from reports import hub, mock_pulse, pulse as renderer

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample"
# Filename prefixes per marketplace: the seller-portal samples, then Goodwill's tools
# (Upright "paid_orders_*" for ShopGoodwill, Cash Monkey "orders2023-*" for eBay and Amazon).
EXPECTED_SOURCES = {"shopgoodwill": ("shopgoodwill", "sg_", "paid_orders"), "ebay": ("ebay", "orders2023"),
                    "amazon": ("amazon", "orders2023")}
ENGINE_CMD = ["-m", "engine", "run", "--inbox", "{inbox}", "--out", "{out}", "--date", "{date}"]
PULSE_CMD = ["-m", "recon.pulse", "--date", "{date}", "--in-dir", "{out}"]
STORE_CMD = ["-m", "engine.store", "load", "--in-dir", "{out}", "--date", "{date}"]
PULL_CMD = ["-m", "engine.internal_api", "pull", "--date", "{date}"]
KPI_CMDS = [["-m", "recon.kpi", "--date", "{date}"],
            ["-m", "recon.kpi", "--week", "{week}", "--through", "{date}"],
            ["-m", "recon.kpi", "--month", "{month}", "--through", "{date}"]]

STEPS = 7
PACE = 0.0


def log(msg, step=None):
    tag = f"[{step}/{STEPS}] " if step else ""
    print(f"{datetime.now():%H:%M:%S}  {tag}{msg}", flush=True)
    time.sleep(PACE)


def run(cmd, fatal=True, **fmt):
    """Run one pipeline command. A fatal step stops the night; a non-fatal one returns False."""
    args = [sys.executable] + [a.format(**fmt) for a in cmd]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    for line in (result.stdout + result.stderr).strip().splitlines():
        print(f"            | {line}")
    if result.returncode:
        if fatal:
            raise SystemExit(f"step failed: {' '.join(args[1:])} (exit {result.returncode})")
        print(f"            FAILED: {' '.join(args[1:])} (exit {result.returncode}); the night goes on")
    return result.returncode == 0


def check_inbox(inbox):
    files = sorted(f for f in inbox.iterdir() if f.is_file())
    log(f"Inbox {(inbox.relative_to(ROOT) if inbox.is_relative_to(ROOT) else inbox).as_posix()}: {len(files)} file(s)", 1)
    for f in files:
        print(f"            {f.name:<45} {f.stat().st_size / 1024:>6.1f} KB")
    for source, prefixes in EXPECTED_SOURCES.items():
        hits = [f.name for f in files if f.name.lower().startswith(prefixes)]
        status = f"OK ({len(hits)} file{'s' if len(hits) > 1 else ''})" if hits else "MISSING: will show as 'No data', not $0"
        print(f"            {source:<14} {status}")


def main(argv=None):
    global PACE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scenario", required=True, help="sample under data/sample/ (day_clean, day_refund, ...)")
    ap.add_argument("--simulated", action="store_true", help="fallback: pulse from the answer key, no engine")
    ap.add_argument("--real", action="store_true", help=argparse.SUPPRESS)  # old flag; real is the default now
    ap.add_argument("--open", action="store_true", help="open the page in the browser when done")
    ap.add_argument("--pace", type=float, default=0.0, help="seconds between log lines, for live demos")
    args = ap.parse_args(argv)
    PACE = args.pace

    inbox = SAMPLES / args.scenario / "inbox"
    key = json.loads((SAMPLES / args.scenario / "expected.json").read_text(encoding="utf-8"))
    day = key["business_date"]
    if not day:
        raise SystemExit("pick a day_* scenario (the nightly run covers one business day)")
    out = ROOT / "out" / args.scenario
    shutil.rmtree(out, ignore_errors=True)
    rel = out.relative_to(ROOT).as_posix()
    started = time.perf_counter()
    print(f"\n== Goodwill Michiana nightly pulse - business date {day} ==\n")

    check_inbox(inbox)

    if not args.simulated:
        log(f"Engine: parse, clean, dedupe -> {rel}/transactions.csv", 2)
        run(ENGINE_CMD, inbox=inbox, out=out, date=day)
        log(f"Pulse: revenue, orders, customers by marketplace -> {rel}/pulse/{day}.json", 3)
        run(PULSE_CMD, date=day, out=out)
        p = json.loads((out / "pulse" / f"{day}.json").read_text(encoding="utf-8"))
    else:
        log("Engine: SIMULATED (fallback; pulse built from the sample answer key)", 2)
        log(f"Pulse: SIMULATED -> {rel}/pulse/{day}.json", 3)
        p = mock_pulse.build(args.scenario)[-1]
        (out / "pulse").mkdir(parents=True, exist_ok=True)
        (out / "pulse" / f"{day}.json").write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    # File the night's pulse in the shared history (out/pulse/, as in docs/contracts/pulse.md),
    # which the weekly dashboard and monthly scorecard read.
    archive = ROOT / "out" / "pulse"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / f"{day}.json").write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    ent = p["enterprise"]
    print(f"            enterprise revenue {renderer.money(ent['revenue_cents'])}, {ent['orders']} orders; "
          f"marketplaces with data: {', '.join(ent['included']) or 'none'}")
    if ent.get("excluded"):
        print(f"            excluded (no data): {', '.join(renderer.excluded_keys(ent))}")
    dq = (p.get("data_quality") or {}).get("by_kind") or {}
    if dq:
        print("            data quality: " + ", ".join(f"{n} {k} rows" for k, n in dq.items()))

    failed = [] if args.simulated else store_and_kpis(out, day)
    if args.simulated:
        log("Store, internal API, KPIs: SKIPPED (simulated pulse; no transactions to store)", 4)

    log("Render: dashboard page, CSV, email copy", 7)
    paths = renderer.render(p, ROOT / "reports" / "pulse")
    for path in paths:
        print(f"            {path.relative_to(ROOT).as_posix()}")
    print(f"            {hub.build().relative_to(ROOT).as_posix()} (portal)")

    print(f"\n   {renderer.summary_line(p)}\n")
    log(f"Done in {time.perf_counter() - started:.1f}s"
        + (f"; FAILED: {', '.join(failed)} (the pulse page is up to date, the KPIs may not be)" if failed else ""))
    if args.open:
        webbrowser.open(paths[0].resolve().as_uri())
    return 1 if failed else 0


def store_and_kpis(out, day):
    """Steps 4 to 6: load the night into the store, pull the internal snapshot, compute the KPIs.
    Returns the names of the steps that failed."""
    failed = []
    log(f"Store: load the night into the database ({os.environ.get('ECOM_DB') or 'out/store/ecom.db'})", 4)
    if not run(STORE_CMD, fatal=False, out=out, date=day):
        return ["store load", "internal pull", "KPIs"]  # nothing new to pull or compute from
    log("Internal API: labor, listings, costs, categories -> store (SIMULATED internal data)", 5)
    if not run(PULL_CMD, fatal=False, date=day):
        failed.append("internal pull")
    iso = date.fromisoformat(day).isocalendar()
    log("KPIs: the 15 scorecard KPIs for the day, the week to date and the month to date -> out/kpi/", 6)
    for cmd in KPI_CMDS:
        if not run(cmd, fatal=False, date=day, week=f"{iso.year}-W{iso.week:02d}", month=day[:7]):
            failed.append("KPIs " + cmd[3].lstrip("-"))
    return failed


if __name__ == "__main__":
    sys.exit(main())
