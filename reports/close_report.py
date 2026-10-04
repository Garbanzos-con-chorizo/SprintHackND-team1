"""Month-end close page: what `reports.bc_export` produced, for the people who post it.

Reads out/close/<YYYY-MM>/ (control totals, exceptions, General Journal, AR invoice; and, when they are
there, the close payload, the engine's files and the run history) and writes reports/close/<YYYY-MM>.html:
what is simulated, the reconciliation status per source, the exceptions to work with who owns each,
shipping cost per carrier, the Cash Monkey cross-check, Goodwill's nine month-end sources with what this
run has for each and a file picker beside each one (below), jewelry sales by supplier, and a block of
download buttons for the export files (copied next to the page). The explanations of each table sit in a "Notes and Definitions" dropdown at the bottom;
an asterisk beside a heading opens it.

The nine sources and their wording come from reports/config/close_sources.csv (deck slide 38). `Detect`
says how the page knows a source reached this run; `When_Absent` is what it says otherwise ("not in
this inbox" now that the engine reads all nine; "not modeled" for a source nothing reads).

The file pickers: Goodwill's Controller downloads the month-end reports by hand (Debie Coble, 2026-10-04;
decision 012), so each of the nine sources has a place to choose the downloaded file. The chosen files go to
the server's /api/close/<month>/ routes (decision 010, reports/close_upload.py), which keep them in
out/uploads/<month>/ and run the same close again. The page computes nothing; opened from disk, it says it
needs the server.

    python -m reports.close_report --month 2026-09
"""
import argparse
import csv
import json
import re
import shutil
from collections import defaultdict
from datetime import date
from html import escape
from pathlib import Path

from reports.pulse import CSS, PAGE, ast, notes

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "close"
DEST = ROOT / "reports" / "close"
SOURCES = ROOT / "reports" / "config" / "close_sources.csv"
FILES = [("general_journal", "General Journal"), ("ar_invoice", "AR Invoice"),
         ("control_totals", "Control Totals"), ("exceptions", "Exceptions")]
OPTIONAL = [("shipping_costs", "Shipping Costs")]  # written since D3.5; a folder from before has none
TO_IMPORT = {"general_journal", "ar_invoice"}  # the two files that go into Business Central; the rest are for review
STATUS_CLASS = {"RECONCILED": "ok", "OPEN": "stale", "INCOMPLETE": "missing", "UNEXPLAINED": "missing",
                "MISMATCH": "missing"}
LABELS = {"cashmonkey": "Cash Monkey"}

CLOSE_CSS = """
main { max-width:1100px; }
h2.sec { font-size:13px; color:var(--primary); text-transform:uppercase; letter-spacing:.05em; margin:20px 0 6px; }
.pill.stale { background:var(--ink); color:#fff; }
td.detail { white-space:normal; text-align:left; max-width:520px; }
td.text, th.text { white-space:normal; text-align:left; }
td.owner { text-align:left; }
table.tight th, table.tight td { padding-left:8px; padding-right:8px; }
table.tight th { white-space:normal; }
/* The export files: one button each, right under the summary. */
.export { padding:14px 16px; margin:16px 0 0; overflow:visible; border-left:5px solid var(--primary); }
.export h2.sec { margin:0 0 10px; }
.export .actions { margin:0; }
.export .hint { margin:10px 0 0; font-size:14px; color:var(--muted); }
.simnote { margin:12px 0 0; font-size:13px; border:1px dashed var(--ink); padding:8px 12px; border-radius:var(--radius); }
/* One file picker per month-end source, and the button that hands the chosen files to the close. */
td.pick, th.pick { white-space:normal; text-align:left; }
td.pick input[type=file] { font:inherit; font-size:13px; max-width:230px; }
.byhand { margin:0 0 8px; font-size:15px; }
.pickrun { padding:12px 16px; margin:8px 0 0; overflow:visible; border-left:5px solid var(--primary); }
.pickrun .actions { margin:0; }
.pickrun [hidden] { display:none; }
.pickrun p { margin:8px 0 0; font-size:13px; color:var(--muted); }
.pickrun p#pick-state { min-height:1.5em; font-size:15px; font-weight:600; color:var(--ink); }
.pickrun p#pick-state.bad { color:var(--down); }
.state { font-weight:700; }
.state.absent { font-weight:400; color:var(--muted); }
@media print {
  @page { size:letter portrait; margin:0.4in; }
  body { font-size:8.5pt; }
  table { font-size:7.5pt; }
  th, td { padding:3px 5px; }
  td.detail { max-width:none; }
  .simnote { font-size:7.5pt; padding:3px 6px; }
  .export, .nav, .pick, .pickrun { display:none; }
}
"""


