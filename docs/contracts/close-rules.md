# The rules of the month-end close (D3.10)

- **Owner:** Dani for phase 3 (decision 009). **Readers:** anyone who has to say what "automates the rules" means, and Goodwill, to correct us.
- **Status:** v0.1, 2026-10-04. It describes what is on `main` (the code in `reports/reconcile.py` and `reports/bc_export.py`, the config in `reports/config/`).

Goodwill's slide 41 asks, as workstream 3, for the workbook's rules to be written down: "orange-field inputs, workbook formulas, control totals and source-to-account/dimension mapping". **We have never seen the workbook.** This is the list of the rules *our* close applies, each with where it lives and where it comes from, so that a person at Goodwill can read it and say which ones their workbook does differently. Nothing here has been compared with the workbook.

**From:** `deck` = on a slide (number given) · `assumed` = our reading, listed in `docs/ASSUMPTIONS.md` · `control` = not an accounting rule but a check we chose.

## What goes into the month
| # | Rule | Where it lives | From |
|---|---|---|---|
| 1 | The month is the Eastern calendar month: a row belongs to it by its `business_date` | the engine (`engine/contract.py`); `reports/reconcile.py`, `in_month` | assumed (4.6) |
| 2 | Revenue is sales minus refunds. Shipping and handling charged to buyers, and marketplace fees, are kept apart and posted to their own accounts | `transaction.md`; one account column each in `bc_mapping.csv` | assumed (4.1 to 4.3) |
| 3 | A refund posts in the month it is issued. A refund whose sale is not in the month's files is posted and flagged `prior_month_refund` | `reports/reconcile.py` | assumed (4.2) |
| 4 | A row the engine could not read (bad amount, bad date) is left out and listed. A row downloaded twice counts once | the engine; listed by `reports/reconcile.py` | control |
| 5 | A marketplace with rows but no row in the mapping is not posted and is listed as `unmapped_source` | `reports/reconcile.py`, `reports/bc_export.py` | control |

## What Business Central receives
| # | Rule | Where it lives | From |
|---|---|---|---|
| 6 | Each source posts through exactly one path: a General Journal document, or an AR sales invoice. ShopGoodwill by invoice; eBay and Amazon by journal | `Path` in `bc_mapping.csv` | deck (slide 39: journal entry tabs and one Invoices tab); **which source goes where is assumed** |
| 7 | Journal path, one document per source per month: debit the net receivable to a clearing account; credit sales, shipping charged and handling; debit refunds and marketplace fees | `Clearing_Account`, `Sales_Account`, `Refunds_Account`, `Shipping_Account`, `Handling_Account`, `Fees_Account` | assumed. **Every account number is a placeholder** |
| 8 | Invoice path: one sales invoice per source to its customer, a line each for sales, shipping charged and handling; its fees as a journal document against the customer | `Customer_No` and the same account columns | assumed. The customer number is a placeholder |
| 9 | Every line carries department 180 | `Department_Code` | deck (slide 38 gives "Dept 180" for FedEx); that all of e-commerce is 180 is assumed |
| 10 | Each bank deposit is one journal document on its own date: debit the bank, credit the clearing account (or the customer) | `Bank_Account`; `reports/bc_export.py` | assumed |
| 11 | Posting date is the last day of the month. Documents are numbered `ECOM-<yymm>-<source>`, `SI-ECOM-<yymm>-<source>`, `BNK-<mmdd>-<source>` | `reports/bc_export.py` | assumed |
| 12 | **A document that does not sum to 0.00 is never written**: the export refuses and writes nothing. The written files are read back and checked again | `reports/bc_export.py` | deck (slide 40: "balanced ... journal and invoice payloads") |

## Matching the money
| # | Rule | Where it lives | From |
|---|---|---|---|
| 13 | A bank credit belongs to the source whose text is in its description. A credit no rule matches is `unmatched_deposit` and stays out of the journal | `Bank_Text` | assumed |
| 14 | A deposit pays one or more consecutive payouts of its source, paid on or before its date and at most 5 days earlier, **adding up to it exactly**. No tolerance | `WINDOW_DAYS` in `reports/reconcile.py` | assumed |
| 15 | How each source pays: eBay every day for the day before (Eastern days); Amazon for everything since the last settlement, through the day before it is paid (Pacific days); ShopGoodwill weekly through Sunday (Pacific days), and since it has no payout report each of its deposits is taken as a payout | `Payout_Cutoff`, `Payout_Timezone` | assumed. A payout whose report states its own period keeps that period |
| 16 | Each payout is compared with what our files hold for the days it covers. Equal: nothing to say. Paid more, and the window has days no report covers: `payout_data_gap`, the source reads `INCOMPLETE`. Any other difference: `payout_mismatch`, the source reads `UNEXPLAINED` | `reports/reconcile.py`, `explain_payouts` | control (slide 40: "missing reports ... remain visible for review") |
| 17 | At month end two things are left open and stay a receivable: a payout paid but not yet in the bank (`in_transit`), and activity no payout covers yet (`not_yet_paid_out`, to the cent) | `reports/reconcile.py` | assumed |
| 18 | A payout for activity before the month is `prior_month_payout`. **Last month's open items are not carried over**: the first payout of a month is taken to start on the 1st | `reports/reconcile.py` | not modeled |
| 19 | A day no report covers is `missing_report` | the report file names | control |
| 20 | Cash Monkey's month report is compared with a marketplace's own report order by order, and never added to it | `Cross_Check_Source` | assumed (2c.7); which file the workbook uses is unknown |

## Reading the result
| # | Rule | Where it lives | From |
|---|---|---|---|
| 21 | A source's status, worst first: `MISMATCH` (posted revenue differs from the files), `UNEXPLAINED` (money nobody has accounted for), `INCOMPLETE` (accounted for, but a report is missing), `OPEN` (open and fully explained), `RECONCILED` | `reports/bc_export.py`; `close-payload.md` | control |
| 22 | Every exception has an owner and an action | `reports/config/close_exceptions.csv` | deck asks for "owned exceptions" (slide 40); **the role names are ours** |
| 23 | Every run is archived with its inputs and a manifest, and says `not_posted` | `reports/close.py`; `close-outputs.md` | deck (slides 39 and 40: the archive folder, "run history", "posting status ... retained"); the archive is a local folder |

## Rules Goodwill named that we do not have
These are on slide 38 and nothing on `main` applies them yet (tasks in `docs/PLAN_PHASE_3.md`):
- **Shipping cost:** the bank lookup for OSM, PB and EasyPost (1st Source account 0101, GL 10009) and the FedEx lookup (GL 40356, department 180, vendor V00122, net of BNKDEPOSIT refunds). Tasks V3.5, V3.7, D3.5.
- **Jewelry:** the Jewelry Report and the Supplier that "Co-Pivot" fills in. Task V3.10.
- **ShopGoodwill's periodic reports:** "Period 1 periodic only; Period 3 all reports". We do not know what the periods are. Task V3.8 reads a report of our own design as payouts.
- **Goodwill Books:** the prior-month payment statement. Tasks V3.9, D3.13.
- **Whatever the workbook's formulas do** that is not in the tables above.

## Changelog
- v0.1 (2026-10-04, Dani): first list, from the code on `main` after D3.1 to D3.4, D3.7 to D3.9 and D3.14.
