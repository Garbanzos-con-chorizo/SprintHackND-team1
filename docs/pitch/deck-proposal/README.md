# The pitch deck (shared by Victor, Orlando and Dani)

**Everyone edits this folder, on branch `victor/pitch-deck`.** Orlando owns `docs/pitch/` and has the last word on the deck. Small commits, `git pull --rebase` before you push, never force-push, and say what you changed in your status file.

**The deck to use is the Slides artifact:** https://claude.ai/artifact/F1y3oyZP9vKm88Vn6Tqcti (Victor shares it from its Share menu). `slides-artifact/` is a copy of its files as published at 15:05 EDT: nine slides, a title slide (1), Goodwill's words (2), Orlando's diagram (3) and missing-report steps (6) ported in, an integration slide (7) that follows decision 012 (the Controller downloads the month-end reports by hand; Business Central is cloud and takes CSV), and a thank-you slide in Goodwill's words (9) instead of the ask. A PowerPoint and a PDF of it (one picture per slide, speaker notes in the PowerPoint) can be rebuilt from the deck's own Share › Export menu, which also gives an editable PowerPoint: `deck.json` (title, slide order, sections) and one `slides/<id>.html` per slide, with the speaker notes in each slide's `<aside>`.

To change a slide, either way works:
- edit it in the artifact's own editor (once it is shared with you), then copy the changed slide into `slides-artifact/` and commit it;
- or edit the file here, ask your agent to publish it to the artifact, and commit it.
Either way the repo and the deck must agree before the 15:00 submission.

To work on it:
```
git fetch origin
git worktree add ../deck victor/pitch-deck
```
(or `git checkout victor/pitch-deck`).

Other files:
- `narration.md`: the three-minute take, with what to run, say and point at, and the numbers to expect. Check it at the dry run: `main` has moved since it was written (#79 changed the close page's downloads).
- `content.json` and `deck.html`: the first version, built with Orlando's generator from `o/skills-sdd`. The slide wording is close but older; use the artifact.

Everything on the slides is about synthetic data; the footer says so on every slide.
