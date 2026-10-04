# 012 — Shared agent skills and spec-driven development for the pitch

- **Date:** 2026-10-04 · **By:** Orlando · **Status:** proposed (any teammate may object; skills are additive)

**Decision.** Add four project skills in `.claude/skills/`: `slides` (presentation design rules from research), and `spec`, `plan`, `audit` (spec-driven development: spec → phased plan → implement one phase → audit with evidence). Repetitive pitch work is automated in `docs/pitch/tools/` (modules) and `docs/pitch/scripts/` (commands), stdlib only, no new dependency. Specs live in `docs/pitch/specs/<NNN-slug>/`.

**Why.** The deck needed a reproducible design standard, and agents were re-typing slide HTML (slow, token-heavy, rules not checked). SDD adds human gates and an evidence-based audit per phase.

**Sources.** GitHub spec-kit (MIT), AWS Kiro (EARS), frontend-slides (MIT); ideas only from guizang-ppt-skill (AGPL) and Anthropic's pptx skill. Notes: `.claude/skills/slides/reference/research.md`.

**Effect on others.** None unless invoked. Teammates may use `spec`/`plan`/`audit` in their lanes.
