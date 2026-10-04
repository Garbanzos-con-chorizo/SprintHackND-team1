# Plan: Pitch deck v2 and recorded demo

**Spec:** spec.md · **Status:** Phase 0 done, Phase 1 next

## Approach
Content lives in one JSON file; `deckgen` renders it with Swiss layouts (hairlines, one anchor color, varied layouts) and `lint_deck` enforces the slides skill. Published to the existing Slides artifact so the link stays the same. Chosen over hand-written HTML: rebuilds cost one command instead of re-typing slides (token efficient) and the rules are checked, not remembered.

## Phase 0: Process and tooling
- [x] T001 Skills: `.claude/skills/{slides,spec,plan,audit}`
- [x] T002 [P] Tools: `docs/pitch/tools/deckgen.py`, `lint_deck.py`, tests
- [x] T003 [P] Scripts: `docs/pitch/scripts/build_deck.py`, `new_spec.py`, `audit_phase.py`
- [x] T004 Claim `.claude/skills/` + decision 010
- **Exit criteria:** tools tested; this spec and plan scaffolded by `new_spec.py`.
- **Audit:** `python -m pytest docs/pitch/tools -q`

## Phase 1: Content as claims (US1)
- [ ] T101 `docs/pitch/deck/content.json`: 8 slides, sentence titles, one hero number each, varied layouts, notes
- [ ] T102 Build + lint to 0 errors
- **Exit criteria:** AC-001, AC-002, AC-003, AC-004, SC-001
- **Audit:** `python docs/pitch/scripts/build_deck.py docs/pitch/deck/content.json --out <scratch>`

## Phase 2: Style by preview (US2)
- [ ] T201 [P] Render slide 1 in `swiss`, `keynote`, `ledger`; Orlando picks
- [ ] T202 Publish the chosen theme to the artifact; inspect every slide
- **Exit criteria:** AC-005, AC-006, SC-002

## Phase 3: Submission-ready (US3)
- [ ] T301 Replace numbers with the 13:00 dry-run values; fill team name
- [ ] T302 Export PDF/PPTX → Google Slides; video inserted; sharing checked logged out
- **Exit criteria:** AC-007, SC-003

## Risks and fallbacks
- Numbers move on `main` before 13:00 → keep them in content.json only; one rebuild updates all.
- Google Fonts unavailable offline → export PDF (fonts embedded) for the recording.
