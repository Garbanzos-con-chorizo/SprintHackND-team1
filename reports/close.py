"""Month-end close in one command: Goodwill's six steps, an archive of the run and a status file (D3.7).

    python -m reports.close --inbox data/sample/messy_month/inbox --month 2026-09
    python -m reports.close --inbox DIR --inbox DIR2 --month 2026-09 --out out/close --archive out/archive

It runs what used to be three commands (`reports.reconcile`, `reports.bc_export`, `reports.close_report`)
in the order of Goodwill's target close (their deck, slide 40) and prints one line per step:

  01 ACQUIRE           every --inbox is gathered into <out>/<month>/inbox/ (emptied first)
  02 ARCHIVE           the gathered files are copied to <archive>/Accounting/Month End/<year>/<month>/
                       Journal Entries/E-Commerce JEs/<run id>/inputs/ (the folder names of slide 39,
                       under a local root: this is not Goodwill's shared drive)
  03 ENRICH            the engine reads them: every row gets its marketplace, source file and row
  04 APPLY RULES       `reconcile.build`: the month's range, deposits matched to payouts, payout windows
  05 CREATE BC OUTPUT  `bc_export`: General Journal lines, AR invoice lines, control totals, exceptions
  06 POST + RECONCILE  each source's status. NOTHING IS POSTED: there is no Business Central connection.
                       The output is import files, and the status file says `not_posted`.

Then it writes close_status_<month>.json, copies the outputs next to the archived inputs with a
manifest.json (bytes, SHA-256, rows read and rejected per input file), appends a line to runs.csv and
renders the page. Contract: docs/contracts/close-outputs.md.

Exit codes: 0 = files written, whatever the statuses. 1 = refused (two inboxes hold a file of the same
name, a journal document does not sum to 0.00, ...): no CSV, page, status file or runs.csv line is
written. 2 = the written files failed the read-back check: the status file and runs.csv say so, and no
page is rendered.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from reports import bc_export as bc
from reports import close_report, reconcile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "close"
ARCHIVE = ROOT / "out" / "archive"
DEST = ROOT / "reports" / "close"
STEPS = ["ACQUIRE", "ARCHIVE", "ENRICH", "APPLY RULES", "CREATE BC OUTPUT", "POST + RECONCILE"]
RUNS_COLUMNS = ["run_id", "run_at", "inboxes", "journal_lines", "journal_documents", "statuses", "exceptions",
                "needs_review", "exit_code", "archive"]
NO_REVIEW = ("OPEN", "RECONCILED")  # every other status of a source needs a person
NOT_CONNECTED = "no Business Central connection: import files only"
CHECK_FAILED = "the written files failed the read-back check: do not import them"


class Refused(Exception):
    """The close cannot start. Raised before anything is written."""


def say(step, text):
    print(f"{STEPS.index(step) + 1:02d} {step:<17} {text}", flush=True)


def shown(path):
    """A path as the output and the status file show it: relative to the repo when it is inside it."""
    p = Path(os.path.abspath(path))
    return (p.relative_to(ROOT) if p.is_relative_to(ROOT) else p).as_posix()


def fs(path):
    """The same path, for file operations. The archive's folder names are Goodwill's and they are long:
    on Windows the extended-length prefix keeps a deep path under them from hitting the 260-character limit."""
    p = os.path.abspath(path)
    return Path("\\\\?\\" + p) if os.name == "nt" and not p.startswith("\\\\") else Path(p)


def run_folder(archive, month, run_id):
    """Slide 39's own path: Accounting / Month End / year / month / Journal Entries / E-Commerce JEs."""
    return Path(archive) / "Accounting" / "Month End" / month[:4] / month / "Journal Entries" / "E-Commerce JEs" / run_id


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


# ---------------------------------------------------------------- 01 acquire, 02 archive

