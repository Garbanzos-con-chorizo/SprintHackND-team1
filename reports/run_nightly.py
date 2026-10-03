"""Nightly run, end to end, with step-by-step logging (task P-O4).

Stand-in for a scheduler: it runs once when called. In production, Windows Task Scheduler
or cron would call it after staff drop the day's exports into the inbox.

    python -m reports.run_nightly --scenario day_ebay_missing [--open] [--pace 0.5]

Steps: check the inbox -> engine (parse, clean) -> pulse (calculate) -> render (HTML, CSV, email).
By default the engine and pulse steps are simulated from the scenario's answer key, and the log
says so. --real runs `python -m engine run` and `python -m recon.pulse` instead; use it once the
engine reports per-source status (P-V4), otherwise every source shows as missing.
"""
import argparse
import json
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from reports import mock_pulse, pulse as renderer

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample"
# Filename prefixes per marketplace: the seller-portal samples, then Goodwill's tools
# (Upright "paid_orders_*" for ShopGoodwill, Cash Monkey "orders2023-*" for eBay and Amazon).
EXPECTED_SOURCES = {"shopgoodwill": ("shopgoodwill", "sg_", "paid_orders"), "ebay": ("ebay", "orders2023"),
                    "amazon": ("amazon", "orders2023")}
# Real commands, used once the modules are merged (integration task I1).
ENGINE_CMD = ["-m", "engine", "run", "--inbox", "{inbox}", "--out", "{out}", "--date", "{date}"]
PULSE_CMD = ["-m", "recon.pulse", "--date", "{date}", "--in-dir", "{out}"]

STEPS = 4
PACE = 0.0


def log(msg, step=None):
    tag = f"[{step}/{STEPS}] " if step else ""
    print(f"{datetime.now():%H:%M:%S}  {tag}{msg}", flush=True)
    time.sleep(PACE)


def run(cmd, **fmt):
    args = [sys.executable] + [a.format(**fmt) for a in cmd]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    for line in (result.stdout + result.stderr).strip().splitlines():
        print(f"            | {line}")
    if result.returncode:
        raise SystemExit(f"step failed: {' '.join(args[1:])} (exit {result.returncode})")


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
    ap.add_argument("--real", action="store_true", help="run the real engine and pulse commands")
    ap.add_argument("--open", action="store_true", help="open the page in the browser when done")
    ap.add_argument("--pace", type=float, default=0.0, help="seconds between log lines, for live demos")
    args = ap.parse_args(argv)
    PACE = args.pace

    inbox = SAMPLES / args.scenario / "inbox"
    key = json.loads((SAMPLES / args.scenario / "expected.json").read_text(encoding="utf-8"))
    day = key["business_date"]
    if not day:
        raise SystemExit("pick a day_* scenario (the nightly run covers one business day)")
    out = ROOT / "out"
    started = time.perf_counter()
    print(f"\n== Goodwill Michiana nightly pulse - business date {day} ==\n")

    check_inbox(inbox)

    if args.real:
        log("Engine: parse, clean, dedupe -> out/transactions.csv", 2)
        run(ENGINE_CMD, inbox=inbox, out=out, date=day)
        log(f"Pulse: revenue, orders, customers by marketplace -> out/pulse/{day}.json", 3)
        run(PULSE_CMD, date=day, out=out)
        p = json.loads((out / "pulse" / f"{day}.json").read_text(encoding="utf-8"))
    else:
        log("Engine: SIMULATED (sample answer key; --real runs engine/)", 2)
        log(f"Pulse: SIMULATED -> out/pulse/{day}.json (--real runs recon.pulse)", 3)
        p = mock_pulse.build(args.scenario)[-1]
        (out / "pulse").mkdir(parents=True, exist_ok=True)
        (out / "pulse" / f"{day}.json").write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    ent = p["enterprise"]
    print(f"            enterprise revenue {renderer.money(ent['revenue_cents'])}, {ent['orders']} orders; "
          f"marketplaces with data: {', '.join(ent['included']) or 'none'}")
    if ent.get("excluded"):
        print(f"            excluded (no data): {', '.join(renderer.excluded_keys(ent))}")
    dq = (p.get("data_quality") or {}).get("by_kind") or {}
    if dq:
        print("            data quality: " + ", ".join(f"{n} {k} rows" for k, n in dq.items()))

    log("Render: dashboard page, CSV, email copy", 4)
    paths = renderer.render(p, ROOT / "reports" / "pulse")
    for path in paths:
        print(f"            {path.relative_to(ROOT).as_posix()}")

    print(f"\n   {renderer.summary_line(p)}\n")
    log(f"Done in {time.perf_counter() - started:.1f}s")
    if args.open:
        webbrowser.open(paths[0].resolve().as_uri())


if __name__ == "__main__":
    main()
