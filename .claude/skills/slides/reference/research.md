# Research notes behind the `slides` skill (2026-10-04)

## Evidence-based principles
- **Assertion-evidence** (Michael Alley, Penn State): sentence headline + visual evidence beat topic-title + bullets on comprehension, fewer misconceptions, better delayed recall. https://pure.psu.edu/en/publications/how-the-design-of-presentation-slides-affects-audience-comprehens/
- **One number per slide** (Apple keynotes, Carmine Gallo): the only number on screen is the one remembered; two stats → two slides. https://www.carminegallo.com/?p=13642
- **Signal-to-noise, restraint** (Reynolds, Presentation Zen; Duarte, slide:ology "glance test"). https://policyviz.com/resources/presentation-books/
- **Accessibility**: ≥ 24 pt minimum for projected/remote, 4.5:1 contrast (3:1 large). https://dis.acm.org/2023/creating-accessible-presentations-videos
- **Hackathon judging**: a clear "why it matters" anchor beats a stronger but confusing project; reward = "does this make the sponsor look good?". https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table/ · https://sustained.substack.com/p/lessons-from-winning-five-hackathons
- **Financial figures**: tabular numerals so amounts align (Stripe practice). https://design.hagicode.com/designs/stripe/DESIGN.md

## Skills compared (top 3 kept)
| Skill | Kept from it |
|---|---|
| frontend-slides (25k★, MIT) https://github.com/zarazhangrui/frontend-slides | 3 real previews to choose a style; density modes; split instead of shrink; "AI slop" list (identical card grids, everything centered, generic fonts, purposeless shadows); fixed 1920×1080 stage |
| guizang-ppt-skill (20.8k★, AGPL, ideas only) https://github.com/op7418/guizang-ppt-skill | Swiss discipline: one saturated anchor color, hairline rules, right angles, extreme type-size contrast, no gradients/shadows; fixed layout set; automated overflow/alignment checks |
| Anthropic pptx skill (ideas only) https://github.com/anthropics/skills | Every slide has a visual element; vary layouts; avoid decorative accent lines; mandatory render-and-inspect QA |
| ppt-master (38k★) — not kept: its value is native editable PPTX objects, which our deck tool already exports | |
