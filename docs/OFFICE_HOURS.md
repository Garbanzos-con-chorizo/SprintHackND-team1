# Office hours questions: Amanda Baumer

Room 109B, 3:00-5:00 PM. Record answers in `docs/decisions/001-partner-answers.md` (Orlando, task 0.4). Questions marked **MUST** block the build; get those first. Ask for **real or anonymized sample files** wherever possible, since that matters more than any answer.

## Ask first (blocks the build)
1. **MUST** Can we have real or anonymized sample exports from each source (ShopGoodwill, Amazon, eBay, Cash Monkey, Upright, Books, bank activity), ideally one messy month?
2. **MUST** Business Central: cloud or on-prem? How do entries go in today (journal, Excel paste, configuration package)? Can we get the chart of accounts and one finished month-end journal?
3. **MUST** What are the top 5 spreadsheet rules staff apply in the close, in order?
4. **MUST** Who will run this, with what skills, on what machine? Any IT policy on installing software or sending data to cloud services?

## Nightly pulse
5. Is "revenue" gross, net of refunds, or net of marketplace fees? (Default: net of refunds, fees separate.)
6. Is "customer count" unique buyers or orders? Which sources actually expose buyer identity? (Default: unique buyers, falling back to orders and labelled.)
7. What defines "a day": order date, payout date, or the export cutoff? What timezone?
8. When do staff download the data, and by what time must the report be ready?
9. What counts as "Other"? Cash Monkey, Upright, Books, in-store, anything else?
10. Who reads it and how: email, PDF, or a page? One recipient or many?
11. Is a comparison useful (vs yesterday, vs same day last week)? What should happen when a source's data is missing?
12. Do they want the enterprise total to include non-e-commerce revenue, or e-commerce only?

## Monthly dashboard
13. Which metrics define each of growth, profitability, productivity, inventory management and customer engagement today?
14. Where would profitability data come from (cost of goods, fees, labor)? Does any of it exist digitally?
15. How is productivity measured (items listed per hour, items sold per labor hour)? Is labor data available?
16. Is there an inventory count or aging data we can get, and in what format?
17. Who is the audience (leadership, board) and what decision should the dashboard support?
18. Which month should we compare against, and is there a target or budget to measure against?

## Month-end close
19. Which of the six portal downloads is the slowest or most error-prone today?
20. Which close rules are the most error-prone or most often corrected afterwards?
21. How do marketplace payouts reach the bank (batching, delay, one deposit for many payouts)?
22. What does staff do today when a deposit doesn't match anything, and how often does it happen?
23. How long does a month-end close take now, and what would "good" look like?
24. Does a human need to approve entries before they go into Business Central? Is a reviewable file acceptable, or must it post directly?
25. Which entries are routine and which need judgment?

## Constraints and pilot
26. Budget, time and staff constraints we should design around?
27. Is any of the data sensitive (donor or customer data) so that we should avoid sending it to an external service, including LLM APIs?
28. What would make you want to pilot this next week? Who would we talk to?
29. Can we show you the demo or a screenshot before Sunday's submission?
