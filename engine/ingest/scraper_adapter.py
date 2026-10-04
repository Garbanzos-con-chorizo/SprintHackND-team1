"""Demo adapter: shows a web scraper plugging into the same normalization as the file inbox.

A real scraper (see engine/scrapers/) logs in and downloads a report file. This stub skips the
network: it is handed the records a scraper would have extracted from a page (a list of dicts keyed by
the column names shown on the page) and runs them through the SAME source parser and cleaning as a
dropped file. That is the whole point of the demo: the scraper only has to produce records; nothing
downstream knows or cares where they came from.

Assumptions (stubbed): the payload comes from a synthetic fixture or is passed in directly, not from a
live site; its keys are the same column names the source's export uses; no login, retries or paging.
"""
import json
from pathlib import Path

from ..parsers import Parser, load_sources
from ..table import Table
from .base import DataIngestAdapter, NormalizedBatch


def table_from_records(name: str, records: list[dict]) -> Table:
    header: list[str] = []
    for rec in records:
        for key in rec:
            if key not in header:
                header.append(key)
    rows = [(i, {h: rec.get(h, "") for h in header}) for i, rec in enumerate(records, start=1)]
    return Table(name=name, header=header, rows=rows)


class MockScraperAdapter(DataIngestAdapter):
    def __init__(self, source: str, payload: list[dict] | Path | str, parsers: list[Parser] | None = None):
        """`source` is the engine source name (e.g. 'ebay'); `payload` is records or a path to a JSON file."""
        self.source = source
        self.name = f"mock-scraper:{source}"
        self.payload = payload
        self.parsers = parsers

    def _records(self) -> tuple[str, list[dict]]:
        if isinstance(self.payload, (str, Path)):
            path = Path(self.payload)
            return path.name, json.loads(path.read_text(encoding="utf-8"))
        return f"{self.source}_scrape.json", self.payload

    def fetch_and_normalize(self, business_date: str | None = None) -> NormalizedBatch:
        parsers = load_sources() if self.parsers is None else self.parsers
        parser = next((p for p in parsers if p.source == self.source), None)
        batch = NormalizedBatch()
        name, records = self._records()
        if parser is None:
            batch.warnings.append({"source_file": name, "source_row": 0, "kind": "unparseable",
                                   "reason": f"no parser registered for source {self.source!r}"})
            return batch
        if not records:
            return batch
        batch.add_result({"file": name, "source": parser.source, "feeds": list(parser.feeds)},
                         parser.parse(table_from_records(name, records)))
        return batch
