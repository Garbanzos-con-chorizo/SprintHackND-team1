# Pitch tools and scripts

`tools/` = importable modules. `scripts/` = commands you run. Rules they enforce: `.claude/skills/slides`. Stdlib only.

| Command | Does |
|---|---|
| `python docs/pitch/scripts/build_deck.py <content.json> --out <dir> [--html deck.html] [--preview]` | Renders the Slides-artifact files and lints them (exit 1 on ERROR); `--html` writes one offline file to present; `--preview` screenshots every slide |
| `python docs/pitch/scripts/new_spec.py <NNN-slug> --title "..."` | Scaffolds `docs/pitch/specs/<NNN-slug>/spec.md` and `plan.md` |
| `python docs/pitch/scripts/audit_phase.py <spec-dir> --phase N` | Lists the phase's tasks, open markers and criteria without evidence |
| `python -m pytest docs/pitch/tools -q` | Tests for the tools |

## content.json
```json
{"title": "Deck name", "no_numbers": true, "chrome": "Team · Partner · synthetic data",
 "sections": [{"description": "one sentence", "start": "slide-id"}],
 "slides": [
  {"id": "a", "layout": "statement", "surface": "accent", "label": "Demo", "title": "Here it is, *running*.", "sub": "...", "notes": "..."},
  {"id": "b", "layout": "quotes", "title": "...", "quotes": [{"label": "...", "text": "..."}], "attribution": "..."},
  {"id": "c", "layout": "system", "surface": "dark", "title": "...", "in_label": "...", "inputs": ["..."],
   "core": {"label": "...", "head": "...", "lines": ["..."]}, "out_label": "...", "outputs": ["..."]},
  {"id": "d", "layout": "timeline", "title": "...", "steps": [{"head": "...", "text": "...", "flag": true}]},
  {"id": "e", "layout": "duo", "title": "...", "left": {"label": "...", "marked": true, "items": ["..."]}, "right": {"label": "...", "color": "muted", "items": ["..."]}},
  {"id": "f", "layout": "points", "title": "...", "points": ["..."]},
  {"id": "g", "layout": "closing", "label": "The ask", "title": "...", "then_label": "Then we", "then": ["..."]}
 ]}
```
`surface`: `light` (default), `dark`, `accent`. `*phrase*` in a title = italic accent (one per title). System fonts only.
