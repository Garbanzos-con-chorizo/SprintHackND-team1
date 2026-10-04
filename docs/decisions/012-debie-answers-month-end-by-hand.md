# 012 — Debie's answers: the month-end reports are downloaded by hand; Business Central is cloud and takes CSV

- **Date / author:** 2026-10-04 13:45 EDT, Dani
- **Status:** accepted (it records a partner's answer; the wording changes that follow from it are listed below)
- **Changes:** `docs/ASSUMPTIONS.md` 1.2 and 2c.1; `docs/PLAN_PHASE_3.md` section 6, questions 16 and 1. Nothing in decisions 009 or 010 changes.

## Context
On Sunday Dani emailed Debie Coble (President and CEO, Goodwill Industries of Michiana) two questions about the month-end close, the two the phase 3 plan ranks first:

1. For each month-end source (the Jewelry report, the bank activity for account 0101, the Business Central ledger entries, ShopGoodwill's periodic reports, the Goodwill Books statement): is there an API or a report that can be scheduled and emailed, or does someone download it by hand?
2. How do entries go into Business Central today, and is it cloud or on-premises?

Her reply, in full:

> For question 1, Controller downloads it by hand.
> Find question 2. It is cloud. Controller does a recurring entry and changes the monthly amount. We can also do CSV uploads.

## Decision
1. **The month-end reports are downloaded by hand, by the Controller.** That is a fact from Goodwill now, and it replaces assumption 2c.1 ("each source can be fetched through an API") as a description of today's process. No API and no scheduled report exists for these sources as far as we have been told.
2. **The simulated APIs stay in the code, described as what they are:** a stand-in for the Controller's download, and a possible later step. No page, script or slide may say or imply that the program fetches these sources from Goodwill's systems.
3. **The file drop is the real path.** The close already reads files from a folder (`python -m reports.close --inbox`). The month's close page gets a file picker beside each of the nine sources, so the person who downloaded a report can hand it over without a terminal. The pickers use the routes of decision 010 (`/api/close/<month>/...`, `reports/close_upload.py`): same limits, same `out/uploads/<month>/` folder, same close. Nothing new on the server.
4. **Business Central is cloud, and CSV upload is possible.** Assumption 1.2 (we write import files and post nothing) stands, and the format is confirmed as usable in principle. We have not tested an import, so "import-ready" remains a claim about the column order only.
5. **Recorded as heard, not interpreted further:** "Controller does a recurring entry and changes the monthly amount." Our reading (Dani's, not confirmed): Business Central's recurring journal, with fixed lines and one amount typed each month. If so, Goodwill's entry is far shorter than the journal we write (65 lines in 28 documents for the messy September). We do not change the journal on this reading; it is a question for a follow-up.

## Consequences
- **Close page** (`reports/close_report.py`): above the nine-source table it says the Controller downloads these reports by hand and who told us; the note on "simulated API" says Goodwill has no such API today; each source has a file picker and one button runs the close again with the chosen files.
- **Pitch and "built versus used"** (Orlando): say "the Controller still downloads the reports; we automate everything after the download" and "Goodwill confirmed Business Central is cloud and accepts CSV uploads". Do not say "integrated with" or "fetches from" for any month-end source.
- **Victor's files** (`README.md`, `engine/README.md`, the close email, `docs/pitch/demo_script_close.md`): where they say "simulated API", the reader should also learn that today the report is downloaded by hand. A note is in his requests; his files are not edited here.
- **Still open:** which CSV upload route Goodwill means (Edit in Excel, a configuration package, a data exchange definition), and what the recurring entry's lines are. Questions 2 to 15 of the plan's section 6 are not answered.
- The demo is unchanged except that the browser step of decision 010 can also be done on the month's own page, source by source.