BY_HAND = ("Goodwill's Controller downloads these reports by hand today (Debie Coble, President and CEO, "
           "2026-10-04). Nothing in Goodwill's process fetches them, so the close starts from the downloaded files.")

# Sends the files chosen beside the sources to the server, asks it to run the close again and reloads the page.
# The server does the work (reports.close_upload, decision 010); opened from disk, the pickers say they need it.
PICK_SCRIPT = """<script>
(function () {
  var box = document.getElementById("pick");
  if (!box) return;
  var api = "../api/close/" + box.dataset.month, head = { "X-Reports": "1" };
  var picks = [].slice.call(document.querySelectorAll("input.src-file"));
  var run = document.getElementById("pick-run"), clear = document.getElementById("pick-clear");
  var state = document.getElementById("pick-state");
  function say(text, bad) { state.textContent = text; state.className = bad ? "bad" : ""; }
  function off(text) { picks.forEach(function (p) { p.disabled = true; }); run.disabled = true; clear.hidden = true; say(text); }
  function json(r) { return r.json(); }
  function again() { return fetch(api + "/run", { method: "POST", headers: head }).then(json).then(function (d) {
    if (!d.ok) throw new Error(d.error || (d.log || []).slice(-2).join(" ") || "the close did not run");
    say("Done. Loading the new result...");
    location.reload();
  }); }
  function fail(e) { run.disabled = clear.disabled = false; say("Not done: " + e.message, true); }
  if (location.protocol === "file:") return off("Choosing files needs the report server: run python server.py and open http://127.0.0.1:8000/");
  fetch(api + "/uploads").then(json).then(function (d) {
    if (!d.enabled) return off("Adding files is switched off on this server.");
    clear.hidden = !(d.files || []).length;
    if (!clear.hidden) say("Added so far: " + d.files.join(", "));
  }).catch(function () { off("Choosing files needs the report server (python server.py)."); });
  run.addEventListener("click", function () {
    var files = [], seen = {};
    picks.forEach(function (p) { [].forEach.call(p.files, function (f) { if (!seen[f.name]) { seen[f.name] = 1; files.push(f); } }); });
    if (!files.length) return say("Choose a downloaded file beside at least one source first.", true);
    run.disabled = true;
    say("Adding " + files.length + " file(s)...");
    files.reduce(function (before, f) { return before.then(function () {
      return fetch(api + "/uploads/" + encodeURIComponent(f.name), { method: "PUT", headers: head, body: f }).then(json)
        .then(function (d) { if (!d.ok) throw new Error(d.error || d.detail || "the file was not accepted"); });
    }); }, Promise.resolve()).then(function () { say("Running the close again..."); return again(); }).catch(fail);
  });
  clear.addEventListener("click", function () {
    clear.disabled = true;
    say("Removing the added files and running the close again...");
    fetch(api + "/uploads", { method: "DELETE", headers: head }).then(json).then(again).catch(fail);
  });
})();
</script>"""


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_if_there(path):
    return read(path) if path.exists() else []


def cents(text):
    return round(float(text) * 100) if text not in ("", None) else 0


def money(c):
    return f"{'-' if c < 0 else ''}${abs(c) / 100:,.2f}"


def headline(control, journal_docs, exceptions):
    bad = [r for r in control if r["Status"] in ("INCOMPLETE", "UNEXPLAINED", "MISMATCH")]
    parts = [f"{journal_docs} journal documents, all balanced to 0.00"]
    parts.append(", ".join(f"{r['Source']} {r['Status']}" + (f" ({money(cents(r['Unexplained']))})" if r["Status"] == "UNEXPLAINED" else "")
                           for r in control))
    parts.append(f"{len(exceptions)} exceptions")
    return "; ".join(parts) + ".", bool(bad)


def source_states(folder, payload, path=SOURCES):
    """Goodwill's nine month-end sources and what this run has for each: (config row, present, note)."""
    engine = folder / "engine"
    bank, payouts = read_if_there(engine / "bank.csv"), read_if_there(engine / "payouts.csv")
    missing = {e["source"] for e in payload.get("exceptions", []) if e["kind"] == "missing_report"}
    states = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            how, _, what = row["Detect"].partition(":")
            present = {
                "marketplace": lambda: what in payload.get("sources", {}),
                "cross_check": lambda: any(c["against"] == what for c in payload.get("cross_checks", [])),
                "engine_file": lambda: bool(read_if_there(engine / what)),
                "bank_account": lambda: any(r.get("account") == what for r in bank),
                "payout_period": lambda: any(r["marketplace"] == what and r.get("period_from") for r in payouts),
            }[how]()
            note = "a report is missing for some days: see the exceptions" if how == "marketplace" and what in missing else ""
            states.append((row, present, note))
    return states


