# Spec: Pitch deck v2 and recorded demo

**ID:** 001-pitch-deck · **Created:** 2026-10-04 · **Status:** Draft (awaiting Orlando's OK) · **Owner:** Orlando

## Problem (why)
The judges score the opening slide, one continuous take, and honesty about what is simulated (`docs/pitch/presentation_guide.md`). The current deck (artifact 9rNv3bvkMWeohczA5p7X2y, v4) has the right story but the wrong design: identical card rows on 6 of 8 slides, label titles, up to 3 hero numbers per slide, no visual QA. The submission must be a Google Slides link with the video inside, by 15:00 (final 16:00).

## Stories (prioritized)
### US1 (P1): A judge gets the point of every slide in 3 seconds
- **Independent check:** lint passes with 0 errors; a teammate states each slide's point after a 3-second look.
- **Acceptance (EARS):**
  - AC-001 WHEN the deck opens THE first slide SHALL show Goodwill's problem in Goodwill's words, verbatim and attributed.
  - AC-002 WHEN any content slide shows THE slide SHALL have a sentence title (a claim), at most one hero number, no text under 24 px.
  - AC-003 THE deck SHALL include a built-vs-simulated slide and an ask slide; every number SHALL be labelled synthetic.
  - AC-004 IF two consecutive slides share a layout THEN the build SHALL fail.

### US2 (P2): The slides and the product look like one thing
- AC-005 WHEN the video cuts from a slide to the portal THE palette SHALL match the portal (anchor #0054A4, ink #231F20, white).
- AC-006 THE style SHALL be chosen by Orlando from 3 previews of the real first slide.

### US3 (P3): The deck is ready to submit
- AC-007 THE deck SHALL export to PDF/PPTX for Google Slides, and every number on it SHALL match the 13:00 dry run.

## Requirements
- R-001 The deck SHALL be built from `docs/pitch/deck/content.json` by `build_deck.py` (no hand-written HTML).
- R-002 At most 8 slides (guide), 3 minutes or less of talk.
- R-003 Team name on every slide as registered. Name: **Chorizo Power** (Orlando, 2026-10-04).

## Success criteria
- SC-001 `build_deck.py` exits 0 (0 lint errors).
- SC-002 Every slide inspected in Present mode: no overflow, no overlap.
- SC-003 All numbers traced to a command output or file in the audit.

## Constraints
- Freeze and final submission 16:00; first submission 15:00; dry run 13:00.
- Lanes: deck work in `docs/pitch/` (Orlando). Skills in `.claude/skills/` = shared config → claimed + decision 012.
- Simulated: all data, the APIs, 11 of 15 KPIs, BC posting (none), month-end source count.

## Out of scope
Changing product pages; editing the video.

## Open questions
1. ~~Registered team name~~ resolved: Chorizo Power.
2. Month-end source count to state on slide 6 (known at 13:00).
