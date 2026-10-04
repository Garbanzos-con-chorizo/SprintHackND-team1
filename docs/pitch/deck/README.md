# Pitch deck v2 (branch `o/pitch-deck`)

Shared by Orlando and Dani. Small commits; pull before you push; never force-push.

## Get it
```
git fetch origin && git checkout o/pitch-deck && git pull
```

## Change a slide
1. Edit `content.json`. Layouts and fields: `docs/pitch/tools/README.md`. The rules (short copy, no synthetic numbers, no AI tells): `.claude/skills/slides/SKILL.md`.
2. Build it, with screenshots:
   ```
   python docs/pitch/scripts/build_deck.py docs/pitch/deck/content.json --out out/deck --html docs/pitch/deck/deck.html --preview
   ```
   It must end with `0 errors`. Look at `out/deck/preview/*.png`.
3. Open `deck.html` (offline: arrow keys, F for full screen), commit `content.json` and `deck.html`, push.

## Not decided yet
- Which deck we record: this one, or `docs/pitch/deck-proposal/` on `main`.
- Framed product screenshots (numbers blurred) or drawn diagrams only.
