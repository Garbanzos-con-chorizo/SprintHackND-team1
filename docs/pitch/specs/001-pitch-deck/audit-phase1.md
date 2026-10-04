# Audit, phase 1 (content as claims) — 2026-10-04

- PASS — AC-001 — slide `problem`: the three quotes are verbatim from `docs/partner/project-context.md` §1.2, attributed to Debie Coble
- PASS — AC-002 — lint: 0 errors (font floor 24 px, one hero number per slide); every content title is a sentence (0 title warnings)
- PASS — AC-003 — slides `realsim` and `ask` exist; footer "All data synthetic" on all 8
- PASS — AC-004 — lint rule "same layout as the previous slide" = ERROR; tested in `test_tools.py`; order: quotes, columns, statement, hero, ledger, table, columns, statement
- PASS — SC-001 — `build_deck.py docs/pitch/deck/content.json`: "built 8 slides | 0 errors, 0 warnings"
- Numbers' sources: $70,753.96 README; 35 payouts, −$743.10, −$1,875.64, $412.37 `docs/pitch/demo-script-close.md` (run at 752e63f); 11 of 15 KPIs `presentation_guide.md` §6. Re-check at 13:00 (phase 3, SC-003).
- Not yet checked: visual overflow/overlap (SC-002, phase 2).
