# Audit, phase 0 (process and tooling) — 2026-10-04

- PASS — T001 — `.claude/skills/{slides,spec,plan,audit}/SKILL.md` exist with frontmatter
- PASS — T002 — `python -m pytest docs/pitch/tools -q`: 2 passed (every layout renders lint-clean; lint catches repeats, label titles, placeholders, missing notes)
- PASS — T003 — `new_spec.py` scaffolded this folder; `audit_phase.py --phase 0` runs
- PASS — T004 — claim row in `docs/CLAIMS.md`; `docs/decisions/012-agent-skills-and-sdd.md`
- OPEN — spec has 1 [NEEDS CLARIFICATION] (team name): blocks phase 3, not phase 1
