"""export kpi-csv (V2.8): a KPI file (docs/contracts/kpi.md) as one long CSV for Excel and Power BI.

One row per KPI, and one row per category for the two top-10 rankings, so a pivot table or a
Power BI visual needs no reshaping. It renders the KPI file and computes nothing, so the CSV can
never disagree with the page or the PDF. Money is in dollars; a value with no data is blank,
never 0, so sums in a spreadsheet stay honest. Every simulated number says so in its row.
"""
import csv
import json
from pathlib import Path

COLUMNS = ["Period type", "Period", "Period label", "Start", "Through", "Complete", "Area", "Pillar",
           "KPI id", "KPI", "Rank", "Category", "Value", "Unit", "Per", "Display", "Share", "Category margin",
           "Status", "Note", "Prior value", "Change", "Change %", "Change note", "Source", "Simulated",
           "Definition"]
UNIT_LABEL = {"cents": "USD", "ratio": "ratio", "count": "count", "number": "number", "days": "days"}


def kpi_rows(kpi_file: dict) -> list[dict]:
    period = kpi_file["period"]
    areas = {a["id"]: a["name"] for a in kpi_file.get("areas", [])}
    pillars = {p["id"]: p["name"] for p in kpi_file.get("pillars", [])}
    label = (kpi_file.get("internal_data") or {}).get("label") or "Simulated internal data"
    rows = []
    for k in kpi_file["kpis"]:
        unit = k["unit"]
        delta = k.get("delta") or {}
        base = {
            "Period type": period["type"], "Period": period["id"], "Period label": period["label"],
            "Start": period["start"], "Through": period["through"], "Complete": flag(period["complete"]),
            "Area": areas.get(k["area"], k["area"]), "Pillar": pillars.get(k.get("pillar"), k.get("pillar") or ""),
            "KPI id": k["id"], "KPI": k["name"], "Unit": UNIT_LABEL.get(unit, unit), "Per": k.get("per") or "",
            "Status": k["status"], "Note": k.get("note") or "",
            "Prior value": number(k.get("prior_value"), unit), "Change": number(delta.get("value"), unit),
            "Change %": blank(delta.get("pct")), "Change note": delta.get("reason") or "",
            "Source": k["source"], "Simulated": label if k.get("simulated") else "",
            "Definition": k.get("definition") or "",
        }
        if k.get("kind") == "ranking":
            for r in k.get("rows") or []:
                rows.append({**base, "Rank": r["rank"], "Category": r["label"], "Value": number(r["value"], unit),
                             "Display": display(r["value"], unit, None), "Share": blank(r.get("share")),
                             "Category margin": blank(r.get("ratio")), "Prior value": "", "Change": ""})
            if not k.get("rows"):  # a ranking with no data still gets its row, with the reason
                rows.append({**base, "Display": "no data"})
        else:
            rows.append({**base, "Value": number(k.get("value"), unit),
                         "Display": display(k.get("value"), unit, k.get("per"))})
    return rows


def write_kpi_csv(kpi_path: Path, dest: Path) -> Path:
    """Write <dest>/<type>-<id>.csv (next to the scorecard page of the same name) and return its path."""
    kpi_file = json.loads(Path(kpi_path).read_text(encoding="utf-8"))
    period = kpi_file["period"]
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"{period['type']}-{period['id']}.csv"
    with open(target, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
        w.writeheader()
        w.writerows(kpi_rows(kpi_file))
    return target


def number(value, unit):
    """Value in the CSV's unit: cents become dollars; blank when there is no value."""
    if value is None:
        return ""
    return round(value / 100, 2) if unit == "cents" else value


def display(value, unit, per):
    """The number as the page prints it, for people who open the CSV without formatting it."""
    if value is None:
        return "no data"
    text = {"cents": lambda v: f"${v / 100:,.2f}", "ratio": lambda v: f"{v * 100:.1f}%",
            "count": lambda v: f"{v:,.0f}", "days": lambda v: f"{v:.1f} days"}.get(unit, lambda v: f"{v:,.1f}")(value)
    return f"{text} per {per}" if per else text


def blank(value):
    return "" if value is None else value


def flag(value):
    return "TRUE" if value else "FALSE"
