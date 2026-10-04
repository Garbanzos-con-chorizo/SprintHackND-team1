# 009 — Phase 3 split between Dani and Victor; temporary ownership of Orlando's close files

- **Date / author:** 2026-10-04 00:15 EDT, Dani
- **Status:** proposed (needs Victor's response below; Orlando may change it whenever he is back)
- **Changes:** `007-phase-2-3-owners-database-scorecard.md`, point 1 ("phase 3 has no owner yet") and the three packages A, B, C of `docs/PLAN_PHASE_2_3.md`, section 8.
- **Full plan:** `docs/PLAN_PHASE_3.md` (what `main` does today, the gap against deck slides 38 to 42, tasks, contracts, clock, cuts).

## Context
Orlando built the first version of the month-end close (`reports/reconcile.py`, `bc_export.py`, `close_report.py`, the mapping, the messy month and its answer key) and cannot work on it now. Phase 3 was never assigned (007). Checked on `main` at 2fcfafe: the close runs on the messy month and balances, but Amazon is $226.78 off, ShopGoodwill hides a gap of $1,875.64 behind a net, there is no clean month for the close, and the page does not say what is simulated. Victor has only L7 (the demo script) left from phase 2: L1 to L6 and L8 landed tonight. Dani has nothing left.

## Decision
1. **Two parts.** **Dani:** the rules, matching and calculation of the close and their tests; the sample months with their answer keys; the one-command close, its archive and status file; the close page; the rules document and the close demo script. **Victor:** what the engine hands the close (the order time on each transaction, the payout rows, the bank file, which days each report covers), the month-end sources we have never seen, the scheduler, the store's run history, and the rest of his phase 2 list.
2. **The parts meet at two contracts and nowhere else.** `docs/contracts/close-inputs.md` (new, Victor owns, Dani reads) and `docs/contracts/close-outputs.md` (new, Dani owns, Victor's runner and portal read). `docs/contracts/close-payload.md` passes from Orlando to Dani. Until each side's files exist, the other keeps what works today (the readers inside `reports/reconcile.py`; the three commands in `run_scheduled`).
3. **Temporary ownership while Orlando is away.** Nothing is moved or renamed.

   | Files | Held by |
   |---|---|
   | `reports/reconcile.py`, `reports/bc_export.py`, `reports/close_report.py`, `reports/mock_recon.py`, `reports/config/bc_mapping.csv`, `reports/tests/test_reconcile.py`, `reports/tests/test_bc_export.py`, and new `reports/close.py`, `reports/config/close_*.csv`, `reports/tests/test_close*.py` | Dani |
   | `data/generate.py`, `data/sample/messy_month/`, new `data/sample/tidy_month/`, `data/README.md` | Dani |
   | `docs/contracts/close-payload.md`, new `close-outputs.md` and `close-rules.md`, new `docs/pitch/demo_script_close.md` | Dani |
   | `reports/run_scheduled.py`, `run_nightly.py`, `email_gen.py`, `hub.py`, `scorecard.py`, `weekly.py` | Victor (already his by 007 and its last amendment) |
   | Slides, video, submission, and everything else in `reports/`, `data/` and `docs/pitch/` | Orlando |

   It ends when Orlando takes a file back (a line in `docs/CLAIMS.md` or in Dani's or Victor's requests is enough) or at the freeze. Each holder adds their own rows to `docs/CLAIMS.md`.
4. **Two fences.** Dani does not edit `reports/run_scheduled.py` or `reports/hub.py`. Victor does not edit `data/generate.py` or `reports/reconcile.py`. `reconcile.build` keeps its signature, because `engine/tests/test_close_reads_engine_columns.py` calls it.
5. **Victor adds the order time** (`occurred_at`, task V3.1), the one thing Dani's numbers need from the engine. Nobody else edits the engine. If it is not on `main` at 11:00 Sunday, it becomes the only thing he works on. (Dani, 00:35; the first draft let Dani open that PR herself.)
6. **Phase 3 takes no features after 13:00 Sunday**, so the demo can be recorded before the 16:00 freeze. From 15:00 Dani is the one integrator.
7. **The output stays import files, not a posting** (007 point 7, `ASSUMPTIONS.md` 1.2). The page and the files say so, and say that the data is synthetic and the account numbers are placeholders.
8. **The month-end sources we have no file for are built as simulated APIs** (Dani, 00:35). We assume each can be fetched through an API, as Amanda told us to assume for Upright: the Jewelry report, the bank feed for the carriers, Business Central's ledger for FedEx, ShopGoodwill's periodic reports, the Goodwill Books statement (Victor: a simulator, a parser and an answer key each) and Cash Monkey's month file (Dani's generator, since the parser exists; used as a cross-check). The assumption is in `docs/ASSUMPTIONS.md`, section 2c, and it is the first question for Debie on Sunday. Every such source is labelled "simulated API" in the fetch log and on the close page.
9. **Orlando owns the presentation, the recording and the submission**, and is back at 11:00 Sunday (Dani, 00:35). `docs/pitch/presentation_guide.md` is a suggestion for him.

## Consequences
- Dani's agents edit files in Orlando's lane for the weekend; his note is in `docs/members/orlando.md`.
- The sample generator and the parsers are written by different people, so an answer key never comes from the code it checks.
- Six of Goodwill's nine month-end sources come from simulated APIs with layouts we made up. That is more to disclose, not less: the plan lists what we say is simulated and what is not built, and cuts the six one by one, the least defined first.
- The submission has to be a Google Slides link with the video inside it (deck slides 52 and 61), whatever the presentation is built in.
- `docs/PHASES.md` and `docs/TASKS.md` are out of date for phase 3 until task D3.12.

## Response from Victor
**Accepted as written** (2026-10-04, written by Victor's agent on his instruction to finish his phase 3 list; Victor can amend this line). His side is on `main`: V3.1 (#54), V3.2 with C3.1 (#56), V3.3 (#60), V3.5 (#67), V3.7 and V3.9 (#68), V3.8 (#69), V3.10 (#70), V3.4 (#71), V3.6 (#72). Both fences held: nothing of his touches `data/generate.py` or `reports/reconcile.py`. Three small departures from the plan's drafts, all in `docs/contracts/close-inputs.md`: `ledger.csv` has an `entry_no` column; `days_missing` in `source_coverage.json` is `null` for statements and lookups; the simulated ShopGoodwill periodic report is delivered only on request, because the sample months have their own.
