# Sprint Hack ND — Team 1

Hackathon project, 3 humans, each driving their own AI agent(s) in parallel. The partner is **Goodwill Michiana** (Reporting track): see `docs/PROBLEM.md`. Speed matters, but so does not breaking each other's work.

## Project snapshot (keep current — edit in place)
- **Problem:** automate Goodwill's recurring reports: the **nightly pulse** (revenue and customers by marketplace; phase 1, done), the **monthly KPI dashboard** (phase 2, in progress) and the **month-end close to Business Central** (phase 3). Details: `docs/PROBLEM.md`, plan: `docs/PLAN_PHASE_2_3.md`, status: `docs/PHASES.md`.
- **Stack:** Python **3.12+** for the repo (the engine alone also runs on 3.11; `reports/` needs 3.12). Standard library plus `openpyxl`, `tzdata`, `pytest` (`engine/requirements.txt`). SQLite (standard library) for the nightly store. Pages are generated HTML from `reports/`. **Files are the contract between lanes** (CSV and JSON in `out/`). A thin web server is planned (`docs/decisions/008-*`), not built.
- **Run / test / lint:**
  ```
  pip install -r engine/requirements.txt
  python -m pytest engine recon reports -q                      # every test (303 at the time of writing)
  python -m reports.run_nightly --scenario gw_day_clean         # the whole nightly run on sample data
  python -m engine fetch --simulate --date 2026-10-02           # simulated provider emails -> inbox/
  python -m engine run --date 2026-10-02                        # inbox/ -> out/ (clean rows, status, warnings)
  python -m recon.pulse --date 2026-10-02                       # out/ -> out/pulse/<date>.json
  python -m engine.tools.make_sample --scenario messy_day --check --pulse   # engine + pulse vs an independent answer key
  ```
  No linter or formatter is configured. Everything in the samples and simulators is **synthetic**.
- **Demo deadline:** submit by **4:00 PM Sunday Oct 4** (nothing pushed after that counts; the last submission wins). Team code freeze 3:00 PM (`docs/PLAN_PHASE_2_3.md`). Demo 4:30 PM, Pod B, Room 154: a recorded video in Google Slides. **Demo flow:** `docs/PROBLEM.md#demo`, `docs/pitch/`.

## Team and lanes
Each person owns a **lane** = a set of directories. You edit freely inside your lane; anything outside it needs a claim or a contract change (below).

| Member | GitHub | Lane (dirs it owns) | Branch prefix |
|--------|--------|---------------------|---------------|
| Victor | `Garbanzos-con-chorizo` | `engine/` (parsers, cleaning, store, internal API mock, provider simulators). Also, per decision 007, `reports/run_nightly.py`, `run_scheduled.py`, `email_gen.py` and `mock_api.py`, which stay in `reports/` for now. `out/` is generated, never committed. | `victor/` |
| Dani | `dllorens7` | `recon/` (pulse calculation, KPIs) | `d/` |
| Orlando | `VarelaCS` | `data/` (sample inboxes with answer keys), `reports/` (pages, CSV, email layout, Business Central export), `docs/pitch/` | `o/` |

Phase 3 (Business Central) has no single owner: it is split by package in `docs/PLAN_PHASE_2_3.md`. Check the claims file before editing across a lane line.

Shared ground (touch carefully): root config, `package.json`/lockfiles/dependency files, `docs/contracts/`, this file. Default owner of shared files = whoever claims them in `docs/CLAIMS.md`.

