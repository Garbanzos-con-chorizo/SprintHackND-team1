"""The one interface every way of getting data into the engine implements.

An adapter's whole job: get raw data from somewhere (a folder of emailed files, a scraper, an ERP
drop) and return rows in the canonical transaction format (docs/contracts/transaction.md). The
messy part (reading, detecting the source, cleaning) is shared, so a new adapter is small.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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

    def extend(self, other: "NormalizedBatch") -> None:
        self.rows.extend(other.rows)
        self.warnings.extend(other.warnings)
        self.files.extend(other.files)
        self.payouts.extend(other.payouts)
        self.bank.extend(other.bank)

    def add_result(self, file: dict, result) -> None:
        """Take in what a parser returned for one file (a ParseResult)."""
        self.files.append(file)
        self.rows.extend(result.rows)
        self.warnings.extend(result.warnings)
        self.payouts.extend(result.payouts)
        self.bank.extend(result.bank)


class DataIngestAdapter(ABC):
    name: str = ""  # shown in logs

    @abstractmethod
    def fetch_and_normalize(self, business_date: str | None = None) -> NormalizedBatch:
        """Get the data and return it normalized. Must not raise for bad data: put it in warnings.

        `business_date` (YYYY-MM-DD) is a hint for adapters that fetch per day (scrapers); adapters
        that read whatever is already on disk ignore it.
        """
