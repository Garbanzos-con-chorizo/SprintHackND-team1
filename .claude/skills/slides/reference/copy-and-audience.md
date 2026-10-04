# Slide copy and audience psychology (research notes, 2026-10-04)

Each rule names the evidence behind it. Apply in this order: story → titles → body → notes.

## How the audience's mind works
| Finding | Evidence | Rule it gives |
|---|---|---|
| Working memory is small; extra load crowds out understanding | Sweller, Cognitive Load Theory | Cut everything that doesn't prove the title |
| Extraneous material hurts learning (23/23 tests, d = 0.86) | Mayer, **coherence** principle | No decorative words, eyebrows that repeat the title, or "nice to know" lines |
| Narration + identical on-screen text is worse than narration + visual (16/16, d = 0.86) | Mayer, **redundancy** principle | Never put the script on the slide; the slide shows the claim and the evidence, the voice explains |
| Cues that show structure help (24/28, d = 0.41) | Mayer, **signaling** principle | Bold the one key phrase; section labels; consistent position for titles |
| Pictures recalled ~2× words | Paivio, dual coding / picture superiority | Prefer a number, table or screenshot over a sentence |
| Easy-to-read = judged truer and more likable | Processing fluency (Alter & Oppenheimer; Stanford GSB) | Short common words, high contrast, no hyphen breaks, typographic quotes |
| First and last items are remembered best | Serial position (primacy/recency) | Most important claim on slide 1–2 and the ask last; key number first in a sentence |
| Experts can't un-know their jargon | Heath & Heath, "curse of knowledge" | Rewrite every term a partner wouldn't use: "recon", "payload", "store" → "matching", "result", "database" |
| Simple, Unexpected, Concrete, Credible, Emotional, Stories | Heath & Heath, *Made to Stick* (SUCCESs) | One concrete example beats a category; a real day/amount beats "edge cases" |
| Sentence headline + visual evidence → better comprehension and recall | Alley et al., assertion-evidence | Title = the claim, ≤ 2 lines, a full sentence with a verb |
| Projected words per minute matter more than word count | Garner & Alley (ASEE) | Budget words by time on screen: ≤ 40 words for a 30–45 s slide |

## Copy rules (checked by `lint_deck.py` where marked ✓)
1. **Write the spine first** (mblode/presentation-creator): ending first, then stakes, then one beat per slide. Read titles alone top to bottom: they must tell the story.
2. **Titles are claims** ✓: full sentence, verb, ≤ 2 lines, no widow (single word on the last line) ✓.
3. **Lead with the reader's gain, then the feature**: "Goodwill's nightly report builds itself" not "Automated pulse pipeline".
4. **Concrete over abstract**: a day, an amount, a name. "Sep 21–22, $743.10" not "data gaps".
5. **Partner words** (curse of knowledge): use Goodwill's terms (marketplace, close, Business Central); never internal names (recon, payload, lane).
6. **One number per slide** ✓; say it in the title or right under it; tabular figures.
7. **Typography**: curly quotes and apostrophes (’ “ ”) ✓, en dash for ranges (21–22), true minus (−), no manual hyphen breaks.
8. **No redundancy**: eyebrow adds context the title doesn't; notes say what the slide doesn't.
9. **Honest qualifiers stay**: "synthetic", "simulated", "import files". Never trade accuracy for punch.
10. **Notes are prompts, not a script** (mblode): 3–5 short beats, the number to say, what to point at.

## Visual QA (render with `build_deck.py --preview`; check every PNG)
Balance (no empty half-slide), widows, wraps inside labels, alignment to the grid, one focal point, contrast, footer clear of content, nothing over y = 920.

## Sources
- Mayer's principles, effect sizes: https://resolve-he.cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/principles-for-reducing-extraneous-processing-in-multimedia-learning-coherence-signaling-redundancy-spatial-contiguity-and-temporal-contiguity-principles/CD5B7AE1279A9AB81F8EEBB53DBEC86E · https://services.dartmouth.edu/TDClient/1806/Portal/KB/PrintArticle?ID=171655
- Cognitive load for presenters: https://policyviz.com/2017/01/05/applying-cognitive-load-theory-to-presentation-delivery/
- Projected words per minute (Garner & Alley): https://peer.asee.org/projected-words-per-minute-a-window-into-the-potential-effectiveness-of-presentation-slides.pdf
- Processing fluency and persuasion: https://www.gsb.stanford.edu/faculty-research/publications/ease-persuasion-multiple-processes-meanings-effects
- Picture superiority / dual coding: https://en.wikipedia.org/wiki/Picture_superiority_effect
- Serial position: https://www.behavioraleconomics.com/resources/mini-encyclopedia-of-be/serial-position-effect/
- Made to Stick, curse of knowledge: https://personalmba.com/review/made-to-stick/
- Assertion-evidence: https://pure.psu.edu/en/publications/how-the-design-of-presentation-slides-affects-audience-comprehens/
- presentation-creator skill (spine, QA table, notes as prompts): https://github.com/mblode/agent-skills