## Rules for AI agents (read before editing anything)
1. **Know who you work for.** Your human's identity = their `docs/members/<name>.md`. Ask if unclear. Work only in their lane unless told otherwise.
2. **Start of session:** `git pull --rebase origin main`, then read `docs/PROBLEM.md`, `docs/CLAIMS.md`, all `docs/members/*.md` (teammates' status), `docs/ASSUMPTIONS.md` and recent `docs/decisions/`. Run `/sync`.
3. **Never edit a teammate's lane.** If you need a change there, write a request in `docs/members/<their-name>.md` under "Requests to me" (append only) or tell your human to ping them.
4. **Talk through contracts, not code.** Anything crossing lanes (API shapes, data schemas, function signatures, file formats) lives in `docs/contracts/<name>.md`. Code against the contract, not against a teammate's in-progress implementation. Changing a contract = its own small PR, announced in your status file.
5. **Claim before touching shared files** — add a line to `docs/CLAIMS.md` (file/dir, who, time), release it when merged.
6. **Write-once files beat shared files.** To avoid merge conflicts: log decisions as new files `docs/decisions/NNN-short-title.md`, status in your own `docs/members/<name>.md`. Never reformat or reorder files you don't own.
7. **Small, frequent commits; small PRs.** Commit working increments every ~20–30 min, push, and rebase on `main` often. Never force-push `main`. Never leave `main` broken.
8. **Update your status file** (`docs/members/<name>.md`) at each milestone and before you stop: what's done, in progress, blocked, next. Another agent will rely on it.
9. **Stubs and mocks first.** If you depend on another lane, build against a mock that satisfies the contract so you aren't blocked; swap in the real thing at integration.
10. **Don't add dependencies, rename/move directories, or run repo-wide formatters/codemods** without a decision record — these cause conflicts for everyone.
11. **No secrets in git.** Use `.env` (ignored); document required vars in `.env.example`.
12. **Verify before claiming done:** run the project's test/run command and say what you actually saw. Be honest about what's stubbed or broken.
13. **Prefer the simplest thing that demos well.** It's a hackathon: cut scope, not corners on the demo path.
14. **Say what is simulated.** Synthetic data, mock APIs and stand-ins must be labelled as such in the code, the output and the docs, and never presented as real. The judges check the repo against our "built versus used" text, and an upheld overclaim costs the most points.

## Git workflow
- `main` is always demo-able. Work on short-lived branches: `<member-prefix>/<topic>` (e.g. `a/auth-endpoint`).
- Each agent uses its own **git worktree/branch**, never the same working directory as another agent.
- Flow: branch → commit often → `git pull --rebase origin main` → PR → teammate (or you, if blocked >10 min and CI-less) merges with squash. Use `.github/pull_request_template.md`.
- Conflict in a file you don't own? Take the owner's version and message them; don't resolve by overwriting.
- Last hour before demo: **feature freeze** — only bug fixes and demo polish, one designated integrator merges.

## Where things live
```
CLAUDE.md                 this file — rules + snapshot
docs/PROBLEM.md           problem statement, constraints, judging criteria, demo plan
docs/ASSUMPTIONS.md       every assumption, why we made it, how sure we are
docs/PHASES.md            task status by phase; docs/PLAN_PHASE_2_3.md is the current plan
docs/CLAIMS.md            who is touching which shared file right now
docs/members/<name>.md    per-person status, requests inbox (each person edits only their own)
docs/contracts/*.md       cross-lane interfaces (API, schemas, formats)
docs/decisions/NNN-*.md   append-only decision log (one file per decision)
docs/pitch/               presentation material and the demo scripts
engine/                   Victor: parsers, cleaning, store, internal API mock (see engine/README.md)
recon/                    Dani: pulse and KPI calculation (see recon/README.md)
reports/                  Orlando: pages, CSV, email, Business Central export, nightly run
data/                     Orlando: synthetic sample inboxes with answer keys (data/sample/)
out/, inbox/              generated or dropped files; never committed
.claude/commands/         shared slash commands: /sync /claim /handoff /decide
```
Source code goes in lane directories (see table). Create new top-level dirs only inside your lane or via a decision record.

## Handoff protocol (agent → agent)
When pausing or finishing a chunk, run `/handoff`: commit, push, and update your status file so a fresh agent (yours or a teammate's) can continue without chat history. Status entries must include: branch, what works, how to run it, known issues, next step.

## Conventions
- Keep files small and single-purpose; prefer new files over growing shared ones.
- Match the style of the surrounding code; add comments only where intent isn't obvious.
- Commit messages: imperative, prefixed by lane, e.g. `backend: add /predict endpoint`.
