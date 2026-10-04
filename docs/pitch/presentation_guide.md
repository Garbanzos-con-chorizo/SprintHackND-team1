# Presentation guide: suggestions for Orlando

Written 2026-10-04 00:50 EDT by Dani's agent, at Dani's request. **These are suggestions; the presentation is yours.** It covers the whole talk (all three phases) and the question of building it in HTML. It does not repeat `docs/pitch/engine_pitch.md` (Victor: the rubric line by line for phase 1, the real-versus-simulated table, likely questions) or the demo scripts; it points to them.

Take every number from the 13:00 dry run, not from this file: `main` is still moving.

## 1. Read this first: what we hand in is fixed

The organizers' deck (slides 52 and 61, read from the page on Sunday 00:40) says:
- The form takes a **Google Slides link, shared "anyone with the link", with the recorded demo video inside it**.
- The **room computer runs the slides**; the facilitator opens them from the pod folder, and the video plays inside them. Remote judges watch the room's screen through a call.
- The slot is the same length for every team, announced at 4:18 PM, after we have submitted, and it is a **hard cut**.
- Open with the partner's problem in the partner's own words. The judges score Partner Problem Fit partly on **the opening slide**.

So an HTML presentation cannot be the thing we submit. It can still be the thing we make:

| Option | How | Verdict |
|---|---|---|
| **A. HTML inside the recording** | Build the talk as one HTML page. Record one continuous take: the HTML slides, then the terminal and the portal, then the last HTML slides. The Google Slides deck is thin: the problem slide, the video, the real-versus-simulated slide, the ask. | **Suggested.** No editing, no second tool, and the slides and the product look like one thing. |
| B. HTML exported to images | Print each HTML slide to an image (headless Edge, the same trick `engine.export pdf` uses) and place the images in Google Slides around the video. | Fine if you want more slides outside the video. More steps. |
| C. Submit a link to the HTML page | | Do not count on it. Ask Hector only if you have a spare minute; the default is Google Slides. |

Whatever you choose, **the first Google slide is Goodwill's problem in Goodwill's words**, as text on the slide itself, not only inside the video. The three sentences are in `docs/goodwill-project-context.md`, section 1.2 (deck slide 19).

## 2. What the judges score, and what to show for it

| Criterion (points) | Top level asks for | What we show |
|---|---|---|
| Working Evidence (26) | the full workflow in **one take, on more than one example, including a messy input** | One continuous recording: three nights of the pulse (clean, missing report, duplicate), the scorecard, and the close on a tidy month and then on the messy month. No cut, no screenshot standing in for a step |
| Partner Problem Fit (22) | fully solved, fewest steps for the user | All three parts of their brief run: nightly, monthly scorecard, month-end close. Steps for staff: none for the nightly and the scorecard; one command, or the 1st of the month, for the close |
| Fits Their Constraints (19) | works within their limits; could start tomorrow | "Tools they already pay for": the output is Excel-ready CSV in Business Central's own column order, a page, a PDF, an email draft for Outlook. Nothing to buy or install beyond Python. Amanda's answers are built in (API assumed, emailed Excel, 9 PM Pacific cutoff) |
| Technical Substance (15) | the hard part is ours; we can explain limits and next steps | Trusting the numbers: time zones, duplicates, "no data" instead of $0, a journal that refuses to be written unbalanced, every payout explained or flagged, answer keys computed apart from the code |
| Demo Clarity (11) | clear in the first 30 seconds, on time, repeatable | One sentence per part. Say the sentence in section 3 before anything moves on screen |
| X-Factor (7) | the partner would pilot it | A report that says what it does not know: a missing file, a deposit nobody can place, a source we only simulate |

## 3. A storyboard

Aim for **three minutes or less**, with the important things early: we do not know the slot length when we record, and the cut is hard. If you need a shorter version, drop the scorecard to fifteen seconds before you touch the close.

