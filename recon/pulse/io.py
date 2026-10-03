"""Read the engine's output files (docs/contracts/transaction.md)."""
import csv
import json
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
