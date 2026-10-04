"""Business Central API (v2.0): the month-end close as API requests, built and shown, sent only when configured.

NOT CONNECTED. There is no Business Central for us to reach: no tenant, no credentials, no sandbox. Goodwill
told us (decision 012) that their Business Central is cloud, that the Controller does a recurring entry today,
and that they can also upload CSV; nobody has said the API route is open to us. So the CSV import files are
the path Goodwill named, and this module is a possible later step, the backend half of "load the close into
Business Central", ready for the day there is one:

  - `build_requests` turns the close's two import files (general_journal_<month>.csv, ar_invoice_<month>.csv,
    docs/contracts/close-outputs.md) into the ordered requests of Microsoft's standard API v2.0: one journal
    batch, one journalLine per journal row, one sales invoice per invoice document with its lines, and a
    dimensionSetLine per line for the department.
  - the default run writes those requests to `bc_api_requests_<month>.json` and sends nothing (dry run);
  - `BcClient` signs in with the OAuth client-credentials flow and sends them. It has only ever run against
    a local stand-in in the tests, never against a real Business Central.

DRAFTS ONLY. Nothing here calls the `Microsoft.NAV.post` action: the lines land unposted in a journal batch
and the invoice as a draft, and a person reviews and posts them in Business Central. Sending is refused when
the journal does not balance, when the close needs review and nobody says it was reviewed, and when the
close was built from the synthetic sample months.

What a real tenant needs (environment, see docs/contracts/bc-api.md): BC_TENANT_ID, BC_ENVIRONMENT,
BC_COMPANY_ID, BC_CLIENT_ID, BC_CLIENT_SECRET; and real account, customer and bank account numbers in
reports/config/bc_mapping.csv, where today every one is a placeholder.
"""
import csv
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

from ..scrapers.http import HttpError, HttpSession

API_VERSION = "v2.0"
ONLINE_URL = "https://api.businesscentral.dynamics.com/v2.0/{tenant}/{environment}/api/v2.0"
TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
SCOPE = "https://api.businesscentral.dynamics.com/.default"
ENV_KEYS = ("BC_TENANT_ID", "BC_ENVIRONMENT", "BC_COMPANY_ID", "BC_CLIENT_ID", "BC_CLIENT_SECRET")
DEPARTMENT_DIMENSION = "DEPARTMENT"  # the code of Goodwill's department dimension is not known: BC_DEPARTMENT_DIMENSION


class NotConfigured(Exception):
    """No Business Central to send to: the environment variables are missing."""


class Refused(Exception):
    """The close must not be sent as it is."""


def _iso(us_date: str) -> str:
    return datetime.strptime(us_date, "%m/%d/%Y").date().isoformat()


def _read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_requests(journal: list[dict], invoices: list[dict], month: str, journal_code: str | None = None,
                   dimension: str = DEPARTMENT_DIMENSION) -> list[dict]:
    """The requests that load one month's close as drafts, in the order they must be sent.

    Each is `{"step", "what", "method", "path", "body"}`, with `"id_as"` when a later request needs the id
    Business Central gives back: a later path or body refers to it as `{name}`. `{company}` is the company
    id from the configuration. No request posts anything."""
    requests: list[dict] = []

    def add(what, path, body, id_as=None):
        requests.append({"step": len(requests) + 1, "what": what, "method": "POST", "path": path, "body": body,
                         **({"id_as": id_as} if id_as else {})})

    def department(parent, parent_type, name, code):
        if code:
            add(f"department {code} on {name}", f"companies({{company}})/{parent}({{{name}}})/dimensionSetLines",
                {"code": dimension, "parentId": f"{{{name}}}", "parentType": parent_type, "valueCode": code})

    if journal:
        code = journal_code or f"EC{month[2:4]}{month[5:7]}"  # at most 10 characters
        add(f"journal batch {code}", "companies({company})/journals",
            {"code": code, "displayName": f"E-commerce close {month}"}, id_as="journal")
        for i, row in enumerate(journal, start=1):
            body = {"lineNumber": i * 10000, "accountType": row["Account Type"], "accountNumber": row["Account No."],
                    "postingDate": _iso(row["Posting Date"]), "documentNumber": row["Document No."],
                    "amount": float(row["Amount"]), "description": row["Description"][:100]}
            if row.get("Document Type"):
                # The standard journalLine resource has no document type: it rides along as a comment, and
                # someone sets it on the line in Business Central (or a custom API page exposes the field).
                body["comment"] = f"Document Type: {row['Document Type']}"
            add(f"journal line {i} of {row['Document No.']}", "companies({company})/journals({journal})/journalLines",
                body, id_as=f"line{i}")
            department("journalLines", "Journal Line", f"line{i}", row.get("Department Code"))

    documents: dict[str, list[dict]] = {}
    for row in invoices:
        documents.setdefault(row["Document No."], []).append(row)
    for n, (number, lines) in enumerate(documents.items(), start=1):
        head = lines[0]
        add(f"draft sales invoice {number}", "companies({company})/salesInvoices",
            {"externalDocumentNumber": number, "customerNumber": head["Customer No."],
             "invoiceDate": _iso(head["Posting Date"]), "postingDate": _iso(head["Posting Date"])}, id_as=f"invoice{n}")
        for i, row in enumerate(lines, start=1):
            name = f"invoice{n}line{i}"
            add(f"line {i} of sales invoice {number}", f"companies({{company}})/salesInvoices({{invoice{n}}})/salesInvoiceLines",
                {"lineType": "Account", "lineObjectNumber": row["No."], "description": row["Description"][:100],
                 "quantity": float(row["Quantity"]), "unitPrice": float(row["Unit Price"])}, id_as=name)
            department("salesInvoiceLines", "Sales Invoice Line", name, row.get("Department Code"))
    return requests


