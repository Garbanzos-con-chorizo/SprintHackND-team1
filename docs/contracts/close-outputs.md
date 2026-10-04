# Contract: close outputs (C3.3): the one-command close and what it leaves behind

- **Owner:** Dani for phase 3 (decision 009). **Producer:** `python -m reports.close` (`reports/close.py`, task D3.7). **Consumers:** Victor's `reports/run_scheduled.py` (runs it on the 1st), `reports/hub.py` (the portal card) and `reports/email_gen.py` (the close email); the close page (`reports/close_report.py`, D3.8).
- **Status:** draft v0.1. Built and checked on the messy month (`reports/tests/test_close.py`). The example below is a real run on `main` at 116b2c2.
- **Plan:** `docs/PLAN_PHASE_3.md`, section 3 (D3.7) and section 4 (C3.3).

## The command
```
python -m reports.close --inbox DIR [--inbox DIR2 ...] --month YYYY-MM
                        [--out out/close] [--archive out/archive] [--dest reports/close] [--run-id ID]
```
Run it from the repo root. It replaces the three commands `reports.reconcile`, `reports.bc_export` and `reports.close_report`, which still work on their own.

| Flag | Meaning |
|---|---|
| `--inbox` | A folder of month-end files. Repeat it when the files arrive in several folders (the sample files and the simulated APIs' files). Only the files directly in the folder are taken: a sub-folder is not read (the `ACQUIRE` line says how many were left alone), and hidden files (`.gitignore`) and Excel's lock files (`~$...`) are skipped, as in the engine. |
| `--month` | `YYYY-MM`. |
| `--out` | Where the month folder goes. Default `out/close`. |
| `--archive` | Root of the archive. Default `out/archive`: a local folder, **not** Goodwill's shared drive. |
| `--dest` | Where the page goes. Default `reports/close`. |
| `--run-id` | Name of this run and of its archive folder. Default: local time as `YYYY-MM-DDTHH-MM-SS`. Letters, digits, dot, dash, underscore. |

It prints one line per step of Goodwill's target close (their deck, slide 40), then where the evidence is, then one `posting:` line, which is always the last line of stdout:
```
01 ACQUIRE           38 files from 1 inbox, gathered in out/close/2026-09/inbox
02 ARCHIVE           inputs copied to out/archive/Accounting/Month End/2026/2026-09/Journal Entries/E-Commerce JEs/2026-10-04T01-17-04/inputs
03 ENRICH            2,357 rows for 2026-09-01 to 2026-09-30, each with its marketplace, source file and row (1 dated outside the month left out)
04 APPLY RULES       23 deposits classified (19 matched to payouts), 31 payouts read, 16 exceptions
05 CREATE BC OUTPUT  journal: 56 lines in 25 documents, every document sums to 0.00; invoices: 1 document(s), 3 lines
06 POST + RECONCILE  eBay OPEN; Amazon INCOMPLETE; ShopGoodwill INCOMPLETE; 16 exceptions, needs review
   page     reports/close/2026-09.html
   status   out/close/2026-09/close_status_2026-09.json
   history  out/close/2026-09/runs.csv (1 run)
posting: NOT POSTED (import files ready)
```
The text is for people and may change. Programs read the **exit code** and the **status file**.

## Exit codes
| Code | Meaning | What is on disk afterwards |
|---|---|---|
| 0 | Files written, **whatever the statuses**. A month with `INCOMPLETE` or `UNEXPLAINED` sources still exits 0: read `needs_review`. | Everything below. |
| 1 | Refused. Before anything is touched: a bad `--month` or `--run-id`, a bad command line, an inbox that is not a folder or is given twice, no files, **two inboxes holding a file of the same name** (compared without case), a run id already in the archive, an unreadable `bc_mapping.csv`. After the inputs are archived: the engine run failed, or **a journal document does not sum to 0.00**. | In the first group, nothing at all. In the second, the gathered inbox, the archived `inputs/`, the engine folder and (for an unbalanced document) the payload; **no CSV, no page, no status file, no `runs.csv` line, no manifest**. Files of an earlier run of the same month stay as they were. |
| 2 | The four CSVs were written and **failed the read-back check**. Do not import them. | The four CSVs, the status file (`posting.problems` lists what failed, `needs_review` is true), the archive with its manifest and a `runs.csv` line with `exit_code` 2. **No page** is rendered: one left by an earlier run still shows that run. |

A refused run leaves no status file of its own, so after a non-zero exit the status file may be an older run's: check the exit code first, then `run_id`.

## Files in `<out>/<month>/`
| File | Written by | Notes |
|---|---|---|
| `inbox/` | step 01 | Every file of every `--inbox`, in one flat folder. **Emptied at the start of each run.** |
| `engine/` | step 03 | The engine's output for the gathered inbox (`docs/contracts/close-inputs.md`). |
| `close_payload_<month>.json` | step 04 | `docs/contracts/close-payload.md`. Its `inbox` field is the gathered folder; the folders the files came from are `inboxes` in the status file. |
| `general_journal_<month>.csv`, `ar_invoice_<month>.csv`, `control_totals_<month>.csv`, `exceptions_<month>.csv` | step 05 | As `reports.bc_export` writes them. Overwritten by each run that gets this far. |
| `close_status_<month>.json` | after step 06 | Below. Overwritten by each run that exits 0 or 2. |
| `runs.csv` | after step 06 | One line per run that exits 0 or 2, appended; header on the first write. |

The page is `<dest>/<month>.html`, with a copy of the four CSVs in `<dest>/<month>/` for its download links, as `reports.close_report` has always written it. It is rendered last, after the status file and `runs.csv` exist.

## The archive
```
<archive>/Accounting/Month End/<year>/<month>/Journal Entries/E-Commerce JEs/<run id>/
    inputs/                        every gathered inbox file, byte for byte
    general_journal_<month>.csv    the outputs of this run
    ar_invoice_<month>.csv
    control_totals_<month>.csv
    exceptions_<month>.csv
    close_payload_<month>.json
    close_status_<month>.json
    manifest.json
```
The folder names are Goodwill's own (slide 39: "Accounting / Month End / year / month / Journal Entries / E-Commerce JEs"); `<month>` is `YYYY-MM`. One folder per run, never overwritten: a run id that is already there is refused. A run folder with `inputs/` and no `manifest.json` is a run that was refused or did not finish. The page is not archived.

`manifest.json`, hashed from the archived copies:
```json
{
  "month": "2026-09", "run_id": "2026-10-04T01-17-04", "run_at": "2026-10-04T01:17:04-04:00",
  "inboxes": ["data/sample/messy_month/inbox"],
  "inputs": [
    { "name": "ebay_transactions_2026-09-15_2026-09-21.csv", "inbox": "data/sample/messy_month/inbox",
      "bytes": 46780, "sha256": "612b5c9c2d210592e13374593a99d322e506f539bad5de9912e0726cc27fb8c5",
      "rows_read": 94, "rows_rejected": 136, "rejected_by_kind": { "bad_amount": 1, "bad_date": 1, "duplicate": 134 } }
  ],
  "outputs": [
    { "name": "general_journal_2026-09.csv", "bytes": 7133,
      "sha256": "6fb7f85aa21ab4bb56e7308e59629aa6e749c5fe58d68dfeee92283bc1deb9fc" }
  ]
}
```
- `rows_read`: rows of that file the engine kept, counted in every CSV of the engine folder that has a `source_file` column (today `transactions.csv`, `payouts.csv`, `bank.csv`).
- `rows_rejected`, `rejected_by_kind`: the entries of the engine's `warnings.json` that name a row of that file. Most are `duplicate`: a row that an overlapping download already delivered, counted once from the other file. A re-downloaded file can therefore read `rows_read` 0 with every row "rejected".
- `note` (only when there is something to say about the file as a whole): the engine's own remark, kind and reason, for example `unparseable: no source recognizes this file`; or, when the engine wrote neither a row nor a warning for it (an empty report, or a file type it does not open, such as a PDF), `the engine wrote no row and no warning for this file`.

## The status file: `close_status_<month>.json`
A real run of `python -m reports.close --inbox data/sample/messy_month/inbox --month 2026-09` (synthetic sample data):
```json
{
  "month": "2026-09",
  "run_id": "2026-10-04T01-17-04",
  "run_at": "2026-10-04T01:17:04-04:00",
  "inboxes": ["data/sample/messy_month/inbox"],
  "origin": "reconciled from the raw inbox",
  "sources": {
    "ebay": { "status": "OPEN", "open_cents": 146556, "unexplained_cents": 0 },
    "amazon": { "status": "INCOMPLETE", "open_cents": 466706, "unexplained_cents": 0 },
    "shopgoodwill": { "status": "INCOMPLETE", "open_cents": 355429, "unexplained_cents": 0 }
  },
  "journal": { "lines": 56, "documents": 25, "balanced": true },
  "invoices": { "documents": 1, "lines": 3 },
  "exceptions": {
    "total": 16,
    "by_kind": { "bad_amount": 1, "bad_date": 1, "duplicate_rows": 1, "in_transit": 3, "missing_report": 2,
                 "not_yet_paid_out": 3, "payout_data_gap": 2, "prior_month_refund": 2, "unmatched_deposit": 1 }
  },
  "needs_review": true,
  "posting": {
    "status": "not_posted",
    "reason": "no Business Central connection: import files only",
    "checks": ["every document sums to 0.00", "files read back and re-checked"],
    "problems": []
  },
  "archive": "out/archive/Accounting/Month End/2026/2026-09/Journal Entries/E-Commerce JEs/2026-10-04T01-17-04"
}
```
| Field | Meaning |
|---|---|
| `month`, `run_id`, `run_at` | The month closed, the run's name, and when it started (local time with its offset). |
| `inboxes` | The `--inbox` folders, relative to the repo when inside it, with forward slashes. |
| `origin` | The payload's description of where it came from (`origin`, or `mock` until D3.2 renames it). |
| `sources` | One entry per posted source, keyed like `Source` in `bc_mapping.csv`. `status` is the control status of `close-payload.md` (`MISMATCH`, `UNEXPLAINED`, `INCOMPLETE`, `OPEN`, `RECONCILED`); `open_cents` and `unexplained_cents` are `Open Balance` and `Unexplained` of `control_totals_<month>.csv`. |
| `journal` | `lines` and `documents` as counted from the file read back. `balanced` is false only on exit 2, when the read-back found a document that does not sum to 0.00. |
| `invoices` | Sales invoice documents and their lines. |
| `exceptions` | The rows of `exceptions_<month>.csv`: `total`, and the count of each kind, sorted by name. |
| `needs_review` | `true` if any source is not `OPEN` or `RECONCILED`, or any exception has effect `not_posted`, or the read-back check failed. |
| `posting.status` | **Always `not_posted`.** The command has no way to post. |
| `posting.reason` | Why: `no Business Central connection: import files only`, or on exit 2 `the written files failed the read-back check: do not import them`. |
| `posting.checks` | The checks that ran before this file was written. |
| `posting.problems` | What the read-back check found. Empty on exit 0. |
| `archive` | This run's archive folder. |

Paths (`inboxes`, `archive`) are relative to the repo when inside it and absolute otherwise.

## `runs.csv`
One line per run that exits 0 or 2, oldest first.

| Column | Value |
|---|---|
| `run_id`, `run_at` | As in the status file. |
| `inboxes` | The inbox folders, joined with `; `. |
| `journal_lines`, `journal_documents` | As in the status file. |
| `statuses` | Each source's status as `key=STATUS`, joined with `; `: `ebay=OPEN; amazon=INCOMPLETE; shopgoodwill=INCOMPLETE`. One column, so the header stays the same when a source is added. |
| `exceptions` | The total. |
| `needs_review` | `true` or `false`. |
| `exit_code` | 0 or 2. |
| `archive` | The run's archive folder. |

## What is not done
- **Nothing is posted to Business Central.** There is no connection to one. The output is import files in the column order of the General Journal and Sales Invoice pages, and they have never been loaded into a Business Central. The command says so on its last line and the status file says `"status": "not_posted"`; there is no other value.
- **The archive is a local folder** that borrows Goodwill's folder names. Nothing is written to their shared drive.
- **No approvals.** `needs_review` is a flag, not a workflow: nobody signs anything off.
- **A refused run (exit 1) is not in `runs.csv`.** Its trace is the terminal output and, if it got that far, an archive folder with `inputs/` and no manifest.
- **The manifest does not say which inputs came from a simulated API.** That is the fetch log's and `source_coverage.json`'s job (V3.3); until then, the inbox each file came from is the only hint.
- **Sub-folders of an inbox are not read.** A file the engine cannot use is still gathered and archived; the manifest lists it with 0 rows and a `note`, and the run goes on.
- The sample months are **synthetic**, and the account, customer and document numbers in the files are placeholders (`docs/contracts/close-payload.md`, `reports/config/bc_mapping.csv`).

## Changelog
- draft v0.1 (2026-10-04, Dani): the command, its exit codes, the month folder, the archive and its manifest, the status file, `runs.csv`. Against the draft in the plan's section 4: `inbox` became the list `inboxes`; added `run_at`, `origin`, `posting.problems` and `archive`; exit 2 writes a status file and a `runs.csv` line so the failure stays on record.
