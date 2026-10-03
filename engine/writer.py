"""Writes the three output files defined in docs/contracts/transaction.md."""
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .contract import COLUMNS, TIMEZONE


def now_local() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE)).replace(microsecond=0)


def write_outputs(out_dir: Path, rows: list[dict], source_status: dict, warnings: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "transactions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    with open(out_dir / "source_status.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(source_status, f, indent=2)
        f.write("\n")

    with open(out_dir / "warnings.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(warnings, f, indent=2)
        f.write("\n")
