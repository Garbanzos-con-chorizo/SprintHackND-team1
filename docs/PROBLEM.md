# Problem

Partner: **Goodwill Michiana**. Track: **Reporting**. Contact: Amanda Baumer (office hours 3:00-5:00 PM, room 109B). Full analysis in `docs/roadmap.md`.

## Statement
**Brief:** Reporting. Automate the recurring operations reports that staff put together by hand today.

**Full statement (Debie, Oct 3):** From manual reporting to management visibility. A monthly e-commerce dashboard should balance growth, profitability, productivity, inventory management and customer engagement. A nightly report creates a daily pulse: revenue and customer count by marketplace (ShopGoodwill, Amazon, eBay, other), then enterprise totals. From manual month-end close to Business Central integration: today the close combines portal downloads (Cash Monkey, Upright, ShopGoodwill, Books, eBay, Amazon), emailed reports, bank activity, spreadsheet rules and manual Business Central entries; the target automates the rules, not just the downloads.

Open the demo with this in the partner's own words: "From manual reporting to management visibility."

## Constraints & rules
- Time limit / deadline: **submit by 4:00 PM Sunday**; nothing pushed after counts; last submission wins.
- Required tech / sponsors / datasets: none stated. We have no real data yet; ask Amanda for real or anonymized exports, otherwise use synthetic data and disclose it.
- Submission format (innovationsprintlab.com/go/submit): Google Slides link with recorded demo video embedded (anyone with the link), GitHub repo link, built-versus-used text, sources cited (open source, tooling, models, APIs, templates).
- Demo: slides plus recorded video, then Q&A, hard cut at time limit.
- Zero-point flags: eligibility (build looks pre-weekend; all code must be written this weekend), overclaim (checked against built-vs-used and repo; moves Working Evidence to level 1), and "would you spend 30 minutes with this team next week?"
- Known partner limits: none confirmed yet. Questions for Amanda are in `docs/roadmap.md` (BC version and import method, sample exports, top spreadsheet rules, staff skills, IT policy).

## Judging criteria
Six criteria, 100 points, each scored level 0-4 (level 2 = solid team):
- **Working Evidence (26):** full workflow runs in one take on own example (L3); on more than one example including a messy/edge-case input (L4).
- **Partner Problem Fit (22):** fully solves it (L3); in the most efficient way, fewest user steps (L4).
- **Fits Their Constraints (19):** engaged the partner; build works within a real limit (L3), all key limits so they could start tomorrow (L4).
- **Technical Substance (15):** hard part is real, minor edges simulated and disclosed (L3); their own work and they can explain limits and next steps (L4).
- **Demo Clarity (11):** clear in the first 30 seconds, on time, pitch repeatable (L4).
- **X-Factor (7):** stands out; partner would want to pilot it.

## Our interpretation (one paragraph)
Goodwill Michiana staff hand-build nightly, monthly and month-end reports from exports of six or more systems. We are building a file-drop pipeline that ingests those exports, normalizes them to one transaction schema, applies the staff's spreadsheet rules as explicit, editable config (not code), and produces three outputs: a nightly pulse (revenue and customer count by marketplace plus enterprise totals), a monthly dashboard across the five pillars, and a month-end reconciliation with an exceptions queue and a Business Central-ready journal import file. The differentiator is automating the rules, not just the downloads. Ingestion is manual file drop (no portal scraping) and there is no live Business Central integration; we will disclose both.

## MVP scope (must work for demo)
- Parsers for the sources we have sample data for, all emitting one canonical transaction schema (`docs/contracts/`).
- Config-driven rules engine (YAML/JSON) that maps transactions to GL accounts and splits fees.
- Nightly pulse: revenue and customer count by marketplace (ShopGoodwill, Amazon, eBay, other) and enterprise totals.
- Month-end close: reconcile marketplace payouts to bank activity, flag unmatched items in an exceptions queue, export a balanced Business Central journal import file.
- Demo data: one clean month and one messy month (duplicates, a refund, a missing file, an unmatched bank deposit).

## Stretch goals
- Thin monthly dashboard across growth, profitability, productivity, inventory and customer engagement (needs COGS, labor and inventory data; confirm availability with Amanda).
- LLM-suggested GL accounts for unknown descriptions, with human approval, kept off the critical path.
- Live edit of a rule in the demo with the output changing immediately.
- Email or PDF delivery of the nightly pulse.

## Demo
<!-- Target 2-3 minutes. Fill in the click-path once the schema and sample data are locked. -->
1. **Open (0:00-0:30):** the partner's words, "From manual reporting to management visibility", and the pain: six portals, emailed reports, bank activity, spreadsheet rules, manual BC entry.
2. **Clean month, one take:** drop the exports in the inbox, see the nightly pulse by marketplace and enterprise totals, then the reconciled close and the generated BC journal file.
3. **Messy month, one take:** duplicates, a refund, a missing file and an unmatched deposit land in the exceptions queue; staff resolve one and the journal rebalances.
4. **Rule edit:** change one rule in config and show the output change.
5. **Close (last 15s):** what is real, what is simulated (synthetic data, manual file drop, import file not live BC), and what we would build next.