def summary(requests: list[dict]) -> dict:
    count = lambda text: sum(text in r["path"] and "dimensionSetLines" not in r["path"] for r in requests)  # noqa: E731
    return {"requests": len(requests), "journal_batches": sum(r["path"].endswith("/journals") for r in requests),
            "journal_lines": count("/journalLines"), "sales_invoices": sum(r["path"].endswith("/salesInvoices") for r in requests),
            "sales_invoice_lines": count("/salesInvoiceLines"),
            "department_dimensions": sum("dimensionSetLines" in r["path"] for r in requests),
            "post_actions": sum("Microsoft.NAV.post" in r["path"] for r in requests)}


def load_close(close_dir: Path, month: str) -> tuple[list[dict], list[dict], dict]:
    """The journal rows, the invoice rows and the status file of the month's last close."""
    folder = Path(close_dir) / month
    try:
        status = json.loads((folder / f"close_status_{month}.json").read_text(encoding="utf-8"))
        return _read(folder / f"general_journal_{month}.csv"), _read(folder / f"ar_invoice_{month}.csv"), status
    except (OSError, ValueError) as e:
        raise Refused(f"no finished close for {month} in {folder}: run `python -m reports.close` first ({e})") from e


def check_sendable(status: dict, reviewed: bool = False, allow_sample: bool = False) -> None:
    """Raise Refused unless this close may be loaded into Business Central."""
    if not status["journal"]["balanced"] or status["posting"].get("problems"):
        raise Refused("the journal does not balance or the files failed the read-back check: never sent")
    if status["needs_review"] and not reviewed:
        raise Refused(f"the close needs review ({status['exceptions']['total']} exceptions); "
                      f"send it only after someone has reviewed it, with --reviewed")
    sample = [p for p in status["inboxes"] if "data/sample" in p.replace("\\", "/") or "close_sources" in p]
    if sample and not allow_sample:
        raise Refused(f"this close was built from synthetic sample data ({', '.join(sample)}): it is not sent to a "
                      f"Business Central. For a sandbox, say so with --allow-sample")


def write_dry_run(close_dir: Path, month: str, requests: list[dict], status: dict) -> Path:
    path = Path(close_dir) / month / f"bc_api_requests_{month}.json"
    doc = {"month": month, "close_run_id": status["run_id"], "sent": False,
           "note": "NOT SENT. These are the requests the close would make to the Business Central API v2.0 to load "
                   "the journal lines and the sales invoice as DRAFTS (nothing is posted). There is no Business "
                   "Central connection; account, customer and bank account numbers are placeholders.",
           "api": {"version": API_VERSION, "base_url": ONLINE_URL, "token_url": TOKEN_URL, "scope": SCOPE,
                   "environment_variables": list(ENV_KEYS)},
           "summary": summary(requests), "requests": requests}
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    return path


class BcClient:
    """Sends the requests. Sign-in is OAuth 2.0 client credentials against Microsoft Entra (an app registered
    in Goodwill's tenant with API.ReadWrite.All). BC_API_URL and BC_TOKEN_URL override the Microsoft addresses
    (an on-premises server, or the stand-in the tests run)."""

    def __init__(self, env: dict[str, str]):
        missing = [k for k in ENV_KEYS if not env.get(k)]
        if missing:
            raise NotConfigured(f"missing environment variables: {', '.join(missing)}")
        self.env = env
        quoted = {k: urllib.parse.quote(env[v], safe="") for k, v in (("tenant", "BC_TENANT_ID"), ("environment", "BC_ENVIRONMENT"))}
        self.base_url = (env.get("BC_API_URL") or ONLINE_URL.format(**quoted)).rstrip("/")
        self.token_url = env.get("BC_TOKEN_URL") or TOKEN_URL.format(**quoted)
        self.session: HttpSession | None = None

    def sign_in(self) -> None:
        _, body, _ = HttpSession().post(self.token_url, {
            "grant_type": "client_credentials", "client_id": self.env["BC_CLIENT_ID"],
            "client_secret": self.env["BC_CLIENT_SECRET"], "scope": SCOPE})
        token = json.loads(body)["access_token"]
        self.session = HttpSession(self.base_url, {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                                   "Accept": "application/json"})

    def send(self, requests: list[dict]) -> dict:
        """Send the requests in order; stop at the first failure. Returns what happened, including the ids
        Business Central gave, so a half-loaded batch can be found and deleted."""
        if any("Microsoft.NAV.post" in r["path"] for r in requests):
            raise Refused("a request would post: this client loads drafts only")
        if self.session is None:
            self.sign_in()
        ids = {"company": self.env["BC_COMPANY_ID"]}
        done = []
        for r in requests:
            # Only the `{name}` references are filled in; a brace in a description is left alone.
            path = re.sub(r"\{(\w+)\}", lambda m: ids.get(m[1], m[0]), r["path"])
            data = {k: ids.get(v[1:-1], v) if isinstance(v, str) and re.fullmatch(r"\{\w+\}", v) else v
                    for k, v in r["body"].items()}
            try:
                _, body, _ = self.session.post(path, json.dumps(data).encode())
                created = json.loads(body) if body else {}
            except (HttpError, ValueError, KeyError) as e:
                return {"sent": len(done), "of": len(requests), "failed_step": r["step"], "what": r["what"],
                        "error": str(e), "ids": {k: v for k, v in ids.items() if k != "company"}}
            if r.get("id_as"):
                ids[r["id_as"]] = created.get("id", "")
            done.append(r["step"])
        return {"sent": len(done), "of": len(requests), "failed_step": None,
                "ids": {k: v for k, v in ids.items() if k != "company"}}
