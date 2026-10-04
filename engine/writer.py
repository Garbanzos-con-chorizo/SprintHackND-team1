"""Writes the three output files defined in docs/contracts/transaction.md."""
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .contract import BANK_COLUMNS, COLUMNS, PAYOUT_COLUMNS, TIMEZONE


def now_local() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE)).replace(microsecond=0)


def write_outputs(out_dir: Path, rows: list[dict], source_status: dict, warnings: list[dict],
                  payouts: list[dict] = (), bank: list[dict] = ()) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # transactions.csv (transaction.md), then the close inputs (close-inputs.md), written even when empty.
    for name, columns, items in (("transactions.csv", COLUMNS, rows), ("payouts.csv", PAYOUT_COLUMNS, payouts),
                                 ("bank.csv", BANK_COLUMNS, bank)):
        with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(items)

    with open(out_dir / "source_status.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(source_status, f, indent=2)
        f.write("\n")

    with open(out_dir / "warnings.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(warnings, f, indent=2)
        f.write("\n")
