# 004 — Data acquisition and reporting cutoffs (Amanda, office hours)

- **Date / author:** 2026-10-03, Orlando (answers from Amanda Baumer, Goodwill Michiana, office hours)
- **Status:** accepted

## What Amanda confirmed
1. **Ingestion:** we can assume an API exists for getting the reports in.
2. **Format:** the synthetic data arrives as **emailed Excel files**, which we can convert to CSV for processing.
3. **Brick-and-mortar stores** send reports at **1:00 PM and 10:00 PM Eastern**.
4. **E-commerce reporting finishes at 9:00 PM Pacific**, which is midnight Eastern.

## Decisions
- **Business day for the e-commerce pulse = midnight to midnight Eastern.** That is the same window as "closes at 9 PM Pacific", so it stays the engine default (`America/New_York`, `docs/contracts/transaction.md`). The nightly run happens after midnight Eastern.
- **Ingestion is simulated by a folder.** Exports dropped in `inbox/` stand in for "emailed Excel, delivered through an API". We build no email reader and no API client. The demo and the submission say so.
- **No CSV conversion step.** The engine reads `.xlsx` directly (`openpyxl`, decision 002), as well as `.csv`, so an emailed Excel attachment can go straight into the inbox. Converting to CSV first would add a step without changing the result.
- **Stores stay out of the nightly pulse.** Phase 1 is e-commerce only (`docs/contracts/pulse.md`, Q12 default). If stores are added, their 10 PM Eastern report already lands before the midnight Eastern run, so the same run covers them; the 1 PM report would only be a midday preview.

## Evidence (run on 2026-10-03 against `main`)
- `python -m engine run` on every sample inbox in `data/sample/` matches each `expected.json` answer key on **112 of 112 marketplace-days** (revenue and order count), and drops the 46 planted duplicates in `day_duplicates`.
- **Cutoff check:** in `clean_month`, the **23** Amazon orders stamped **9:00 PM PDT or later** are all assigned to the **next** Eastern day, and the **17** stamped 8:00 to 8:59 PM PDT stay on the same day.

## Limits (what is not proven yet)
- The cutoff is right when a timestamp carries its zone (`PDT`, `Z`, `+00:00`). The engine reads a timestamp **without** a zone as already Eastern (`engine/clean.py`, `parse_business_date`). Upright (Pacific, chosen in the report form) and Cash Monkey (UTC) may export plain timestamps, which would put orders near midnight on the wrong day. Needed: a timezone setting per source (Victor).
- Our sample exports imitate the eBay, Amazon and ShopGoodwill seller reports, not the Upright and Cash Monkey files Goodwill uses (`docs/contracts/source-formats.md`). Only the ShopGoodwill sample is Excel; the eBay and Amazon samples are CSV.
- Still open from office hours: the revenue definition (Q5) and which day a refund counts on. The defaults in `transaction.md` apply until answered.

## Consequences
- `run_nightly` stands in for a scheduled job after midnight Eastern; in production it would be triggered by the API delivery or by Windows Task Scheduler.
- Next in Orlando's lane: Upright and Cash Monkey sample files, delivered as `.xlsx`, so the demo inbox looks like what arrives by email.
