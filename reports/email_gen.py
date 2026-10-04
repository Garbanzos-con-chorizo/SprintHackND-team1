"""Email distributor: one .eml per active subscriber for each report produced in a run.

Reads reports/config/subscribers.csv (Name, Email, Report_Type = Daily | Weekly | Monthly | Close,
Status = Active | Inactive) and writes out/outbox/<run date>/<type>-<recipient>.eml plus a
manifest.csv. Nothing is sent: each .eml opens in Outlook as an unsent message (X-Unsent), and
sending automatically needs an SMTP account from Goodwill IT. Bad rows are listed, not fatal.

    python -m reports.email_gen --run-date 2026-10-05 --daily 2026-10-04 [--weekly 2026-W40] [--monthly 2026-09]
                                [--close 2026-09]
"""
import argparse
import csv
import json
import mimetypes
import re
from datetime import date, datetime
from email.message import EmailMessage
from email.utils import format_datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from reports.hub import headline
from reports.pulse import E, EMAIL_FONT, long_date

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
SUBSCRIBERS = REPORTS / "config" / "subscribers.csv"
OUTBOX = ROOT / "out" / "outbox"
SENDER = "Goodwill Michiana E-commerce Reports <ecommerce-reports@example.org>"
TYPES = ("Daily", "Weekly", "Monthly", "Close")
# Fixed types for what we attach: mimetypes reads the Windows registry, where Excel maps .csv to
# application/vnd.ms-excel, so the same email would differ from one PC to the next.
CONTENT_TYPES = {".pdf": "application/pdf", ".csv": "text/csv", ".json": "application/json",
                 ".html": "text/html"}
SEND_TIME = (6, 0)  # Eastern; reports are built after midnight, mail goes out before the workday


def load_subscribers(path=SUBSCRIBERS):
    """Active subscribers and a list of rows that could not be used."""
    active, problems = [], []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            kind, status = row.get("Report_Type", "").title(), row.get("Status", "").title()
            if kind not in TYPES:
                problems.append(f"row {n}: Report_Type '{row.get('Report_Type')}' is not Daily, Weekly, Monthly or Close")
            elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", row.get("Email", "")):
                problems.append(f"row {n}: '{row.get('Email')}' is not an email address")
            elif status not in ("Active", "Inactive"):
                problems.append(f"row {n}: Status '{row.get('Status')}' is not Active or Inactive")
            elif status == "Active":
                active.append({"name": row.get("Name") or row["Email"], "email": row["Email"], "type": kind})
    return active, problems


def _fmt(value, unit):
    if value == "":
        return "n/a"
    v = float(value)
    if unit == "USD":
        return f"{'-' if v < 0 else ''}${abs(v):,.2f}"
    if unit == "ratio":
        return f"{v * 100:.1f}%"
    return f"{int(v):,}" if unit == "count" else f"{v:,.1f}"


def _scorecard_body(title, period, text, kpi_file, attached="The full scorecard page and its KPI file are attached."):
    """The 15 KPIs as an inline-styled table; simulated ones say so, no-data ones say so."""
    from reports.scorecard import fmt
    kf = json.loads(Path(kpi_file).read_text(encoding="utf-8"))
    sim_label = (kf.get("internal_data") or {}).get("label") or "Simulated internal data"
    td = f'style="{EMAIL_FONT}font-size:13px;color:{E["ink"]};padding:5px 10px;border-bottom:1px solid {E["line"]};"'
    tdr = td.replace("padding", "text-align:right;padding")
    rows = []
    for k in kf["kpis"]:
        if k["kind"] == "ranking":
            shown = ", ".join(r["label"] for r in (k["rows"] or [])[:3]) or "No data"
        else:
            shown = fmt(k["value"], k["unit"]) or "No data"
            if k.get("per") and k["value"] is not None:
                shown += f" per {k['per']}"
        flag = f' <span style="color:{E["muted"]};font-size:11px;">({sim_label.lower()})</span>' if k["simulated"] else ""
        rows.append(f'<tr><td {td}>{escape(k["name"])}{flag}</td><td {tdr}>{escape(shown)}</td></tr>')
    return f"""<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:100%;">
<tr><td style="{EMAIL_FONT}background:{E['primary']};color:#ffffff;padding:16px 20px;">
  <div style="font-size:20px;font-weight:bold;">{escape(title)}</div>
  <div style="font-size:12px;">{escape(period)}</div></td></tr>
<tr><td style="{EMAIL_FONT}font-size:16px;font-weight:bold;color:{E['ink']};border-left:5px solid {E['primary']};padding:12px 14px;">{escape(text)}</td></tr>
<tr><td style="padding-top:8px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
{chr(10).join(rows)}
</table></td></tr>
<tr><td style="{EMAIL_FONT}font-size:12px;color:{E['muted']};padding:12px 2px;">{escape(attached)}</td></tr>
</table>"""


