---
name: plan
description: Spec-driven development, step 2. Turn an approved spec into a phased plan with tasks, exit criteria and an audit checklist per phase, then execute one phase at a time. Use after `spec` is approved, or when the user asks for a phased plan.
---

# Plan (SDD step 2: spec → **plan** → implement by phase → audit)

Merged from spec-kit (plan + tasks, `[P]` parallel markers, tasks grouped by story, constitution gates) and Kiro (design then tasks, one task at a time, human gate).

## Pre-plan gates (stop if any fails)
- **Research done:** `research.md` exists; every approach choice in the plan cites a finding from it (or is labelled an assumption). Unsure? Research more before planning, not after.
- Spec has no `[NEEDS CLARIFICATION]`.
- **Simplicity:** the smallest thing that meets P1; no future-proofing.
- **Automate the repeatable:** anything done twice becomes a tool (`docs/pitch/tools/`, importable) or script (`docs/pitch/scripts/`, runnable). Agents call scripts instead of re-typing output (token efficiency).
- **Lanes:** files outside the owner's lane need a claim (`docs/team/claims.md`) or a request.

## plan.md (next to spec.md; `new_spec.py` scaffolds it)
1. **Approach**: 3–6 lines on how, why this over the alternative, and which `research.md` findings support it.
2. **Phases**: each phase delivers something checkable on its own, in priority order (P1 story first). Per phase:
   - Tasks `T###` with exact file paths; `[P]` if parallelizable; `[US1]` story tag.
   - **Exit criteria**: which spec acceptance criteria (EARS) and SCs this phase satisfies.
   - **Audit command(s)**: the script/test that proves it (e.g. `python docs/pitch/scripts/build_deck.py …`).
3. **Risks** and the fallback for each.

## Execution loop
For each phase: implement → run its audit commands → `audit` skill → tick tasks in plan.md → commit (`<lane>: …`) → short report to the user (≤ 5 lines). Next phase only when the audit passes or the user accepts the gaps.
