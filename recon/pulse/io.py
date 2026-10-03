"""Read the engine's output files (docs/contracts/transaction.md) and write the pulse files."""
import csv
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

MARKETPLACES = ("shopgoodwill", "amazon", "ebay", "other")
TYPES = ("sale", "refund")
BASES = ("buyer", "order")


@dataclass(frozen=True)
class Transaction:
    txn_id: str
    source: str
    marketplace: str
    type: str
    business_date: str
    order_id: str
    customer_id: str
    customer_basis: str
    gross_cents: int
    fee_cents: int


def load_transactions(path):
    """Rows of transactions.csv. Unknown columns are ignored, as the contract allows.

    The engine dedupes on txn_id; a repeated txn_id here is dropped (first wins)
    so an engine slip can't double count. Returns (rows, dropped_count).
    """
    rows, seen, dropped = [], set(), 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for line, raw in enumerate(csv.DictReader(f), start=2):
            try:
                row = Transaction(
                    txn_id=raw["txn_id"],
                    source=raw["source"],
                    marketplace=raw["marketplace"],
                    type=raw["type"],
                    business_date=raw["business_date"],
                    order_id=raw["order_id"],
                    customer_id=raw["customer_id"] or "",
                    customer_basis=raw["customer_basis"],
                    gross_cents=int(raw["gross_cents"]),
                    fee_cents=int(raw["fee_cents"]),
                )
            except (KeyError, TypeError, ValueError) as e:
                raise ValueError(f"{path} line {line}: not to contract ({e!r})") from e
            if row.marketplace not in MARKETPLACES or row.type not in TYPES or row.customer_basis not in BASES:
                raise ValueError(f"{path} line {line}: enum value not in contract")
            if row.txn_id in seen:
                dropped += 1
                continue
            seen.add(row.txn_id)
            rows.append(row)
    return rows, dropped


def _load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_source_status(path):
    """source_status.json as a dict, or None if the file is absent."""
    return _load_json(path)


def load_warnings(path):
    """warnings.json as a list, or None if the file is absent."""
    return _load_json(path)


def load_pulse(path):
    """A pulse file written earlier, or None if the file is absent."""
    return _load_json(path)


def write_pulse(out_dir, pulse):
    """Write <out_dir>/<business_date>.json and refresh latest.json. Returns the dated path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{pulse['business_date']}.json"
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pulse, f, indent=2)
        f.write("\n")
    dated = [p for p in out_dir.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)]
    shutil.copyfile(max(dated, key=lambda p: p.stem), out_dir / "latest.json")
    return target
