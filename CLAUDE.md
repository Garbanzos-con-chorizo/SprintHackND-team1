# Sprint Hack ND — Team 1

Hackathon project, 3 humans, each driving their own AI agent(s) in parallel. The problem statement is **not known yet** — see `docs/PROBLEM.md` (fill in first thing). Speed matters, but so does not breaking each other's work.

> TODO (team): replace the `<...>` placeholders below once the problem, stack and lanes are known.

## Project snapshot (keep current — edit in place)
- **Problem:** see `docs/PROBLEM.md`
- **Stack:** `<TBD>`
- **Run / test / lint:** `<TBD>` (agents: once known, put exact commands here)
- **Demo deadline:** `<TBD>`  · **Demo flow:** `docs/PROBLEM.md#demo`

## Team and lanes
Each person owns a **lane** = a set of directories. You edit freely inside your lane; anything outside it needs a claim or a contract change (below).

| Member | GitHub | Lane (dirs it owns) | Branch prefix |
|--------|--------|---------------------|---------------|
| A | `<handle>` | `<e.g. backend/, api/>` | `a/` |
| B | `<handle>` | `<e.g. frontend/>` | `b/` |
| C | `<handle>` | `<e.g. data/, ml/, docs/pitch>` | `c/` |

Shared ground (touch carefully): root config, `package.json`/lockfiles/dependency files, `docs/contracts/`, this file. Default owner of shared files = whoever claims them in `docs/CLAIMS.md`.

## Rules for AI agents (read before editing anything)
1. **Know who you work for.** Your human's identity = their `docs/members/<name>.md`. Ask if unclear. Work only in their lane unless told otherwise.
2. **Start of session:** `git pull --rebase origin main`, then read `docs/PROBLEM.md`, `docs/CLAIMS.md`, all `docs/members/*.md` (teammates' status), and recent `docs/decisions/`. Run `/sync`.
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
docs/CLAIMS.md            who is touching which shared file right now
docs/members/<name>.md    per-person status, requests inbox (each person edits only their own)
docs/contracts/*.md       cross-lane interfaces (API, schemas, formats)
docs/decisions/NNN-*.md   append-only decision log (one file per decision)
.claude/commands/         shared slash commands: /sync /claim /handoff /decide
```
Source code goes in lane directories (see table). Create new top-level dirs only inside your lane or via a decision record.

## Handoff protocol (agent → agent)
When pausing or finishing a chunk, run `/handoff`: commit, push, and update your status file so a fresh agent (yours or a teammate's) can continue without chat history. Status entries must include: branch, what works, how to run it, known issues, next step.

## Conventions
- Keep files small and single-purpose; prefer new files over growing shared ones.
- Match the style of the surrounding code; add comments only where intent isn't obvious.
- Commit messages: imperative, prefixed by lane, e.g. `backend: add /predict endpoint`.