| Time | On screen | Say (one idea each) |
|---|---|---|
| 0:00 | Slide: Goodwill's three sentences | "This is Goodwill's problem in their words: three reports built by hand." |
| 0:15 | Slide: one line each for nightly, monthly, month-end, and one line "synthetic data; here is what is simulated" | "We automated all three. The data is synthetic and we will show exactly what is real." |
| 0:30 | Terminal and page: the nightly pulse, a clean night, then the night a report never came | "No file is 'No data', never $0." (`docs/pitch/demo_script_pulse.md`) |
| 1:00 | Page: the COO scorecard | "These are Goodwill's own 15 KPIs from their slide. The ones built on internal data we have not seen are badged as simulated." (Victor's L7 script) |
| 1:25 | Terminal and page: the close on the tidy month | "One command. The journal balances, every cent of what each marketplace owes is explained, and these are the files Business Central takes." |
| 1:50 | The same command on the messy month | "The same month as it really arrives. Two reports were never downloaded: it names the days and the amounts. One deposit matches nothing: it is held out. Nothing is hidden in a net." (`docs/pitch/demo_script_close.md`, when Dani's task D3.11 lands) |
| 2:20 | The General Journal CSV open in Excel; the nine-source table on the close page | "This opens in the tools they already pay for. Of their nine sources, these come from sample files and these from simulated APIs." |
| 2:35 | Slide: real versus simulated | Read it. It protects two scores. |
| 2:50 | Slide: the ask | "Send us one real month of files and last month's allocation workbook, and we will show you your own close." |

The close gets the most time because it is the part Goodwill called the real problem ("automates the rules, not just the downloads" is the title of their slide 40).

**One take.** The level-4 sentence for Working Evidence says "one take". If the video is a single recording from the first slide to the last, there is nothing to argue about. Rehearse until it fits, and keep the first complete take even if you try for a better one.

## 4. If you build it in HTML

- **One file, nothing from the network.** No CDN, no web fonts, no remote images: it must open from disk with no internet. Keep it in `docs/pitch/` so the claims are in the repo the judges check.
- **16:9, and big.** Remote judges see a shared screen of the room's screen. Body text no smaller than about 32 px at 1920 x 1080, 25 words or fewer per slide, dark on white.
- **Look like the product.** The portal's colours are in `reports/pulse.py` (`--primary: #0054A4`, `--ink: #231F20`, white background, 2 px corners). Same look, so the slides and the pages read as one thing.
- **Keys, not timing.** Arrow keys or space to advance, a small slide counter, no animation that has to be waited for. You are recording a take; a transition that lags costs a retake.
- **Do not embed the generated pages.** They live in `reports/` and exist only after a run. Switch to the real browser tab during the take: that is the evidence. Screenshots inside slides count as "a screenshot" against Working Evidence.
- **Label what is synthetic** on any slide that shows a number.
- **Eight slides at most.** Problem in their words · what we built, in three lines · (the take) · how we know the numbers are right (answer keys) · real versus simulated · limits and next steps · the ask.

## 5. Recording and embedding

Before the take:
- Fresh clone, `pip install -r engine/requirements.txt`, `out/` empty. Run the whole script once to warm up and once more to check the numbers you will say.
- Terminal font 18 pt or more, browser at 110-125%, everything else closed, notifications off.
- The commands in a text file to paste; nothing typed live.
- Narrate, and also put the key sentence of each part on screen: nobody has told us how well the room's sound carries to the remote judges.

After the take:
- Export 1080p MP4, upload to Google Drive, **Insert, Video** in Google Slides.
- Share **both** the slides and the video file as "anyone with the link". The usual failure is a video that only its owner can play.
- Open the link in a private window, logged out, and press play. Then give the link to one of us to try on another machine.
- Submit once by 15:00 and again if anything changes; the last submission before 16:00 counts.

## 6. What must be said or shown (an overclaim costs more than any feature earns)

The organizers check our "built versus used" text against the repo. Saying something is simulated costs nothing. These go on the real-versus-simulated slide and into the form:

- All data is synthetic. No real Goodwill file has been read.
- The provider APIs are assumed (Amanda, for Upright; Dani's decision for the month-end sources) and simulated. All nine month-end sources now reach the close: five from sample files we generated (Upright, eBay, Amazon, ShopGoodwill's periodic report, Cash Monkey's month file) and four from simulated APIs (the Jewelry report, the carriers' bank feed, FedEx's ledger entries, the Goodwill Books statement), every layout ours. The page's nine-source table says which is which for the run on screen: read the count from it.
- 11 of the 15 KPIs rest on a simulated internal API and are badged on the page, the PDF and the CSV.
- The close writes import files in Business Central's column order. Nothing is posted; the files have never been loaded into a Business Central.
- Account, customer and document numbers are placeholders, except Dept 180 and the codes on their slide 38.
- The rules are our reading. We have not seen the allocation workbook.
- No mailbox and no scheduler: a folder stands in for email, a command for the scheduler; emails are drafts, not sent.

For the form, start from the table and the sources list in `docs/pitch/engine_pitch.md` and add: SQLite (in Python), FastAPI and Uvicorn (the static server), headless Edge or Chrome (the PDF), the AI coding tools each of us used. List only what is in the repo, and check the list with Victor and Dani before submitting.

## 7. Questions to be ready for (phases 2 and 3; phase 1 is in `engine_pitch.md`)

| Question | Short honest answer |
|---|---|
| Does this post to Business Central? | No. It writes the General Journal and the AR invoice as files in the page's column order, for paste or Edit in Excel. Posting needs their environment; the status file says "not posted". |
| How do you know the journal is right? | Every document sums to zero or nothing is written; the files are read back and checked again; totals are compared with an answer key computed from the generated orders, not by our code. What we cannot check is their workbook: we have not seen it. |
| What happens when a report is missing? | The close still runs. It names the days no report covers and the amount the marketplace paid that our files cannot explain, and marks the source incomplete. |
| Which of the nine sources do you really read? | All nine reach the close, none of them real. Five from sample files we generated (only Upright's layout comes from their slide), four from simulated APIs. The page says which is which, and what each one is used for. |
| How much of the scorecard is real? | Four KPIs come from the sales files alone. Eleven need internal data we simulate, and each is badged. What is real is the definitions and the plumbing. |
| Could Goodwill start tomorrow? | The nightly report, yes, once one real file of each kind confirms the column names. The close needs their chart of accounts and their workbook's rules first. |
| What would you build next? | Read one real month; replace the placeholder accounts; compare our journal with their workbook line by line; then post through Business Central's API. |

## 8. Your Sunday

| Time | What |
|---|---|
| 11:00 | Arrive. Read this, `engine_pitch.md`, and the three demo scripts. Ask Dani and Victor what is on `main` |
| 11:15 | Build the slides (HTML or not) and the Google Slides shell with the problem slide. Draft "built versus used" and the sources |
| 12:30 | Run the scripts yourself from a fresh clone; note the numbers you will say |
| 13:00 | Dry run with the three of us. `main` takes no more features. Anything not on `main` now goes on the "not built" line |
| 13:30 | Record. A second take, if needed, until 14:30 |
| 14:30 | Video into Google Slides, sharing checked from a private window |
| 15:00 | First submission. From here only bug fixes go into `main` |
| 15:45 | Final submission if anything changed |

What you need from us, and when: the close demo script from Dani by 12:30; the phase 2 script from Victor (his L7; agree with him who writes it); at 13:00, the list of what is on `main` and what is not.

One last thing: the team name on every slide and in the form is spelled exactly as it was registered. It is what the judges see on the ballot.
