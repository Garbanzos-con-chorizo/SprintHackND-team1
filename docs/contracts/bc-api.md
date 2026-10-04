# Contract: the close as Business Central API requests (API-ready, not connected)

- **Owner:** Victor (`engine/export/bc_api.py`). **Reads:** the close's outputs (`docs/contracts/close-outputs.md`, Dani). **Consumers:** nobody yet: this is the backend for a later "load into Business Central" step.
- **Status:** v0.1, 2026-10-04. **Built and tested against a local stand-in. Never run against a real Business Central**: we have no tenant, no sandbox and no credentials.
- **What does not change:** the close still writes import files and posts nothing (`docs/ASSUMPTIONS.md` 1.2, decision 007 point 7). This adds a second way to hand over the same lines.

## What to say about it (and what not to)
- **Say:** "The close writes import files today. The backend can also produce the same lines as requests to Business Central's standard API, and has a client that loads them as drafts for a person to review and post. It has never been connected to a Business Central."
- **Do not say:** "integrated with Business Central", "posts to Business Central", or anything that suggests a connection exists.

## The command
```
python -m engine.export bc-api --month 2026-09                       # dry run: writes the requests, sends nothing
python -m engine.export bc-api --month 2026-09 --send [--reviewed] [--allow-sample]
```
Run it after `python -m reports.close` for that month. `--close-dir` names the close's `--out` folder (default `out/close`).

**Dry run (the default).** Reads `general_journal_<month>.csv`, `ar_invoice_<month>.csv` and `close_status_<month>.json`, and writes `out/close/<month>/bc_api_requests_<month>.json`:
```json
{ "month": "2026-09", "close_run_id": "2026-10-04T13-14-44", "sent": false,
  "note": "NOT SENT. These are the requests the close would make to the Business Central API v2.0 ...",
  "api": { "version": "v2.0", "base_url": "https://api.businesscentral.dynamics.com/v2.0/{tenant}/{environment}/api/v2.0",
           "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
           "scope": "https://api.businesscentral.dynamics.com/.default",
           "environment_variables": ["BC_TENANT_ID", "BC_ENVIRONMENT", "BC_COMPANY_ID", "BC_CLIENT_ID", "BC_CLIENT_SECRET"] },
  "summary": { "requests": 120, "journal_batches": 1, "journal_lines": 56, "sales_invoices": 1,
               "sales_invoice_lines": 3, "department_dimensions": 59, "post_actions": 0 },
  "requests": [ { "step": 1, "what": "journal batch EC2609", "method": "POST",
                  "path": "companies({company})/journals", "body": { "code": "EC2609", "displayName": "E-commerce close 2026-09" },
                  "id_as": "journal" } ] }
```
The summary above is the messy sample month. `{company}` is the company id from the configuration; `{journal}`, `{line1}` and the like are ids Business Central returns for an earlier request (`id_as`).

## The requests, in order
All are `POST` to Microsoft's standard API v2.0. The field names are from Microsoft's reference pages (linked below).

| What | Path | Body, from our file |
|---|---|---|
| One journal batch for the month | `companies({company})/journals` | `code` (`EC<yymm>`), `displayName` |
| One line per row of the General Journal file | `companies({company})/journals({journal})/journalLines` | `lineNumber`, `accountType` (`G/L Account`, `Customer`, `Bank Account`), `accountNumber`, `postingDate`, `documentNumber`, `amount`, `description` |
| The department of each line | `companies({company})/journalLines({line})/dimensionSetLines` | `code` (the department dimension), `valueCode` (`180`), `parentId`, `parentType` |
| One draft sales invoice per invoice document | `companies({company})/salesInvoices` | `externalDocumentNumber` (our document number), `customerNumber`, `invoiceDate`, `postingDate` |
| One line per row of the invoice file | `companies({company})/salesInvoices({invoice})/salesInvoiceLines` | `lineType` `Account`, `lineObjectNumber` (the G/L account), `description`, `quantity`, `unitPrice` |
| The department of each invoice line | `companies({company})/salesInvoiceLines({line})/dimensionSetLines` | as above |

**Drafts only.** No request calls `Microsoft.NAV.post`. The journal lines land unposted in their batch and the invoice as a draft; a person reviews and posts them in Business Central. The client refuses any request list that contains a post action.

## Sending (`--send`)
Sign-in is the OAuth 2.0 client-credentials flow against Microsoft Entra: an app registered in Goodwill's tenant, granted `API.ReadWrite.All` on Dynamics 365 Business Central with admin consent, and given a permission set inside Business Central. Configuration is environment variables (or a `.env` file, which git ignores; names in `.env.example`):

| Variable | Meaning |
|---|---|
| `BC_TENANT_ID`, `BC_ENVIRONMENT`, `BC_COMPANY_ID` | Which Business Central: the Entra tenant, the environment name (`Production`, `Sandbox`), the company's id |
| `BC_CLIENT_ID`, `BC_CLIENT_SECRET` | The registered app |
| `BC_DEPARTMENT_DIMENSION` | Code of the department dimension. Default `DEPARTMENT`, a guess |
| `BC_API_URL`, `BC_TOKEN_URL` | Optional: replace Microsoft's addresses (an on-premises server; the tests' stand-in) |

Sending is **refused**, with nothing sent, when:
- the journal does not balance, or the files failed the close's read-back check;
- the close reads `needs_review` and `--reviewed` was not given (someone has to have looked);
- the close was built from the synthetic samples or the simulated sources and `--allow-sample` was not given (a sandbox is the only place for those);
- a variable is missing (`not configured`).

A request that fails stops the run. The message says how many went through and to delete the journal batch and any draft invoice before sending again: there is no automatic undo.

## Known gaps (untested against a real tenant)
- **Nothing has been sent to a real Business Central.** The request shapes follow Microsoft's reference pages; which optional fields a given tenant requires is unknown.
- **Document Type** (`Payment` on the deposit documents) has no field in the standard `journalLine` resource. It is sent as the line's `comment`; someone sets it in Business Central, or a custom API page exposes the field.
- **The department dimension** is sent by code (`code`, `valueCode`). Microsoft's example also carries ids; a tenant may require them.
- **Every account, customer and bank account number is a placeholder** (`reports/config/bc_mapping.csv`), except department 180. A real tenant would reject them.
- **The journal batch is created new each time** (`EC<yymm>`). If it already exists the first request fails and nothing else is sent.
- **Business Central numbers the invoice itself**; our document number goes in `externalDocumentNumber`.
- No button on the close page calls this. The page is static and the server has no sign-in; a button that writes to a ledger needs both first.

## References
- [journal](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/resources/dynamics_journal) and [journalLine](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/resources/dynamics_journalline) resource types
- [Create dimensionSetLines](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/api/dynamics_dimensionsetline_create)
- [salesInvoice](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/resources/dynamics_salesinvoice) and [salesInvoiceLine](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/resources/dynamics_salesinvoiceline) resource types
- [Service-to-service authentication](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/administration/automation-apis-using-s2s-authentication)

## Changelog
- v0.1 (2026-10-04, Victor): the request builder, the dry-run file, the client, the refusals. Tests: `engine/tests/test_export_bc_api.py` (12, the client against a local stand-in).
