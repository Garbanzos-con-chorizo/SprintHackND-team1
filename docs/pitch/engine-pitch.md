# How to present the nightly pulse and the engine to the judges

Written 2026-10-03 for the Sunday 4:30 PM demo (Pod B, Room 154), a **recorded video embedded in Google Slides, then questions, hard cut at the time limit**. Submission closes **4:00 PM Sunday**. This covers phase 1 and the engine (Victor's part). Orlando's script for the three nights is `docs/pitch/demo-script-pulse.md`; this file explains **what to claim, what to prove, and what to say out loud** so the demo scores. Phase 2 and 3 lines are marked *fill in only when it runs on screen*.

## The idea in 30 seconds (the judges decide how clear you are in the first 30)
Open on **Goodwill's own words** (the rubric asks for it): *"From manual reporting to management visibility."* Then:

> "Every night someone at Goodwill opens two tools, Upright and Cash Monkey, clicks through ten steps, counts rows in Excel and types the numbers into the Daily Summary Spreadsheet. We turned that into one run. Two emailed reports go in; one trustworthy page comes out: revenue and customers for ShopGoodwill, Amazon and eBay, and the e-commerce total. It's honest about a missing report, and it counts a duplicated download once. The data is synthetic, and we'll show you exactly what's real."

If the judges can repeat that, Demo Clarity is a 4. Do not start with architecture, the stack or the database.

## Score it against the rubric (the six criteria, each 0-4, level 2 = a solid team)
| Criterion (points) | What lifts you to 3 or 4 | What we can show | Be careful |
|---|---|---|---|
| **Working Evidence (26)** | 3: full workflow in one take on your own example. **4: one take on more than one example, including a messy or edge-case input.** | Three nights, one take each, **on the real pipeline** (`run_nightly`): a clean night, a night where the Cash Monkey report never came, a night with the Upright report saved twice. Our generator adds refunds, a bad amount, a bad date and midnight crossings. | Never cut, screenshot or narrate a step. Use `--simulated` only as a stage fallback, never in the recording. |
| **Partner Problem Fit (22)** | 3: fully solves the problem. 4: the fewest steps for the user. | The nightly report is fully solved for the e-commerce rows: **zero steps for staff** once the report arrives; today it is ten. | The brief has **three** parts (nightly, monthly dashboard, month-end to Business Central). Say plainly which run on screen. Level 3 for "fully solves" needs honesty about scope. *Fill in the dashboard and Business Central lines only if they run.* |
| **Fits Their Constraints (19)** | 3: works within one real limit. 4: all key limits, so Goodwill could start tomorrow. | Goodwill's stated limit is **"tools they already pay for"**. We add **no new software for staff**: the inputs are the emailed reports Upright and Cash Monkey already send, the outputs are a page, an Excel-ready CSV and an email. We engaged Amanda and **built her answers in**: assume an API, reports arrive as emailed Excel, e-commerce closes at 9 PM Pacific = midnight Eastern, brick and mortar is separate. We also match their real quirks: Upright in Pacific time, Cash Monkey in UTC, one line per unit, customers counted as rows. | Level 4 is not honest yet: no real file, no IT-policy answer. Say what you *would* need (below). |
| **Technical Substance (15)** | 3: the hard part is real, minor edges simulated and disclosed. 4: it's your own work and you can explain its limits and next steps. | The hard part is **not the page, it's trusting the numbers**: putting every order on the right Eastern day across three time zones, counting a duplicated download once, not mistaking one-line-per-unit for duplicates, and refusing to show $0 for a missing report. Show the **independent answer key** (below). | The data, the APIs, the email and the scheduler are simulated: say so on a slide. "AI coding tools are fine. Explain your own system." |
| **Demo Clarity (11)** | 4: clear in the first 30 seconds, on time, and the pitch is repeatable. | The 30-second opening above. One sentence per night. | Comprehension, not polish. Finish early. |
| **X-Factor (7)** | 4: they'd back you and the partner would pilot it. | The line no spreadsheet has: **a report that tells you when it's missing data instead of lying.** And the ask below. | Don't pitch a business (market size and pricing score zero). |

### The ask that answers the "30 minutes next week?" question
End with: *"Send us one real Upright file and one real Cash Monkey file. We'll show Amanda her own pulse, from her own data, in 30 minutes."* It's concrete, it's honest about what's missing, and the partner judge can say yes.

## Three moments that earn Working Evidence and Technical Substance
1. **The clean night** (30 s): the log shows the inbox, the engine, the pulse, the page, in under two seconds. Point at the definitions printed under the numbers.
2. **The missing report** (30 s): *"A spreadsheet would show eBay and Amazon at zero. Ours says 'No data: file not received', and the comparison uses only what we have on both days."* This is the moment judges remember.
3. **The duplicate** (25 s): the '(4)' in the Upright file name is the same one visible in Goodwill's own walkthrough. *"Added up by hand, ShopGoodwill doubles. It found 149 duplicate rows and said so."*

**One extra 20-second moment for Technical Substance, if time allows:** *"How do we know the numbers are right? We never ask our own code. We generate the orders, compute the expected totals from those orders, then run the real engine and compare. And we break the timezone handling on purpose to prove the check can fail."* Run `python -m engine.tools.make_sample --scenario messy_day --check --pulse` and end on `PULSE MATCHES THE ANSWER KEY`.

## What is real and what is simulated (paste into "built versus used", and show on one slide)
| | Real, built by us this weekend | Simulated or assumed, and said so |
|---|---|---|
| Ingestion | The inbox reader for CSV and Excel; source detection; the parsers; cleaning of money, dates and timezones; cross-file dedupe; the per-marketplace source status; warnings | **The data is synthetic.** Upright's columns come from a screenshot; Cash Monkey's are guesses |
| Providers | The adapter and provider structure; one class per provider | **The APIs.** Amanda told us to assume one; the clients are stubs and the simulators write synthetic emails. The fetch log marks each as simulated |
| Delivery | Output files, the page, a CSV, an email-ready copy | **No mailbox, no scheduler.** A folder stands in for email; `run_nightly` stands in for Windows Task Scheduler or cron |
| Checking | 140 engine tests (at the time of writing); an answer-key generator; the same checks against Orlando's independent samples | |
| Pulse and pages | Dani's calculation and Orlando's renderer | |
| Phase 2 and 3 | *Fill in what runs; label the mock internal API ("simulated internal data") and the Business Central files ("import file, not a live posting")* | |

**Sources to cite** (open source, tooling, models): Python and its standard library; `openpyxl` (read Excel); `tzdata` (timezones on Windows); `pytest` (tests); Claude Code and Claude models (AI coding assistance, as the rubric allows); plus whatever Orlando and Dani used for the page and the server. List only what is actually in the repo.

## Say these limits out loud (the overclaim flag is checked against the repo and this text)
- "No real Goodwill file has been read. The first thing we'd do with a real file is replace two column names."
- "The APIs are assumed, on Amanda's word. We have not seen them."
- "Brick and mortar is independent and out of scope; our total is the e-commerce total, as slide 31 says."
- "Two things could change the numbers: how staff count customers for Cash Monkey, and whether Cash Monkey covers only Goodwill Books. We've written both down as questions."
- "The run is on demand today; production would schedule it just after midnight Eastern."

## Questions the judges are likely to ask
| Question | Honest answer |
|---|---|
| How do you know it works on real files? | We don't yet. It works on files built to the layouts in Goodwill's own walkthrough, checked against answer keys we computed independently. One real file of each would settle it in minutes. |
| Why not scrape the portals? | Amanda told us to assume an API and emailed reports, so we built for that. Scraping is fragile, and we don't know Goodwill's IT policy. The tools already email reports; we read those. |
| What if a report is late or never comes? | The run sees it before anyone opens the page, shows "No data" for that marketplace, leaves it out of the total, and says the total is partial. |
| Why Python? Where does it run? | Fast to build. It needs one machine with Python and a folder. We have not yet learned what machine or policy Goodwill has (an open question for Amanda), and the contract between the parts is files, so any part can be replaced. |
| What does a new report type cost? | One file with the column names, the timezone and the filename pattern. A new marketplace row on the page is a contract change, not just a file. |
| How are customers counted? | Like staff do today: Upright's row count, so one per order. Slide 26 says so. We keep the buyer id too. |
| What would you build next? | Read a real file and a real API; schedule it; then the month-end close to Business Central (rules, bank matching, a balanced journal file). |
| Who built what? | Say your own part plainly and one line on each teammate's. Explain the system, not just the tool you used. |

## Suggested slides (the video goes on slide 4)
1. **The problem, in Goodwill's words**, and the ten manual steps it replaces (one line).
2. **What we learned from Goodwill:** two tools, two time zones, one line per unit, customers counted as rows; Amanda's answers (API, emailed Excel, 9 PM Pacific cutoff).
3. **What we built:** inbox, engine, pulse, page; the three messy cases it handles.
4. **The demo video** (three nights, one take each).
5. **How we know the numbers are right:** the independent answer key and the check that can fail.
6. **Real versus simulated:** the table above. This slide protects your Technical Substance score.
7. **Limits and next steps:** what a real file or API would change; the month-end close.
8. **The ask:** one real file each, 30 minutes with Amanda.

## Before 4:00 PM Sunday
- [ ] **Clean-clone test.** In a fresh folder on Python 3.12 or 3.13: `pip install -r engine/requirements.txt`, then the commands in the README and `run_nightly --scenario gw_day_clean`. A judge may do exactly this.
- [ ] **Every sentence on a slide has a command that proves it.** If you cannot run it, cut the sentence.
- [ ] **Eligibility:** the repo history starts 2026-10-03 (checked). Confirm with the team that nobody pasted in code from before the weekend, and don't force-push history.
- [ ] **Docs agree:** `PROBLEM.md`, `roadmap.md`, `ASSUMPTIONS.md` and `CLAUDE.md` all say the same thing about what is real. `CLAUDE.md` still has `<TBD>` for the stack and run commands; fill it in.
- [ ] **Slides shared "anyone with the link"; the video embeds and plays;** GitHub link works logged out.
- [ ] **Record early, re-record if time allows.** Keep a fallback browser tab for each night.
- [ ] **Submit, then resubmit** if anything changes before 4:00 PM; the last one counts. Nothing pushed after 4:00 PM counts.
