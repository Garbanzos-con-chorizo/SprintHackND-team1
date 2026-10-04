# Pitch tools and scripts

`tools/` = importable modules. `scripts/` = commands you run. Rules they enforce: `.claude/skills/slides`. Stdlib only.

| Command | Does |
|---|---|
| `python docs/pitch/scripts/build_deck.py <content.json> --out <dir>` | Renders the Slides-artifact files (`<dir>/project/...`) and lints them. Exit 1 on lint ERROR |
| `python docs/pitch/scripts/new_spec.py <NNN-slug> --title "..."` | Scaffolds `docs/pitch/specs/<NNN-slug>/spec.md` and `plan.md` |
| `python docs/pitch/scripts/audit_phase.py <spec-dir> --phase N` | Lists the phase's tasks, open markers and criteria without evidence |
| `python -m pytest docs/pitch/tools -q` | Tests for the tools |

## content.json
```json
{"title": "Deck name", "theme": "swiss|keynote|ledger", "footer": "All data synthetic · ...",
 "sections": [{"description": "one sentence", "start": "slide-id"}],
 "slides": [
  {"id": "a", "layout": "statement", "eyebrow": "...", "title": "...", "sub": "...", "invert": false, "notes": "..."},
  {"id": "b", "layout": "quotes", "title": "...", "quotes": [{"label": "...", "text": "..."}], "attribution": "..."},
  {"id": "c", "layout": "hero", "title": "claim", "number": "$70,753.96", "caption": "...", "tone": "warn?"},
  {"id": "d", "layout": "ledger", "title": "claim", "rows": [{"status": "...", "label": "...", "amount": "...", "warn": true}]},
  {"id": "e", "layout": "columns", "title": "claim", "cols": [{"label": "...", "head": "...", "text": "..."}]},
  {"id": "f", "layout": "table", "title": "claim", "head": ["A", "B"], "widths": [40, 60], "rows": [["...", "..."]]}
 ]}
```
Any slide takes `"alt": true` (second background tone). Text fields may hold inline `<b>`.