def inbox_files(inboxes, gathered):
    """Every file the inboxes hold, as [{name, path, inbox}], and how many sub-folders were left alone.
    Only the files directly in each inbox are taken; hidden files (.gitignore) and Excel's lock files
    (~$...) are not inputs, as in the engine. Refuses a missing inbox, an inbox given twice, no files at
    all, and two files of the same name."""
    files, taken, clashes, folders, seen = [], {}, [], 0, set()
    for inbox in inboxes:
        here = Path(os.path.abspath(inbox))
        if not here.is_dir():
            raise Refused(f"inbox {shown(here)} is not a folder")
        if here in seen:
            raise Refused(f"inbox {shown(here)} is given twice")
        if here == gathered or gathered in here.parents:
            raise Refused(f"inbox {shown(here)} is the folder the close gathers into and empties: pass the original inbox")
        seen.add(here)
        for p in sorted(here.iterdir()):
            if p.is_dir():
                folders += 1
            elif not p.name.startswith((".", "~$")):
                key = p.name.casefold()  # Windows would write "A.csv" and "a.csv" to the same file
                if key in taken:
                    clashes.append(f"{p.name} ({taken[key]} and {shown(here)})")
                else:
                    taken[key] = shown(here)
                    files.append({"name": p.name, "path": p, "inbox": shown(here)})
    if clashes:
        raise Refused("two inboxes hold a file of the same name, and the close cannot tell which one to read: "
                      + "; ".join(clashes) + ". Rename or remove one and run again")
    if not files:
        raise Refused("no files in " + ", ".join(shown(i) for i in inboxes))
    return files, folders


def copy_all(files, dest):
    dest.mkdir(parents=True)
    for f in files:
        shutil.copy2(f["path"], dest / f["name"])


# ---------------------------------------------------------------- 03 enrich

