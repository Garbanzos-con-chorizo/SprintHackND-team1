---
name: report-design
description: Design, restyle or review the Goodwill report pages in reports/ (portal, pulse, scorecards, close, site map). Braun / Dieter Rams minimalism as Apple practices it, one design system in reports/theme.py, modest motion, hover and info popovers, progressive disclosure, one-page print. Use for any change to how a report page looks or behaves, and before calling UI work done.
---

# Report design

The report pages are read by executives and accountants, on screen and on paper. The design has one job: make the
numbers and their status obvious, then get out of the way. "Less, but better" (Dieter Rams).

This skill distils three public design skills, chosen from the most-used on GitHub (October 2026), plus Rams:

| Source | What we kept |
|---|---|
| [anthropics/skills, frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | Ground every choice in the subject; a small named token set; spend boldness in one place and keep the rest quiet; motion that answers a user action beats decoration; remove one accessory before shipping. |
| [vercel-labs/web-interface-guidelines](https://github.com/vercel-labs/web-interface-guidelines) (via vercel-labs/agent-skills `web-design-guidelines`) | The rules list: `:focus-visible` rings, `prefers-reduced-motion`, animate `transform`/`opacity` only, never `transition: all`, tabular figures, hover states that raise contrast, `text-wrap: balance`, semantic `<a>`/`<button>`, icon buttons with `aria-label`. |
| [Leonxlnx/taste-skill, minimalist-skill](https://github.com/Leonxlnx/taste-skill/tree/main/skills/minimalist-skill) | Colour is a scarce resource; 1px hairlines; shadows under 0.05 opacity; radius capped at 14px, pills only for badges; entrances of 12px over ~600ms on an ease-out curve, staggered; 200ms hovers; `scale(.98)` on press. |
| Dieter Rams, ten principles (Braun) | Useful, understandable, unobtrusive, honest, thorough to the last detail, as little design as possible. Braun's grammar: light neutral bodies, one coloured control, instrument-like labels, round indicator lamps. |

Not taken: UI/UX Pro Max (a catalogue of styles; we already have one style), GSAP or any library (pages are static
files with inline CSS and a few lines of script), web fonts (pages travel as email attachments and open offline).

## Principles for these pages

1. **Numbers first.** The default view is values, changes and status. Definitions, formulas, notes and audit detail
   sit one interaction away: the info button, an accordion, an expandable row. Never delete them: print shows them.
2. **One accent.** Goodwill blue `#0054A4` is the only brand colour: links, focus, the Home button, share bars.
   Green, red and orange mean status only (ok, problem, simulated), always as soft tints with the word written.
3. **Honest.** No motion on numbers (no count-ups: a PDF or screenshot could catch a wrong value), no decoration
   that implies data, simulated numbers always badged, missing data says "No data", never 0.
4. **Indicator lamps, not alarms.** A small round dot carries status (Braun's lamps). Only a red lamp may pulse,
   slowly, and it stops under reduced motion.
5. **Quiet surfaces.** Canvas `#F5F5F7`, white cards, 1px `rgba(0,0,0,.06)` borders, shadow at most
   `0 4px 20px rgba(0,0,0,.03)` at rest. Depth comes from spacing and grouping, not shadow.
6. **Every page has a way home** (top bar Home button) and appears on the site map; `python -m reports.sitemap`
   must report 0 problems.

## Tokens (reports/theme.py `:root`; never hard-code a colour in a page module)

- Surfaces: `--canvas #F5F5F7`, `--card #FFF`, `--hair #F0F0F2` (row lines), `--line rgba(0,0,0,.06)`, `--hover #F8F9FA`.
- Text: `--ink #1D1D1F`, `--muted #6E6E73`, `--faint #86868B`.
- Accent: `--accent #0054A4` (+ `--accent-tint`). Status: `--ok #248A3D`, `--bad #D70015`, `--warn #B25900`, each with a `*-bg` tint at 12%.
- Type: system stack (SF Pro, Inter, Segoe UI). Hero numbers 26-32px bold, `letter-spacing:-0.03em`, `tabular-nums`
  everywhere. Small uppercase labels only for category and column heads (11px, 600, +0.05em); everything else
  sentence case.
- Radius: 14px cards, 12px accordions and popovers, 980px pills (badges and buttons only).
- Spacing: 4px base (`--sp-1`..`--sp-7` = 4, 8, 12, 16, 20, 24, 32).

## Motion

| Use | Duration | Easing | What moves |
|---|---|---|---|
| Press | 120ms | `--ease-out` | `scale(.98)` |
| Hover | 200ms | `--ease-out` | colour, shadow, `translateY(-2px)` on cards |
| Reveal (popover, row, accordion) | 240ms | `--ease-out` | opacity + 4-8px translate |
| Page entrance | 560ms | `--ease-out` | opacity + `translateY(12px)`, staggered 50ms, at most 8 steps |
| Data bars | 700ms | `--ease-out` | `transform: scaleX()` from the left |

`--ease-out: cubic-bezier(.2,.8,.2,1)`. Rules: animate `transform` and `opacity` only (colour and shadow on hover
are fine), list properties explicitly, the entrance plays once per page load, anything interactive stays
interruptible. `@media (prefers-reduced-motion: reduce)` removes entrances, pulses and bar growth. `@media print`
sets `animation:none; transition:none` on everything so the PDF shows the final state.

## Hover and disclosure vocabulary

- Cards that are links lift 2px and deepen their shadow; a chevron or arrow slides 2px toward where it goes.
- Text links grow an underline from the left; table rows tint `--hover`; the expandable row's chevron turns 90°.
- Info button `ⓘ`: grey at rest, accent on hover or focus; its popover is dark frosted glass
  (`rgba(29,29,31,.86)`, `backdrop-filter: blur(12px)`), opens on hover or tap, closes on Escape.
- Status pills and lamps get a popover saying what the status means when it isn't obvious (OPEN, PARTIAL).
- Accordions: white, 12px radius, chevron `›`, closed by default; content fades in on open.

## Workflow

1. Read `reports/theme.py` and the page module. Change tokens and shared components in the theme; page modules
   only add layout.
2. Keep the test hooks the tests pin (class names like `tile`, `sim`, `pillar`, `part`, `summary alert`,
   `chg down`, `>RECONCILED<`, the `Download:` and `Period:` lines). Grep `reports/tests` before renaming markup.
3. Rebuild the pages, then verify. All of these, every time:
   - `python -m pytest engine recon reports -q`
   - `python -m reports.sitemap` reports 0 problems and 0 unlinked pages
   - every page prints on one sheet (headless Edge `--print-to-pdf`; scorecards landscape, the rest portrait), and
     the four KPI examples through `engine.export.pdf`
   - screenshots at 1440px and 375px, no horizontal scroll; check a popover, a row and an accordion open
   - reduced motion: nothing moves; print: nothing interactive shows
4. Before finishing, remove one accessory. If a choice would look the same on any other product, reconsider it.
