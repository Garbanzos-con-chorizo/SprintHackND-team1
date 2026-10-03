# Roadmap: Goodwill Michiana, Reporting

## Brief
**Reporting.** Automate the recurring operations reports that staff put together by hand today.

Full statement (Debie, Oct 3): From manual reporting to management visibility. A monthly e-commerce dashboard should balance growth, profitability, productivity, inventory management and customer engagement. A nightly report creates a daily pulse: revenue and customer count by marketplace (ShopGoodwill, Amazon, eBay, other), then enterprise totals. From manual month-end close to Business Central integration: today the close combines portal downloads (Cash Monkey, Upright, ShopGoodwill, Books, eBay, Amazon), emailed reports, bank activity, spreadsheet rules and manual Business Central entries; the target automates the rules, not just the downloads.

Partner contact: Amanda Baumer, office hours 3:00 to 5:00 PM, room 109B.

## What they're asking for
Three separate pain points, different sizes.

| # | Deliverable | Real difficulty | Demo value |
|---|---|---|---|
| 1 | **Nightly pulse**: revenue and customer count by marketplace (ShopGoodwill, Amazon, eBay, other), then enterprise totals | Low. Ingest, normalize, aggregate. | High, quick to show running |
| 2 | **Monthly dashboard**: growth, profitability, productivity, inventory, customer engagement | Medium. Five pillars means five metric definitions, and some need data nobody mentioned (COGS, labor hours, inventory counts). | High visually |
| 3 | **Month-end close to Business Central**: portal downloads, emailed reports, bank activity, spreadsheet rules, manual BC entries | **High, and it's the real problem.** | Highest if it works |

The key sentence is "**the target automates the rules, not just the downloads.**" The value is in the spreadsheet rules living in staff heads: how a Cash Monkey payout maps to GL accounts, how eBay fees are split out, how a bank deposit is matched to a settlement. Those rules need to be written down as explicit, editable logic.

## Judging rubric (100 pts, each criterion scored level 0-4, level 2 = solid team)
1. **Working Evidence (26):** what the recorded demo shows running end to end. L3 = full workflow in one take on own example; L4 = one take on more than one example, including a messy or edge-case input.
2. **Partner Problem Fit (22):** solves the partner's problem with a clear, rational approach. L4 = fully solved with the fewest steps for the user.
3. **Fits Their Constraints (19):** engaged the partner and understood the problem beyond the surface. L3 = build works within one real limit; L4 = all key limits, partner could start tomorrow.
4. **Technical Substance (15):** how much of the hard part is real and built by the team. L3 = hard part real, minor edges simulated and disclosed.
5. **Demo Clarity (11):** clear in the first 30 seconds, on time, pitch repeatable.
6. **X-Factor (7):** stands out; would you back them; would the partner pilot it.

Zero-point items: eligibility flag (build looks made before this weekend), overclaim flag (checked against the built-vs-used text and repo; upheld moves Working Evidence to L1 on every ballot), and the "30 minutes next week?" question.

Demo: Google Slides with recorded demo video embedded, then questions. Hard cut at time. Open with the partner's problem in the partner's own words.

**Submit by 4:00 PM Sunday** at innovationsprintlab.com/go/submit: Slides link (anyone with the link), GitHub repo link, built versus used, sources cited. Nothing pushed after 4:00 PM counts.

### How this plays on the rubric
- **Working Evidence:** plan the demo around a clean month plus a messy month (duplicate rows, a refund, a missing file, a bank deposit that matches nothing).
- **Partner Fit:** ideal is "drop the files in a folder, get the nightly report and a ready-to-import BC journal." Avoid a tool with ten screens.
- **Constraints:** engaging Amanda is explicitly scored, and the build must reflect a real limit she gives. Cheapest points available.
- **Technical Substance:** the rules engine and reconciliation must be real. Disclose anything simulated. Overclaiming is costly.
- **Demo Clarity:** open with Debie's words, "From manual reporting to management visibility."

## Recommended architecture (simplest thing that demos well)
```
inbox/ (CSV/XLSX exports per source)  ->  parsers (one per source, same output schema)
   ->  canonical transactions table  ->  rules engine (YAML/JSON rules, human-readable)
   ->  outputs:  nightly pulse (HTML/email)  -  monthly dashboard  -  recon report with exceptions
                 -  Business Central journal import file (balanced debits/credits)
```
- **Automate the portal downloads, with file drop as the fallback.** Staff download these reports by clicking through logged-in portals (deck slides 21-30). Per Amanda (office hours, Oct 3) we assume Upright has an API that emails the report as an Excel attachment, which lands in `inbox/`; the parsers read it exactly as they read a hand-dropped file (`docs/decisions/005-api-email-delivery-and-run-schedule.md`). We have not seen the API, so the Upright client is a stub, and anything without an API stays a file drop. The demo discloses which is which.
- **Rules as config, not code.** Show a rule such as "eBay payout -> debit Bank, credit Sales, debit Fees" being edited and the result changing. This is the proof that the rules are automated.
- **Exceptions queue.** Anything that doesn't match a rule or reconcile to bank goes to a "needs a human" list. This is also the messy-input demo moment.
- **Business Central output:** generate a journal-lines file in the format BC imports; no live integration this weekend. Confirm the format with Amanda.
- **LLM use (optional):** suggest GL accounts for unknown descriptions, with human approval. Keep it out of the critical path so the demo is deterministic.

## Questions for Amanda (office hours, 3-5 PM, room 109B)
1. Can we get **real or anonymized sample exports** from each source, especially a messy month? What do Cash Monkey, Upright and Books actually export?
2. **Business Central:** which version (cloud or on-prem)? How do entries go in today (journal, Excel paste, config package)? Can we get the chart of accounts and one finished month-end journal?
3. What are the **top 5 spreadsheet rules** staff apply, in order?
4. How is "customer count" defined: unique buyers or orders? What counts as "other"?
5. Where would profitability and productivity data come from (COGS, labor hours, inventory counts)? Does any of it exist digitally?
6. **Who runs this, with what skills, on what machine?** Any IT policy on installing software or sending data to cloud services?
7. What's the nightly report's audience and delivery: email, PDF, or a page?
8. How long does close take now, and what would "good" be?

## Risks
- **Scope creep:** three deliverables plus a dashboard is too much for one weekend. Keep the dashboard thin and make the close the star.
- **No real data:** synthetic data is acceptable but must be disclosed. Real samples from Amanda lift Fit and Constraints.
- **Overclaiming "Business Central integration":** say "BC-ready import file" unless actually connected to a sandbox.
- **Eligibility flag:** all code must be written this weekend; no reuse of old repos.

## Suggested lanes (3 people)
- **A, ingestion and rules:** parsers, canonical schema, rules engine, exceptions queue.
- **B, outputs and UI:** nightly pulse, dashboard, exceptions and journal views.
- **C, data and story:** synthetic datasets (clean and messy), BC journal format, demo script, slides, built-vs-used text, Amanda liaison.

Contracts to write first in `docs/contracts/`: the canonical transaction schema and the rule format.

## Next steps
1. Fill in `docs/PROBLEM.md` from this document.
2. Send one person to office hours with the question list.
3. Lock the canonical schema within the first hour so lanes can work in parallel against mocks.
4. Record the demo early, re-record if time allows. Submission deadline is 4:00 PM Sunday.
