"""The close as Business Central API requests (docs/contracts/bc-api.md): built, written as a dry run, and
sent only against a LOCAL STAND-IN here. Nothing in the project has ever talked to a real Business Central."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from engine.export import bc_api
from engine.export.cli import main

MONTH = "2026-09"
JOURNAL = ("Posting Date,Document Type,Document No.,Account Type,Account No.,Description,Amount,Department Code\n"
           "09/30/2026,,ECOM-2609-EBAY,G/L Account,11310,eBay net receivable Sep 2026,100.00,180\n"
           "09/30/2026,,ECOM-2609-EBAY,G/L Account,40120,eBay sales {Sep} 2026,-100.00,180\n"
           "09/04/2026,Payment,BNK-0904-EBAY,Bank Account,OPERATING,deposit,40.00,180\n"
           "09/04/2026,Payment,BNK-0904-EBAY,G/L Account,11310,deposit,-40.00,\n")
INVOICE = ("Document No.,Customer No.,Posting Date,Type,No.,Description,Quantity,Unit Price,Amount,Department Code\n"
           "SI-ECOM-2609-SGW,C-SHOPGOODWILL,09/30/2026,G/L Account,40110,ShopGoodwill sales Sep 2026,1,391.18,391.18,180\n"
           "SI-ECOM-2609-SGW,C-SHOPGOODWILL,09/30/2026,G/L Account,40131,ShopGoodwill shipping Sep 2026,1,14.28,14.28,180\n")
ENV = {"BC_TENANT_ID": "tenant-1", "BC_ENVIRONMENT": "Sandbox", "BC_COMPANY_ID": "company-1",
       "BC_CLIENT_ID": "client-1", "BC_CLIENT_SECRET": "not-a-real-secret"}


def status(needs_review=False, inboxes=("inbox/2026-09",), balanced=True, problems=()):
    return {"month": MONTH, "run_id": "2026-10-01T00-15-07", "inboxes": list(inboxes), "needs_review": needs_review,
            "journal": {"lines": 4, "documents": 2, "balanced": balanced}, "invoices": {"documents": 1, "lines": 2},
            "exceptions": {"total": 3}, "posting": {"status": "not_posted", "problems": list(problems)}}


def write_close(root: Path, **kw) -> Path:
    folder = root / MONTH
    folder.mkdir(parents=True)
    (folder / f"general_journal_{MONTH}.csv").write_text(JOURNAL, encoding="utf-8")
    (folder / f"ar_invoice_{MONTH}.csv").write_text(INVOICE, encoding="utf-8")
    (folder / f"close_status_{MONTH}.json").write_text(json.dumps(status(**kw)), encoding="utf-8")
    return root


def requests_for(tmp_path):
    journal, invoices, _ = bc_api.load_close(write_close(tmp_path / "close"), MONTH)
    return bc_api.build_requests(journal, invoices, MONTH)


def test_the_requests_follow_the_api_and_never_post(tmp_path):
    requests = requests_for(tmp_path)
    assert [r["step"] for r in requests] == list(range(1, len(requests) + 1))
    assert all(r["method"] == "POST" and "Microsoft.NAV.post" not in r["path"] for r in requests)
    assert bc_api.summary(requests) == {"requests": 13, "journal_batches": 1, "journal_lines": 4, "sales_invoices": 1,
                                        "sales_invoice_lines": 2, "department_dimensions": 5, "post_actions": 0}
    batch, line, dimension = requests[0], requests[1], requests[2]
    assert batch["path"] == "companies({company})/journals" and batch["body"]["code"] == "EC2609" and batch["id_as"] == "journal"
    assert line["path"] == "companies({company})/journals({journal})/journalLines"
    assert line["body"] == {"lineNumber": 10000, "accountType": "G/L Account", "accountNumber": "11310",
                            "postingDate": "2026-09-30", "documentNumber": "ECOM-2609-EBAY", "amount": 100.0,
                            "description": "eBay net receivable Sep 2026"}
    assert dimension["path"] == "companies({company})/journalLines({line1})/dimensionSetLines"
    assert dimension["body"] == {"code": "DEPARTMENT", "parentId": "{line1}", "parentType": "Journal Line", "valueCode": "180"}
    lines = [r for r in requests if r["path"].endswith("/journalLines")]
    # The amounts are the file's: every document still sums to zero.
    for document in {r["body"]["documentNumber"] for r in lines}:
        assert round(sum(r["body"]["amount"] for r in lines if r["body"]["documentNumber"] == document), 2) == 0
    # A document type has no field in the standard journalLine resource: it is carried as a comment.
    assert [r["body"].get("comment") for r in lines] == [None, None, "Document Type: Payment", "Document Type: Payment"]
    # A line without a department gets no dimension request.
    assert not [r for r in requests if r["path"] == "companies({company})/journalLines({line4})/dimensionSetLines"]
    invoice = next(r for r in requests if r["path"].endswith("/salesInvoices"))
    assert invoice["body"] == {"externalDocumentNumber": "SI-ECOM-2609-SGW", "customerNumber": "C-SHOPGOODWILL",
                               "invoiceDate": "2026-09-30", "postingDate": "2026-09-30"}
    first = next(r for r in requests if r["path"].endswith("/salesInvoiceLines"))
    assert first["path"] == "companies({company})/salesInvoices({invoice1})/salesInvoiceLines"
    assert first["body"] == {"lineType": "Account", "lineObjectNumber": "40110", "description": "ShopGoodwill sales Sep 2026",
                             "quantity": 1.0, "unitPrice": 391.18}


def test_the_default_is_a_dry_run_that_says_it_sent_nothing(tmp_path, capsys):
    close = write_close(tmp_path / "close", needs_review=True, inboxes=("data/sample/messy_month/inbox",))
    assert main(["bc-api", "--month", MONTH, "--close-dir", str(close)]) == 0
    out = capsys.readouterr().out
    assert "13 Business Central API requests" in out and "NOT SENT (dry run" in out and "nothing here posts" in out
    doc = json.loads((close / MONTH / f"bc_api_requests_{MONTH}.json").read_text(encoding="utf-8"))
    assert doc["sent"] is False and doc["note"].startswith("NOT SENT") and "placeholders" in doc["note"]
    assert doc["summary"]["post_actions"] == 0 and len(doc["requests"]) == 13
    assert doc["api"]["environment_variables"] == list(bc_api.ENV_KEYS)
    assert "not-a-real-secret" not in json.dumps(doc)


@pytest.mark.parametrize("kw, flags, reason", [
    ({"balanced": False}, ["--reviewed", "--allow-sample"], "does not balance"),
    ({"problems": ["general_journal: a document does not sum to 0.00"]}, ["--reviewed", "--allow-sample"], "read-back"),
    ({"needs_review": True}, ["--allow-sample"], "needs review"),
    ({"inboxes": ("data/sample/messy_month/inbox",)}, ["--reviewed"], "synthetic sample data"),
    ({"inboxes": ("inbox/real", "out/close_sources/2026-09/inbox")}, ["--reviewed"], "synthetic sample data"),
])
def test_sending_is_refused(tmp_path, capsys, kw, flags, reason):
    close = write_close(tmp_path / "close", **kw)
    assert main(["bc-api", "--month", MONTH, "--close-dir", str(close), "--send", *flags]) == 1
    err = capsys.readouterr().err
    assert "REFUSED, nothing sent" in err and reason in err


def test_without_credentials_nothing_is_sent(tmp_path, capsys, monkeypatch):
    for key in bc_api.ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    close = write_close(tmp_path / "close")
    assert main(["bc-api", "--month", MONTH, "--close-dir", str(close), "--send"]) == 1
    assert "not configured, nothing sent: missing environment variables: BC_TENANT_ID" in capsys.readouterr().err


def test_a_month_with_no_close_is_refused(tmp_path, capsys):
    assert main(["bc-api", "--month", MONTH, "--close-dir", str(tmp_path)]) == 1
    assert "no finished close for 2026-09" in capsys.readouterr().err


# ---------------------------------------------------------------- sending, against a local stand-in

@pytest.fixture
def stand_in():
    """A local stand-in for Microsoft's token endpoint and the Business Central API: it records every call
    and answers each create with an id. `fail_at` makes the nth API call fail."""
    calls, state = [], {"fail_at": None}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if self.path == "/token":
                calls.append(("token", dict(p.split("=", 1) for p in body.decode().split("&")), None))
                return self._reply(200, {"access_token": "stand-in-token"})
            calls.append((self.path, json.loads(body), self.headers.get("Authorization")))
            n = sum(1 for c in calls if c[0] != "token")
            if state["fail_at"] == n:
                return self._reply(400, {"error": "stand-in refuses this one"})
            self._reply(201, {"id": f"id-{n}"})

        def _reply(self, code, payload):
            data = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield {**ENV, "BC_API_URL": f"{url}/api/v2.0", "BC_TOKEN_URL": f"{url}/token"}, calls, state
    httpd.shutdown()


def test_the_client_signs_in_and_loads_the_drafts_in_order(tmp_path, stand_in):
    env, calls, _ = stand_in
    requests = requests_for(tmp_path)
    result = bc_api.BcClient(env).send(requests)
    assert result["sent"] == result["of"] == 13 and result["failed_step"] is None
    token, api = calls[0], calls[1:]
    assert token[0] == "token" and token[1]["grant_type"] == "client_credentials" and token[1]["client_id"] == "client-1"
    assert all(auth == "Bearer stand-in-token" for _, _, auth in api)
    # The ids Business Central gave are used by the requests that follow.
    assert [p for p, _, _ in api][:3] == ["/api/v2.0/companies(company-1)/journals",
                                         "/api/v2.0/companies(company-1)/journals(id-1)/journalLines",
                                         "/api/v2.0/companies(company-1)/journalLines(id-2)/dimensionSetLines"]
    assert api[2][1]["parentId"] == "id-2"
    assert api[-2][0] == "/api/v2.0/companies(company-1)/salesInvoices(id-9)/salesInvoiceLines"
    assert api[3][1]["description"] == "eBay sales {Sep} 2026"  # a brace in a description is left alone
    assert not [p for p, _, _ in api if "Microsoft.NAV.post" in p]  # drafts only
    assert result["ids"]["journal"] == "id-1" and result["ids"]["invoice1"] == "id-9"


def test_a_failure_stops_the_run_and_says_what_went_through(tmp_path, stand_in, capsys, monkeypatch):
    env, calls, state = stand_in
    state["fail_at"] = 4
    close = write_close(tmp_path / "close")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert main(["bc-api", "--month", MONTH, "--close-dir", str(close), "--send"]) == 1
    err = capsys.readouterr().err
    assert "STOPPED at request 4 of 13" in err and "3 request(s) went through" in err and "delete the journal batch" in err
    assert len([c for c in calls if c[0] != "token"]) == 4  # nothing after the failure


def test_a_request_that_would_post_is_never_sent(stand_in):
    env, calls, _ = stand_in
    bad = [{"step": 1, "what": "post", "method": "POST", "path": "companies({company})/journals(x)/Microsoft.NAV.post", "body": {}}]
    with pytest.raises(bc_api.Refused):
        bc_api.BcClient(env).send(bad)
    assert calls == []