CLOSE_FILES = ("general_journal", "ar_invoice", "control_totals", "exceptions")  # the four CSVs of the close


def _close_body(period, text, control, exceptions):
    """The month-end close for accounting: what it is (import files, not posted), each source's status and
    open balance, and the exceptions by kind. The numbers come from the close's own CSVs."""
    td = f'style="{EMAIL_FONT}font-size:13px;color:{E["ink"]};padding:5px 10px;border-bottom:1px solid {E["line"]};"'
    tdr = td.replace("padding", "text-align:right;padding")
    th = td.replace(f'color:{E["ink"]}', f'color:{E["muted"]}')
    money = lambda t: f"{'-' if float(t) < 0 else ''}${abs(float(t)):,.2f}"  # noqa: E731
    sources = "".join(f'<tr><td {td}>{escape(r["Source"])}</td><td {td}>{escape(r["Status"])}</td>'
                      f'<td {tdr}>{money(r["Open Balance"])}</td><td {tdr}>{money(r["Unexplained"])}</td></tr>'
                      for r in control)
    kinds = {}
    for e in exceptions:
        kinds[e["Kind"]] = kinds.get(e["Kind"], 0) + 1
    listed = ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in sorted(kinds.items())) or "none"
    note = (f'<strong>Not posted.</strong> The attached files are import files in Business Central\'s column order: '
            f'nothing has been posted. <strong>Synthetic sample data</strong>, placeholder account numbers.')
    return f"""<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:100%;">
<tr><td style="{EMAIL_FONT}background:{E['primary']};color:#ffffff;padding:16px 20px;">
  <div style="font-size:20px;font-weight:bold;">Month-end close</div>
  <div style="font-size:12px;">{escape(period)}</div></td></tr>
<tr><td style="{EMAIL_FONT}font-size:13px;color:{E['ink']};padding:10px 2px;">{note}</td></tr>
<tr><td style="{EMAIL_FONT}font-size:16px;font-weight:bold;color:{E['ink']};border-left:5px solid {E['primary']};padding:12px 14px;">{escape(text)}</td></tr>
<tr><td style="padding-top:8px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td {th}>Source</td><td {th}>Status</td><td {th.replace("padding", "text-align:right;padding")}>Open balance</td><td {th.replace("padding", "text-align:right;padding")}>Unexplained</td></tr>
{sources}
</table></td></tr>
<tr><td style="{EMAIL_FONT}font-size:13px;color:{E['ink']};padding:12px 2px;">{len(exceptions)} exceptions to review: {escape(listed)}. Each has an owner and an action in the attached exceptions file.</td></tr>
<tr><td style="{EMAIL_FONT}font-size:12px;color:{E['muted']};padding:4px 2px 12px;">Attached: the close page, the General Journal and sales invoice import files, the control totals and the exceptions.</td></tr>
</table>"""


def _close_payload(key, root):
    page, folder = root / "close" / f"{key}.html", root / "close" / key
    files = [folder / f"{name}_{key}.csv" for name in CLOSE_FILES]
    if not (page.exists() and all(f.exists() for f in files)):
        return None
    text, _ = headline(page)
    period = f"{date.fromisoformat(key + '-01'):%B %Y}"
    read = lambda f: list(csv.DictReader(f.read_text(encoding="utf-8-sig").splitlines()))  # noqa: E731
    return {"subject": f"Month-end close - {period} - not posted - {text.split(';')[1].strip() if ';' in text else text}",
            "text": f"{text} Not posted: the attached files are import files. Synthetic sample data.",
            "html": _close_body(period, text, read(files[2]), read(files[3])), "attachments": [page] + files}


