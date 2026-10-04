"""Email distributor: one .eml per active subscriber for each report produced in a run.

Reads reports/config/subscribers.csv (Name, Email, Report_Type = Daily | Weekly | Monthly,
Status = Active | Inactive) and writes out/outbox/<run date>/<type>-<recipient>.eml plus a
manifest.csv. Nothing is sent: each .eml opens in Outlook as an unsent message (X-Unsent), and
sending automatically needs an SMTP account from Goodwill IT. Bad rows are listed, not fatal.

    python -m reports.email_gen --run-date 2026-10-05 --daily 2026-10-04 [--weekly 2026-W40] [--monthly 2026-09]
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
TYPES = ("Daily", "Weekly", "Monthly")
SEND_TIME = (6, 0)  # Eastern; reports are built after midnight, mail goes out before the workday


def load_subscribers(path=SUBSCRIBERS):
    """Active subscribers and a list of rows that could not be used."""
    active, problems = [], []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            kind, status = row.get("Report_Type", "").title(), row.get("Status", "").title()
            if kind not in TYPES:
                problems.append(f"row {n}: Report_Type '{row.get('Report_Type')}' is not Daily, Weekly or Monthly")
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


def _kpi_body(title, period, text, kpi_csv, attachments_note):
    """Inline-styled table email (Outlook renders with Word: tables, inline styles, hex colors)."""
    rows = [r for r in csv.DictReader(open(kpi_csv, encoding="utf-8"))
            if r["Source"] == "Marketplace files" and r["Section"] != "Category Effectiveness"]
    td = f'style="{EMAIL_FONT}font-size:14px;color:{E["ink"]};padding:6px 10px;border-bottom:1px solid {E["line"]};"'
    tdr = td.replace('padding', 'text-align:right;padding')
    lines = "\n".join(
        f'<tr><td {td}>{escape(r["KPI"])}{"" if r["Marketplace"] == "All" else " - " + escape(r["Marketplace"])}</td>'
        f'<td {tdr}>{_fmt(r["Value"], r["Unit"])}</td></tr>'
        for r in rows if r["KPI"] != "Days with data")
    return f"""<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:100%;">
<tr><td style="{EMAIL_FONT}background:{E['primary']};color:#ffffff;padding:16px 20px;">
  <div style="font-size:20px;font-weight:bold;">{escape(title)}</div>
  <div style="font-size:12px;">{escape(period)}</div></td></tr>
<tr><td style="{EMAIL_FONT}font-size:16px;font-weight:bold;color:{E['ink']};border-left:5px solid {E['primary']};padding:12px 14px;">{escape(text)}</td></tr>
<tr><td style="padding-top:8px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
{lines}
</table></td></tr>
<tr><td style="{EMAIL_FONT}font-size:12px;color:{E['muted']};padding:12px 2px;">{escape(attachments_note)}</td></tr>
</table>"""


def _scorecard_body(title, period, text, kpi_file):
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
<tr><td style="{EMAIL_FONT}font-size:12px;color:{E['muted']};padding:12px 2px;">The full scorecard page and its KPI file are attached.</td></tr>
</table>"""


def payload(kind, key, root=REPORTS):
    """Subject, HTML body and attachments for one report, or None if that report wasn't built."""
    if kind == "Daily":
        page, mail = root / "pulse" / f"{key}.html", root / "pulse" / f"{key}.email.html"
        if not (page.exists() and mail.exists()):
            return None
        text, _ = headline(page)
        body = re.search(r"<body[^>]*>(.*)</body>", mail.read_text(encoding="utf-8"), re.S)[1]
        return {"subject": f"Nightly pulse - {long_date(key)} - {text.split(';')[0]}",
                "text": text, "html": body, "attachments": [root / "pulse" / f"{key}.csv"]}
    if kind == "Monthly":
        page, kfile = root / "scorecard" / f"month-{key}.html", root / "scorecard" / f"month-{key}.json"
        if not (page.exists() and kfile.exists()):
            return None
        text, _ = headline(page)
        title, period = "COO scorecard", f"{date.fromisoformat(key + '-01'):%B %Y}"
        return {"subject": f"{title} - {period} - {text.split(';')[0]}", "text": text,
                "html": _scorecard_body(title, period, text, kfile), "attachments": [page, kfile]}
    page, kcsv = root / "weekly" / f"{key}.html", root / "weekly" / f"{key}.csv"
    title, period = "Weekly dashboard", key
    if not (page.exists() and kcsv.exists()):
        return None
    text, _ = headline(page)
    note = ("KPIs calculated from the marketplace exports. The attached report also has the KPIs that use "
            "simulated internal data (labor, listings, cost of goods, categories), marked SIMULATED.")
    return {"subject": f"{title} - {period} - {text.split(';')[0]}", "text": text,
            "html": _kpi_body(title, period, text, kcsv, note), "attachments": [page, kcsv]}


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
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        maintype, subtype = ctype.split("/")
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return msg


def distribute(run_date, daily=None, weekly=None, monthly=None, subscribers=SUBSCRIBERS, outbox=OUTBOX):
    """Write the run's emails; return (written rows, problems)."""
    keys = {"Daily": daily, "Weekly": weekly, "Monthly": monthly}
    reports = {k: payload(k, v) for k, v in keys.items() if v}
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
    args = ap.parse_args(argv)
    written, problems = distribute(args.run_date, args.daily, args.weekly, args.monthly)
    for row in written:
        print(f"{row['Report_Type']:<8} {row['Email']:<34} {row['File']}")
    for p in problems:
        print(f"skipped: {p}")
    print(f"{len(written)} email(s) in {OUTBOX / args.run_date.isoformat()} (not sent; open the .eml in Outlook)")


if __name__ == "__main__":
    main()
