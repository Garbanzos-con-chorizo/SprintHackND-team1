"""Pluggable ingestion: any adapter that returns canonical rows plugs into the same pipeline."""
from ..dedupe import dedupe_bank, dedupe_payouts, dedupe_rows, dedupe_table
from .base import DataIngestAdapter, NormalizedBatch
from .email_adapter import EmailAttachmentAdapter
from .scraper_adapter import MockScraperAdapter

__all__ = ["DataIngestAdapter", "NormalizedBatch", "EmailAttachmentAdapter", "MockScraperAdapter", "ingest"]


def ingest(adapters: list[DataIngestAdapter], business_date: str | None = None) -> NormalizedBatch:
    """Run every adapter, merge their rows, and count a transaction that arrived twice (from the
    same or different adapters) once. Duplicates dropped are listed in the warnings."""
    merged = NormalizedBatch()
    for adapter in adapters:
        merged.extend(adapter.fetch_and_normalize(business_date))
    merged.rows, duplicate_warnings = dedupe_rows(merged.rows)
    merged.warnings.extend(duplicate_warnings)
    merged.payouts, duplicate_warnings = dedupe_payouts(merged.payouts)
    merged.warnings.extend(duplicate_warnings)
    merged.bank, duplicate_warnings = dedupe_bank(merged.bank)
    merged.warnings.extend(duplicate_warnings)
    for name in list(merged.tables):
        merged.tables[name], duplicate_warnings = dedupe_table(name, merged.tables[name])
        merged.warnings.extend(duplicate_warnings)
    return merged
