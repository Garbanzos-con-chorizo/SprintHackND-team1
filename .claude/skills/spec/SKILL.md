---
name: spec
description: Spec-driven development, step 1. Turn a request into a reviewable spec (what and why, never how) before any code or slides. Use when starting any feature, deliverable or rework, or when the user says spec, SDD, requirements or "start properly". Scaffold with `python docs/pitch/scripts/new_spec.py <slug>`.
---

# Spec (SDD step 1 of 4: spec → plan → implement by phase → audit)

Merged from GitHub spec-kit (MIT: spec template, `[NEEDS CLARIFICATION]`, prioritized independently testable stories, measurable success criteria) and AWS Kiro (EARS acceptance criteria, human gate between steps). Sources: https://github.com/github/spec-kit/blob/main/spec-driven.md · https://kiro.dev

## Rules
- **What and why only.** No tech, files or layouts here; those go in the plan.
- **Never guess.** Anything unknown is `[NEEDS CLARIFICATION: question]`. Max 3 open at once; ask the user, then remove them. A spec with markers cannot go to `plan`.
- **Stories are prioritized and independently shippable** (P1 alone must already be useful: an MVP).
- **Acceptance criteria in EARS**: `WHEN <trigger> THE <deliverable> SHALL <observable result>`; also `IF <unwanted condition> THEN … SHALL …`. Each one must be checkable by `audit`.
- **Success criteria are measurable** (numbers, yes/no checks), not "looks good".
- **Constraints and honesty**: list deadlines, the repo's lane rules, and what must be labelled simulated.

## Steps
0. **Research first (mandatory).** Before writing requirements, research the problem: repo docs, the partner's material, and outside sources (papers, official docs, well-sourced articles, strong GitHub projects). Write `research.md` next to the spec: each finding with its source link and the decision it drives (`Finding → Source → Decision`). No decision without a source or an explicit "assumption" label (also logged in `docs/ASSUMPTIONS.md`).
1. `python docs/pitch/scripts/new_spec.py <NNN-slug> --title "…"` creates `docs/pitch/specs/<NNN-slug>/spec.md` from `template.md`.
2. Fill it from the request, the repo docs and research. Mark unknowns.
3. Show the user a ≤ 10-line summary + open questions. **Gate:** user approves → run `plan`.
