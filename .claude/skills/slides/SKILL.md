---
name: slides
description: Design, write and QA a pitch or demo deck (hackathon, partner, judges). Use when asked to make, rework, critique or polish slides or a presentation. Combines assertion-evidence titles, Swiss-grid layout, one-number-per-slide, density modes, preview-first style choice and a mandatory lint + visual QA loop. Builds decks from a JSON content file with the repo's deck tools instead of hand-writing HTML.
---

# Slides

Distilled from: frontend-slides (Zara Zhang, MIT), guizang-ppt-skill Swiss style (ideas only, AGPL, no text copied), Anthropic's pptx skill (ideas only), Alley's assertion-evidence research, Duarte/Reynolds, Apple keynote practice, WCAG. Full notes and sources: `reference/research.md` (design) and `reference/copy-and-audience.md` (copy and audience psychology: Mayer, Sweller, Paivio, fluency, Heath). **Research before deciding**: if a choice isn't covered there, research it and add the finding with its source.

## Non-negotiables
1. **Assertion titles.** Every content slide's title is a full-sentence claim the audience should leave with ("Every cent of September matches an independent answer key"), never a topic label ("Accuracy"). Evidence under it proves it.
2. **One idea, one hero number.** At most one big number per slide. Two stats = two slides (Apple). Can't fit? Split; never shrink text.
3. **Glance test (3 s).** A judge must get the slide's point in 3 seconds. Speaker-led decks: ≤ 40 words on the slide, 1–3 points.
4. **Signal over noise.** No drop shadows, gradients, decorative accent bars or card grids "because cards". Separate with whitespace and hairline rules.
5. **Vary layouts.** No two consecutive slides with the same layout. Identical card rows are the #1 "AI slop" tell.
6. **Readable remotely.** Text ≥ 24 px on a 1920×1080 canvas (body 32+). Contrast ≥ 4.5:1 (3:1 at ≥ 44 px). Color never carries meaning alone (say "INCOMPLETE", don't only paint it orange).
7. **No dependencies.** System fonts only (theme `plain`: Georgia + Segoe UI/Helvetica/Arial), no web fonts, CDNs or libraries. Present and record from the one offline file `build_deck.py --html docs/pitch/deck/deck.html`.
8. **No AI tells** (`reference/ai-tells.md`): no tracked-caps eyebrows on every slide, no marketing verbs, no "not just X", no em dashes, no punchy fragments ("Watch it run."), no triads by reflex. Plain, specific, short: ≤ 25 words per slide.
9. **Describe what the program does; never show output numbers from synthetic data** as if they were results (`"no_numbers": true` makes it a lint error). Counts that describe the build are fine only when the user wants them.
10. **Honest.** Every number on a slide traces to a source run or file; synthetic data is labelled on the slide. An overclaim costs more than any design wins (CLAUDE.md rule 14).

## Workflow (follow the SDD skills: `spec` → `plan` → build → `audit`)
1. **Spine and copy first** (`reference/copy-and-audience.md`). Write the story as assertion titles only (one line per slide). Read it top to bottom: it must make the argument without any visuals. Hackathon arc: problem in the partner's words → what we built → the demo → why trust it → honesty (built vs simulated) → limits → the ask.
2. **Pick density.** Speaker-led (talks, recorded demo): 1 idea per slide. Reading-first (handouts): 4–8 points allowed. Default for demos: speaker-led.
3. **Style by showing, not asking.** Build 3 previews of the *real* first slide (one safe, one bold, one wildcard), no "Option A" labels on them; the user picks by looking. Themes: `reference/themes.md`.
4. **Write `content.json`** (schema: `docs/pitch/tools/README.md`) and build with screenshots: `python docs/pitch/scripts/build_deck.py <content.json> --out <dir> --preview`. Typography (curly quotes, en/minus dashes) is applied automatically.
5. **Lint: 0 errors and 0 warnings** (`lint_deck.py`): font floor, word budget, one hero number, layout repetition, shadows, placeholders, sentence titles, title widows and length, straight quotes.
6. **Visual QA on the PNGs** (`<dir>/preview/`): read every screenshot. Check balance (no empty half), widows in body text, wraps inside labels, overlap, contrast, the 3-second point. Lint is an estimate; the screenshot is the truth. Fix, rebuild, re-check. Never publish unseen slides.
7. **Speaker notes** on every slide: what to say (~30–45 s), the number to say aloud, what to point at.

## Layouts (all in `docs/pitch/tools/deckgen.py`)
| Layout | Use for |
|---|---|
| `statement` | Opening/closing claim, the ask, a section break |
| `quotes` | The partner's own words (verbatim, attributed) |
| `hero` | One number that proves the title |
| `ledger` | Exceptions/financial rows: label · amount · status, hairline rules, tabular numerals |
| `columns` | 2–3 parallel steps or phases separated by hairlines (no boxes) |
| `table` | Built-vs-simulated, comparisons |

## Hackathon specifics
- Opening slide = the partner's problem in the partner's words (judged).
- Always a "built vs simulated" slide and a concrete ask the partner judge can say yes to.
- Under a hard time cut, put the most important evidence early; cut slides, not font size.
- Recording: one continuous take; key sentence on screen in case audio doesn't carry.
