"""The one interface every way of getting data into the engine implements.

An adapter's whole job: get raw data from somewhere (a folder of emailed files, a scraper, an ERP
drop) and return rows in the canonical transaction format (docs/contracts/transaction.md). The
messy part (reading, detecting the source, cleaning) is shared, so a new adapter is small.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..coverage import summarize


@dataclass
class NormalizedBatch:
    rows: list[dict] = field(default_factory=list)       # canonical rows, engine.contract.COLUMNS
    warnings: list[dict] = field(default_factory=list)   # contract warnings (bad rows, unreadable files)
    # One entry per file that was read and recognized: {"file", "source", "feeds": [marketplaces]}.
    # Used to tell a marketplace with no file (missing) from one whose file had nothing for the day (stale).
    files: list[dict] = field(default_factory=list)
    # Close inputs (docs/contracts/close-inputs.md): payouts the marketplaces report, and bank lines.
    payouts: list[dict] = field(default_factory=list)
    bank: list[dict] = field(default_factory=list)
    tables: dict[str, list[dict]] = field(default_factory=dict)  # ledger, statements, ...: CLOSE_TABLES

    def _extend_tables(self, tables: dict[str, list[dict]]) -> None:
        for name, items in tables.items():
            self.tables.setdefault(name, []).extend(items)

    def extend(self, other: "NormalizedBatch") -> None:
        self.rows.extend(other.rows)
        self.warnings.extend(other.warnings)
        self.files.extend(other.files)
        self.payouts.extend(other.payouts)
        self.bank.extend(other.bank)
        self._extend_tables(other.tables)

    def add_result(self, file: dict, result) -> None:
        """Take in what a parser returned for one file (a ParseResult)."""
        self.files.append(summarize(file, result))
        self.rows.extend(result.rows)
        self.warnings.extend(result.warnings)
        self.payouts.extend(result.payouts)
        self.bank.extend(result.bank)
        self._extend_tables(result.tables)


class DataIngestAdapter(ABC):
    name: str = ""  # shown in logs

    @abstractmethod
    def fetch_and_normalize(self, business_date: str | None = None) -> NormalizedBatch:
        """Get the data and return it normalized. Must not raise for bad data: put it in warnings.

        `business_date` (YYYY-MM-DD) is a hint for adapters that fetch per day (scrapers); adapters
        that read whatever is already on disk ignore it.
        """