def month_rows(engine, month):
    """Rows of the month in the engine's transactions.csv, rows it holds outside the month, and how many
    of the month's rows carry their marketplace, source file and source row."""
    with open(engine / "transactions.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    mine = [r for r in rows if r["business_date"].startswith(month)]
    labelled = sum(bool(r["marketplace"] and r["source_file"] and r["source_row"]) for r in mine)
    return len(mine), len(rows) - len(mine), labelled


def engine_counts(engine):
    """Per input file, from the engine's own output: the rows it kept (every CSV it wrote that has a
    `source_file` column: transactions, payouts, bank lines), the rows it left out by kind (warnings.json:
    duplicates counted once elsewhere, bad amounts, bad dates) and its remark on the file as a whole."""
    read, rejected, notes = Counter(), defaultdict(Counter), {}
    for table in sorted(engine.glob("*.csv")):
        with open(table, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if "source_file" in (reader.fieldnames or []):
                read.update(r["source_file"] for r in reader)
    for w in json.loads((engine / "warnings.json").read_text(encoding="utf-8")):
        if w.get("source_row"):
            rejected[w.get("source_file") or ""][w["kind"]] += 1
        else:  # row 0: the engine speaks of the whole file (for example "no source recognizes this file")
            notes[w.get("source_file") or ""] = f"{w['kind']}: {w.get('reason', '')}"
    return read, rejected, notes


# ---------------------------------------------------------------- status, manifest, run history

def build_status(head, payload, mapping, control, invoice, exceptions, n_lines, n_docs, problems, kept):
    """close_status_<month>.json (docs/contracts/close-outputs.md). `posting.status` is always
    "not_posted": this command has no way to post."""
    key = {m["Label"]: src for src, m in mapping.items()}  # control rows carry the label, the status the key
    sources = {key.get(r["Source"], r["Source"]): {"status": r["Status"], "open_cents": r["Open Balance"],
                                                   "unexplained_cents": r["Unexplained"]} for r in control}
    review = (bool(problems) or any(s["status"] not in NO_REVIEW for s in sources.values())
              or any(e.get("effect") == "not_posted" for e in exceptions))
    return {**head, "origin": payload.get("origin") or payload.get("mock"), "sources": sources,
            "journal": {"lines": n_lines, "documents": n_docs,
                        "balanced": not any(p.startswith("journal document") for p in problems)},
            "invoices": {"documents": len({line["Document No."] for line in invoice}), "lines": len(invoice)},
            "exceptions": {"total": len(exceptions), "by_kind": dict(sorted(Counter(e["kind"] for e in exceptions).items()))},
            "needs_review": review,
            "posting": {"status": "not_posted", "reason": CHECK_FAILED if problems else NOT_CONNECTED,
                        "checks": ["every document sums to 0.00", "files read back and re-checked"],
                        "problems": problems},
            "archive": shown(kept)}


def build_manifest(head, kept, files, engine, outputs):
    """manifest.json: what went into the run and what came out, hashed from the archived copies."""
    read, rejected, notes = engine_counts(engine)
    inputs = []
    for f in files:
        name, copy = f["name"], fs(kept) / "inputs" / f["name"]
        entry = {"name": name, "inbox": f["inbox"], "bytes": copy.stat().st_size, "sha256": sha256(copy),
                 "rows_read": read[name], "rows_rejected": sum(rejected[name].values()),
                 "rejected_by_kind": dict(sorted(rejected[name].items()))}
        if name in notes:
            entry["note"] = notes[name]
        elif not read[name] and not rejected[name]:  # an empty report, or a file the engine does not open (a PDF)
            entry["note"] = "the engine wrote no row and no warning for this file"
        inputs.append(entry)
    return {**head, "inputs": inputs,
            "outputs": [{"name": n, "bytes": (fs(kept) / n).stat().st_size, "sha256": sha256(fs(kept) / n)}
                        for n in outputs]}


def append_run(path, row):
    """One line per run in runs.csv, header on the first write. Returns how many runs it now holds."""
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RUNS_COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)
    with open(path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- the run

def run(inboxes, month, out=OUT, archive=ARCHIVE, dest=DEST, run_id=None):
    """The whole close; returns the exit code. Raises Refused while nothing has been written yet."""
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise Refused("--month must look like 2026-09")
    now = datetime.now().astimezone()
    run_id = run_id or f"{now:%Y-%m-%dT%H-%M-%S}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise Refused("--run-id is a folder name: letters, digits, dot, dash and underscore only")
    folder = Path(os.path.abspath(out)) / month
    gathered, engine, kept = folder / "inbox", folder / "engine", run_folder(archive, month, run_id)
    files, folders = inbox_files(inboxes, gathered)
    if fs(kept).exists():
        raise Refused(f"run {run_id} is already in the archive ({shown(kept)}); an archived run is never overwritten")
    try:
        mapping = bc.load_mapping()
    except ValueError as e:
        raise Refused(str(e))
    head = {"month": month, "run_id": run_id, "run_at": now.isoformat(timespec="seconds"),
            "inboxes": [shown(i) for i in inboxes]}

    if gathered.exists():
        shutil.rmtree(gathered)
    copy_all(files, gathered)
    say("ACQUIRE", f"{len(files)} files from {len(inboxes)} inbox{'es' if len(inboxes) > 1 else ''}, gathered in "
                   f"{shown(gathered)}"
                   + (f" ({folders} sub-folder(s) not read: pass each as its own --inbox)" if folders else ""))

    copy_all([{**f, "path": gathered / f["name"]} for f in files], fs(kept) / "inputs")
    say("ARCHIVE", f"inputs copied to {shown(kept)}/inputs")

    try:
        payload = reconcile.build(gathered, month, mapping, engine)
    except SystemExit as e:  # the engine run failed, or a rule in bc_mapping.csv cannot be read
        print(f"REFUSED: {e}", file=sys.stderr)
        print("posting: NOT POSTED (refused: no import files written)")
        return 1
    write_json(folder / f"close_payload_{month}.json", payload)
    n_rows, outside, labelled = month_rows(engine, month)
    say("ENRICH", f"{n_rows:,} rows for {month}-01 to {payload['posting_date']}, "
                  + ("each with its marketplace, source file and row" if labelled == n_rows
                     else f"{labelled:,} of them with their marketplace, source file and row")
                  + (f" ({outside} dated outside the month left out)" if outside else ""))
    matched = sum(bool(d.get("matches")) for d in payload["deposits"])
    read = sum(not p.get("inferred") for p in payload["payouts"])
    say("APPLY RULES", f"{len(payload['deposits'])} deposits classified ({matched} matched to payouts), "
                       f"{read} payouts read, {len(payload['exceptions'])} exceptions")

    journal, invoice, control, exceptions = bc.build(payload, mapping)
    bad = bc.unbalanced(journal)
    if bad:
        say("CREATE BC OUTPUT", f"REFUSED: {len(bad)} journal document(s) do not sum to 0.00; no import file written")
        for doc, c in bad.items():
            print(f"REFUSED: document {doc} does not balance (off by {bc.dollars(c)})", file=sys.stderr)
        print("No journal, page or status file written. Fix the payload or bc_mapping.csv and run again.",
              file=sys.stderr)
        print("posting: NOT POSTED (refused: no import files written)")
        return 1
    paths = bc.write(folder, month, journal, invoice, control, exceptions, mapping)
    problems, n_lines, n_docs = bc.verify_files(paths)
    status = build_status(head, payload, mapping, control, invoice, exceptions, n_lines, n_docs, problems, kept)
    say("CREATE BC OUTPUT", (f"journal: {n_lines} lines in {n_docs} documents, every document sums to 0.00"
                             if not problems else "CHECK FAILED on the files read back")
                            + f"; invoices: {status['invoices']['documents']} document(s), {len(invoice)} lines")
    for p in problems:
        print(f"CHECK FAILED: {p}", file=sys.stderr)

    say("POST + RECONCILE", "; ".join(
        f"{r['Source']} {r['Status']}" + (f" (unexplained {bc.dollars(r['Unexplained'])})" if r["Unexplained"] else "")
        for r in control) + f"; {len(exceptions)} exceptions" + (", needs review" if status["needs_review"] else ""))

    # Evidence of the run. The page comes last, so it can show the status and the run history.
    status_path = folder / f"close_status_{month}.json"
    write_json(status_path, status)
    outputs = [*paths.values(), folder / f"close_payload_{month}.json", status_path]
    for p in outputs:
        shutil.copy2(p, fs(kept) / p.name)
    write_json(fs(kept) / "manifest.json", build_manifest(head, kept, files, engine, [p.name for p in outputs]))
    exit_code = 2 if problems else 0
    runs = append_run(folder / "runs.csv", {
        **{k: head[k] for k in ("run_id", "run_at")}, "inboxes": "; ".join(head["inboxes"]),
        "journal_lines": n_lines, "journal_documents": n_docs,
        "statuses": "; ".join(f"{src}={s['status']}" for src, s in status["sources"].items()),
        "exceptions": len(exceptions), "needs_review": str(status["needs_review"]).lower(),
        "exit_code": exit_code, "archive": status["archive"]})
    if not problems:  # files that failed the check are not presented to the people who post
        print(f"   page     {shown(close_report.build(month, src=Path(os.path.abspath(out)), dest=dest))}")
    print(f"   status   {shown(status_path)}")
    print(f"   history  {shown(folder / 'runs.csv')} ({runs} run{'s' if runs != 1 else ''})")
    print(f"posting: NOT POSTED ({CHECK_FAILED})" if problems else "posting: NOT POSTED (import files ready)")
    return exit_code


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inbox", action="append", required=True, help="a folder of month-end files; repeat it for several")
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--out", default=str(OUT), help="default out/close")
    ap.add_argument("--archive", default=str(ARCHIVE), help="root of the archive; default out/archive")
    ap.add_argument("--dest", default=str(DEST), help="where the page goes; default reports/close")
    ap.add_argument("--run-id", help="default: local time as YYYY-MM-DDTHH-MM-SS")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:  # argparse exits 2 on a bad command line; here 2 means something else
        return 1 if e.code else 0
    try:
        return run(args.inbox, args.month, args.out, args.archive, args.dest, args.run_id)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        print("posting: NOT POSTED (refused: nothing written)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
