---
name: audit
description: Spec-driven development, step 4. Audit a finished phase against its spec and plan, with evidence, before moving on. Use after each phase, before a handoff or submission, or when the user asks to check, verify or audit work.
---

# Audit (SDD step 4: spec → plan → implement → **audit**)

From spec-kit's `analyze` (consistency across spec/plan/tasks) plus Kiro's per-requirement verification. An audit reports facts with evidence; it never claims a pass it did not run.

## Steps
1. Run the phase's audit commands from plan.md. Save raw output to the scratchpad, not to chat.
2. `python docs/pitch/scripts/audit_phase.py <spec-dir> --phase N` lists every task, EARS criterion and SC for the phase, and flags: unticked tasks, leftover `[NEEDS CLARIFICATION]`, placeholders `[...]`, criteria with no evidence line.
3. For each criterion write one evidence line in `audit-phaseN.md`: `PASS|FAIL|PARTIAL — <criterion id> — <command/output or file:line>`.
4. Cross-checks: spec ↔ plan ↔ what was built agree; honesty (anything simulated is labelled); lane rules respected; tests still pass (`python -m pytest engine recon reports -q` when code changed).
5. Report to the user in ≤ 6 lines: verdict, fails, what you'd fix. **Gate:** next phase only on PASS or the user's explicit OK.
