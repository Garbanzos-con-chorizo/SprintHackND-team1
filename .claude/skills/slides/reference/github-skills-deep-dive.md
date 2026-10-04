# Deep dive: what the best GitHub presentation skills actually do (2026-10-04)

Read in full: frontend-slides (25k★, MIT: SKILL.md, STYLE_PRESETS, the 34-template bold pack, the "Signal", "Raw Grid", "Blue Professional" design.md files), guizang-ppt-skill (20.8k★, AGPL, ideas only: Style B's 22 locked Swiss layouts, screenshot framing, P0–P3 checklist, validators), claude-design-skill (adapted from Claude.ai's design prompt), mblode presentation-creator. Skimmed: html-presentation, claude-skill-deck (McKinsey), deck-factory, skills-slides.

## Why our deck looked bad (diagnosis)
1. **No visual element on any slide**: text in boxes. Every strong skill demands one per slide (diagram, chart, screenshot, giant type).
2. **No system**: sizes, weights and surfaces chosen per slide. The good skills lock a type ladder, two surfaces, one accent, and a fixed layout set.
3. **Weak type contrast**: titles 64 px bold against 32 px body. Swiss/Signal use *extreme* jumps (statement 9–12 vw light weight vs 1 vw body).
4. **No chrome**: real decks have a quiet top bar (metadata left, counter right, hairline under it) that makes every slide read as one document.
5. **Same rhythm everywhere**: no dark "breath" slides alternating with light reading slides.

## Rules adopted (with origin)
| Rule | From |
|---|---|
| Lock the type ladder: serif = voice (titles), sans = substance (body), mono = metadata (chrome, labels). Never cross | Signal |
| Two surfaces alternate (dark for statements/chapters, light for reading); ONE accent used only on rules, emphasis and markers, never body or fills | Signal, Swiss B |
| Signature move: roman headline with one *italic* phrase in the accent color | Signal |
| Chrome bar: mono label left, counter right, 1 px hairline beneath | Signal |
| Flat + hairline: no shadows, no rounded cards, no gradients | Signal, Swiss B, claude-design |
| Extreme type contrast; statement slides ≤ 12 words, light weight, huge | Swiss S03 |
| Fixed layout set; pick, don't improvise: statement, duo compare, linear timeline (square nodes on a 1 px axis), system diagram, closing manifesto | Swiss S03/S08/S11/S17/S09 |
| Data layouts only with real data; otherwise describe | Swiss (S02/S06/S07 "no invented metrics"), claude-design ("decorative stats are lying") |
| Empty space is solved with composition, never filler | claude-design |
| Content fills ≤ half the slide | Signal |
| Screenshots: framed, fit-contain, never redrawn, quiet background | guizang screenshot-framing |
| Placeholder > fake: a labelled placeholder is honest | claude-design |
| Severity checklist P0 (blocks) → P3 (polish); validator script catches centered titles, overflow, undefined layouts | guizang |
| System fonts only is a legitimate design choice (Raw Grid ships with no web fonts) | Raw Grid |

## Our implementation
Theme `signal` in `docs/pitch/tools/deckgen.py`: Georgia (voice) + Segoe UI/Helvetica (substance) + Consolas/Menlo (metadata), navy `#0B2545` and paper `#F7F5F0` surfaces, portal blue `#0054A4` / light `#8FB8E8` accent, chrome bar on every slide. Layouts: `statement`, `quotes`, `system`, `timeline`, `duo`, `points`, `closing`. Emphasis: wrap a phrase in `*…*` in a title to get the italic accent.