def render(month, folder):
    t = {k: read(folder / f"{k}_{month}.csv") for k, _ in FILES}
    shipping_rows = read_if_there(folder / f"shipping_costs_{month}.csv")
    payload_file = folder / f"close_payload_{month}.json"
    payload = json.loads(payload_file.read_text(encoding="utf-8")) if payload_file.exists() else {}
    docs = defaultdict(int)
    for line in t["general_journal"]:
        docs[line["Document No."]] += cents(line["Amount"])
    unbalanced = [d for d, c in docs.items() if c]
    text, alert = headline(t["control_totals"], len(docs), t["exceptions"])
    if unbalanced:
        text, alert = f"Journal does not balance: {', '.join(unbalanced)}.", True
    cols = ["Revenue In", "Revenue Posted", "Receivable Posted", "Deposits", "Open Balance", "Explained", "Unexplained"]
    control_rows = "\n".join(
        f'<tr><td>{escape(r["Source"])}</td><td>{escape(r["Path"])}</td>'
        + "".join(f"<td>{money(cents(r[c]))}</td>" for c in cols)
        + f'<td class="status"><span class="pill {STATUS_CLASS.get(r["Status"], "")}">{escape(r["Status"])}</span></td></tr>'
        for r in t["control_totals"])
    order = {"open_balance": 0, "not_posted": 1, "info": 2}
    exc = sorted(t["exceptions"], key=lambda e: (order.get(e["Effect"], 3), e["Source"], e["Kind"]))
    exc_rows = "\n".join(
        f'<tr><td>{escape(e["Kind"].replace("_", " "))}</td><td>{escape(e["Source"])}</td>'
        f'<td>{money(cents(e["Amount"])) if e["Amount"] else ""}</td><td>{escape(e["Effect"].replace("_", " "))}</td>'
        f'<td class="detail">{escape(e["Detail"])}</td><td class="owner">{escape(e.get("Owner") or "")}</td>'
        f'<td class="text">{escape(e.get("Action") or "")}</td></tr>' for e in exc)

    checks = note_checks = note_sources = note_shipping = note_jewelry = ""
    if payload.get("cross_checks"):
        rows = "\n".join(
            f'<tr><td>{escape(c["source"])}</td><td>{money(c["report_sales_cents"])}</td>'
            f'<td>{money(c["against_sales_cents"])}</td><td>{money(c["difference_cents"])}</td>'
            f'<td>{c["orders_only_in_against"]}</td><td>{c["orders_only_in_report"]}</td>'
            f'<td>{c["orders_with_another_amount"]}</td></tr>' for c in payload["cross_checks"])
        other = LABELS.get(payload["cross_checks"][0]["against"], payload["cross_checks"][0]["against"])
        note_checks = (f"Compared order by order, sales only. The journal posts each marketplace from its own reports; "
                       f"the {escape(other)} file is never added to them.")
        checks = (f'<h2 class="sec">Cross-check: {escape(other)} against each marketplace\'s own reports{ast(note_checks)}</h2>'
                  f'<div class="card"><table><thead><tr><th>Marketplace</th><th>Sales in its reports</th>'
                  f'<th>Sales in {escape(other)}</th><th>Difference</th><th>Orders only in {escape(other)}</th>'
                  f'<th>Orders only in the reports</th><th>Orders with another amount</th></tr></thead><tbody>\n'
                  f'{rows}\n</tbody></table></div>')

    sources = ""
    if payload:
        rows = "\n".join(
            f'<tr class="src"><td>{escape(r["Source"])}</td><td class="text">{escape(r["Month_End_Input"])}</td>'
            f'<td class="text">{escape(r["Acquisition_Rule"])}</td>'
            f'<td class="text"><span class="state{"" if present else " absent"}">'
            f'{escape(r["Origin"] if present else r["When_Absent"])}</span>{"; " + escape(note) if note else ""}</td>'
            f'<td class="detail">{escape(r["What_We_Read"]) if present else ""}</td>'
            f'<td class="pick"><input type="file" class="src-file" multiple accept=".csv,.xlsx" '
            f'aria-label="Downloaded file for {escape(r["Source"])}"></td></tr>'
            for r, present, note in source_states(folder, payload))
        note_sources = ('The first three columns are Goodwill\'s own (their slide 38). "Sample file" is a synthetic file '
                        'we generated; "simulated API" is a file written by our simulator: Goodwill has no such API today, '
                        'and the simulator stands in for the Controller\'s download; '
                        '"not in this inbox" means no file of that source reached this run. A file chosen here is '
                        f'kept in out/uploads/{month}/ and the same close runs again with it; the engine recognizes '
                        'each file by its own name and layout, whichever source it was chosen beside.')
        sources = (f'<h2 class="sec">Goodwill\'s nine month-end sources, and what this run has for each{ast(note_sources)}</h2>'
                   f'<p class="byhand">{escape(BY_HAND)} Choose each downloaded file beside its source.</p>'
                   '<div class="card"><table><thead><tr><th>Source</th><th class="text">Month-end input</th>'
                   '<th class="text">Acquisition / rule</th>'
                   f'<th class="text">In this run</th><th class="text">What we read</th>'
                   f'<th class="pick">Choose the downloaded file</th></tr></thead><tbody>\n{rows}\n</tbody></table></div>'
                   f'<section class="card pickrun" id="pick" data-month="{month}"><div class="actions">'
                   '<button class="btn" id="pick-run" type="button">Add the chosen files and run the close again</button>'
                   '<button class="btn quiet" id="pick-clear" type="button" hidden>Remove the added files and run again</button>'
                   '</div><p id="pick-state" role="status"></p>'
                   '<p>Only .csv and .xlsx. A file whose name is already in the run is refused, not counted twice. '
                   'Nothing is posted.</p></section>' + PICK_SCRIPT)

    shipping = ""
    if shipping_rows:
        rows = "\n".join(
            f'<tr><td>{escape(r["Carrier"])}</td><td class="text">{escape(r["Figure From"])}</td>'
            f'<td>{money(cents(r["Charges"]))}</td><td>{money(cents(r["Refunds"]))}</td><td>{money(cents(r["Net"]))}</td>'
            f'<td>{escape(r["Lines"])}</td><td class="text">{escape(r["Journal Document"]) or "none: already in Business Central"}</td></tr>'
            for r in shipping_rows)
        total = sum(cents(r["Net"]) for r in shipping_rows)
        charged = sum(s.get("shipping_cents", 0) + s.get("handling_cents", 0) for s in payload.get("sources", {}).values())
        note_shipping = (f"Net shipping cost {money(total)}; shipping and handling charged to buyers this month "
                         f"{money(charged)}. Both lookups come from simulated APIs with layouts we made up. The carriers "
                         f"paid from the bank post to a placeholder expense account against G/L 10009; FedEx is read from "
                         f"the ledger, so nothing is posted for it. What entry Goodwill's workbook makes here is not known.")
        shipping = (f'<h2 class="sec">Shipping cost, from the two lookups on Goodwill\'s slide 38{ast(note_shipping)}</h2>'
                    '<div class="card"><table><thead><tr><th>Carrier</th><th class="text">Where the figure comes from</th>'
                    '<th>Charges</th><th>Refunds</th><th>Net</th><th>Lines</th><th class="text">Journal document</th>'
                    f'</tr></thead><tbody>\n{rows}\n</tbody></table></div>')

    jewelry = ""
    items = read_if_there(folder / "engine" / "jewelry.csv")
    if items:
        by = defaultdict(lambda: [0, 0])
        for r in items:
            by[r["supplier"] or "(no supplier: not in the lookup)"][0] += 1
            by[r["supplier"] or "(no supplier: not in the lookup)"][1] += int(r["amount_cents"])
        rows = "\n".join(f'<tr><td>{escape(s)}</td><td>{n}</td><td>{money(c)}</td></tr>' for s, (n, c) in sorted(by.items()))
        note_jewelry = ('From a simulated Jewelry Report and supplier lookup. "Supplier" is read as the store that '
                        'supplied the item. These sales are already in the marketplace reports: this table adds nothing '
                        'to revenue and changes no journal line.')
        jewelry = (f'<h2 class="sec">Jewelry sales by supplier{ast(note_jewelry)}</h2><div class="card"><table><thead><tr><th>Supplier</th>'
                   f'<th>Items</th><th>Sales</th></tr></thead><tbody>\n{rows}\n</tbody></table></div>')

    history = ""
    runs = read_if_there(folder / "runs.csv")
    if runs:
        head = "".join(f'<th class="text">{escape(c.replace("_", " "))}</th>' for c in runs[0])
        rows = "\n".join("<tr>" + "".join(f'<td class="text">{escape(v or "")}</td>' for v in r.values()) + "</tr>"
                         for r in runs[-5:])
        history = (f'<h2 class="sec">Run history (last {min(len(runs), 5)} of {len(runs)})</h2><div class="card"><table>'
                   f'<thead><tr>{head}</tr></thead><tbody>\n{rows}\n</tbody></table></div>')

    invoices = {line["Document No."] for line in t["ar_invoice"]}
    buttons = "".join(f'<a class="btn{"" if k in TO_IMPORT else " quiet"} dl" href="{month}/{k}_{month}.csv" download>{label} (CSV)</a>'
                      for k, label in FILES + (OPTIONAL if shipping_rows else []))
    export = (f'<section class="card export"><h2 class="sec">Export Files for Business Central</h2>'
              f'<div class="actions">{buttons}</div>'
              f'<p class="hint">Review the control totals and exceptions, then paste the General Journal and AR Invoice lines '
              f'into Business Central (their columns are in its order). The buttons only download files: nothing is posted.</p>'
              f'</section>')
    statuses = ('OPEN: money still in transit or not paid out yet, fully explained by the exceptions marked "open balance". '
                'INCOMPLETE: every cent is accounted for, but a payout paid for days no report covers; download that report '
                'and run the close again. UNEXPLAINED: money nobody has accounted for; resolve before posting. Positive '
                'amounts are debits. The owners are role names we chose, not Goodwill\'s.')
    label = f"{date.fromisoformat(month + '-01'):%B %Y}"
    about = notes([
        ("", '<p><strong>Synthetic sample data.</strong> No real Goodwill file has been read. Account, customer and document '
             'numbers are placeholders; only department 180 comes from Goodwill\'s own slide. These are export files in '
             'Business Central\'s column order; nothing here has been sent to a Business Central.</p>'),
        ("Statuses and Exceptions", f"<p>{statuses}</p>"),
        ("Shipping Cost", f"<p>{note_shipping}</p>" if note_shipping else ""),
        ("Cross-check", f"<p>{note_checks}</p>" if note_checks else ""),
        ("Month-End Sources", f"<p>{note_sources}</p>" if note_sources else ""),
        ("Jewelry", f"<p>{note_jewelry}</p>" if note_jewelry else "")])
    not_real = "Account numbers are placeholders; nothing has been sent to Business Central"
    body = (f'<header><h1>Month-End Close: {label}</h1><p>{len(t["general_journal"])} journal lines in {len(docs)} documents · '
            f'{len(invoices)} invoice(s)</p></header>'
            f'<p class="simnote"><strong>Synthetic sample data.</strong> <strong>Posting status: Not posted.</strong> '
            f'Export files only{ast(not_real)}</p>'
            f'<p class="summary{" alert" if alert else ""}">{escape(text)}</p>'
            f'{export}'
            f'<h2 class="sec">Reconciliation by Source{ast("What OPEN, INCOMPLETE and UNEXPLAINED mean is in the notes")}</h2>'
            f'<div class="card"><table class="tight"><thead><tr><th>Source</th><th>Path</th>'
            + "".join(f"<th>{c}</th>" for c in cols) + '<th class="status">Status</th></tr></thead><tbody>\n'
            f'{control_rows}\n</tbody></table></div>'
            f'<h2 class="sec">Exceptions to Work</h2><div class="card"><table><thead><tr><th>Kind</th><th>Source</th><th>Amount</th>'
            f'<th>Effect</th><th class="text">Detail</th><th class="text">Owner</th><th class="text">What to do</th></tr></thead><tbody>\n{exc_rows}\n</tbody></table></div>'
            f'{shipping}{checks}{sources}{jewelry}{history}'
            f'<div class="actions"><a class="btn quiet" href="index.html">All Months</a></div>{about}')
    return PAGE.substitute(title=f"Month-End Close {month}", css=CSS + CLOSE_CSS, body=body)


def build(month, src=SRC, dest=DEST):
    folder = Path(src) / month
    if not (folder / f"control_totals_{month}.csv").exists():
        raise SystemExit(f"no close files in {folder}; run reports.reconcile and reports.bc_export first")
    dest = Path(dest)
    (dest / month).mkdir(parents=True, exist_ok=True)
    for k, _ in FILES + OPTIONAL:
        if (folder / f"{k}_{month}.csv").exists():
            shutil.copyfile(folder / f"{k}_{month}.csv", dest / month / f"{k}_{month}.csv")
    page = dest / f"{month}.html"
    page.write_text(render(month, folder), encoding="utf-8")
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--month", required=True)
    args = ap.parse_args(argv)
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise SystemExit("--month must look like 2026-09")
    print(f"wrote {build(args.month)}")


if __name__ == "__main__":
    main()