def payload(kind, key, root=REPORTS):
    """Subject, HTML body and attachments for one report, or None if that report wasn't built."""
    if kind == "Close":
        return _close_payload(key, root)
    if kind == "Daily":
        page, mail = root / "pulse" / f"{key}.html", root / "pulse" / f"{key}.email.html"
        if not (page.exists() and mail.exists()):
            return None
        text, _ = headline(page)
        body = re.search(r"<body[^>]*>(.*)</body>", mail.read_text(encoding="utf-8"), re.S)[1]
        return {"subject": f"Nightly pulse - {long_date(key)} - {text.split(';')[0]}",
                "text": text, "html": body, "attachments": [root / "pulse" / f"{key}.csv"]}
    stem, period = (f"week-{key}", key) if kind == "Weekly" else (f"month-{key}", f"{date.fromisoformat(key + '-01'):%B %Y}")
    page, kfile = root / "scorecard" / f"{stem}.html", root / "scorecard" / f"{stem}.json"
    if not (page.exists() and kfile.exists()):
        return None
    text, _ = headline(page)
    title = "Weekly dashboard" if kind == "Weekly" else "COO scorecard"
    # The one-page PDF and the CSV for Excel (python -m engine.export) go first when they were built.
    exports = [p for p in (page.with_suffix(".pdf"), page.with_suffix(".csv")) if p.exists()]
    attached = ("Attached: the scorecard as a one-page PDF" if page.with_suffix(".pdf").exists() else "Attached: the scorecard page")
    attached += (", its numbers as a CSV for Excel" if page.with_suffix(".csv").exists() else "") + ", the full page and its KPI file."
    return {"subject": f"{title} - {period} - {text.split(';')[0]}", "text": text,
            "html": _scorecard_body(title, period, text, kfile, attached), "attachments": exports + [page, kfile]}


def message(sub, report, sent):
    msg = EmailMessage()
    msg["From"] = SENDER
    msg["To"] = f'"{sub["name"]}" <{sub["email"]}>'
    msg["Subject"] = report["subject"]
    msg["Date"] = format_datetime(sent)
    msg["X-Unsent"] = "1"  # Outlook opens it as a draft ready to send
    for_line = f"For {sub['name']} - {sub['type']} subscription"
    msg.set_content(f"{for_line}\n\n{report['text']}\n\nThe full report is attached.\n")
    msg.add_alternative(
        f'<!doctype html><html><body style="margin:0;padding:16px;background:#ffffff;">'
        f'<div style="{EMAIL_FONT}font-size:12px;color:{E["muted"]};padding:0 0 8px;">{escape(for_line)}</div>'
        f'{report["html"]}</body></html>', subtype="html")
    for path in report["attachments"]:
        ctype = CONTENT_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        maintype, subtype = ctype.split("/")
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return msg


def distribute(run_date, daily=None, weekly=None, monthly=None, subscribers=SUBSCRIBERS, outbox=OUTBOX, close=None,
               root=REPORTS):
    """Write the run's emails; return (written rows, problems)."""
    keys = {"Daily": daily, "Weekly": weekly, "Monthly": monthly, "Close": close}
    reports = {k: payload(k, v, root) for k, v in keys.items() if v}
    active, problems = load_subscribers(subscribers)
    for k, v in keys.items():
        if v and reports.get(k) is None:
            problems.append(f"{k} report {v} not found; its subscribers get nothing")
    folder = Path(outbox) / run_date.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    sent = datetime(run_date.year, run_date.month, run_date.day, *SEND_TIME, tzinfo=ZoneInfo("America/New_York"))
    written = []
    for sub in active:
        report = reports.get(sub["type"])
        if not report:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", sub["email"].lower()).strip("-")
        path = folder / f"{sub['type'].lower()}-{slug}.eml"
        path.write_bytes(bytes(message(sub, report, sent)))
        written.append({"Run_Date": run_date.isoformat(), "Report_Type": sub["type"], "Name": sub["name"],
                        "Email": sub["email"], "Subject": report["subject"], "File": path.name,
                        "Attachments": "; ".join(p.name for p in report["attachments"])})
    with open(folder / "manifest.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Run_Date", "Report_Type", "Name", "Email", "Subject", "File", "Attachments"])
        w.writeheader()
        w.writerows(written)
    return written, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-date", type=date.fromisoformat, default=date.today(), help="date the mail goes out")
    ap.add_argument("--daily", help="business date of the nightly pulse, YYYY-MM-DD")
    ap.add_argument("--weekly", help="ISO week, e.g. 2026-W40")
    ap.add_argument("--monthly", help="month, e.g. 2026-09")
    ap.add_argument("--close", help="month of the month-end close, e.g. 2026-09")
    args = ap.parse_args(argv)
    written, problems = distribute(args.run_date, args.daily, args.weekly, args.monthly, close=args.close)
    for row in written:
        print(f"{row['Report_Type']:<8} {row['Email']:<34} {row['File']}")
    for p in problems:
        print(f"skipped: {p}")
    print(f"{len(written)} email(s) in {OUTBOX / args.run_date.isoformat()} (not sent; open the .eml in Outlook)")


if __name__ == "__main__":
    main()
