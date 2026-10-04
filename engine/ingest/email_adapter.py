"""Primary adapter: files that arrive by email attachment, manual export or ERP drop.

Staff save the attachment (or the export, or the ERP's file) into the inbox folder; this adapter reads
everything there. Supported extensions: .csv .tsv .txt .xlsx. Old Excel (.xls) is not supported and is
reported as a warning, not skipped silently.
"""
from pathlib import Path

from ..coverage import read_manifest
from ..parsers import Ambiguous, NoMatch, Parser, detect_source, load_sources
from ..table import SUPPORTED_SUFFIXES, UnreadableFile, read_table
from .base import DataIngestAdapter, NormalizedBatch

_ATTACHMENT_LIKE = SUPPORTED_SUFFIXES | {".xls", ".xlsm"}  # recognized as data files, even if we can't read all


def _file_warning(name: str, kind: str, reason: str) -> dict:
    return {"source_file": name, "source_row": 0, "kind": kind, "reason": reason}


class EmailAttachmentAdapter(DataIngestAdapter):
    name = "inbox"

    def __init__(self, inbox: Path, parsers: list[Parser] | None = None):
        self.inbox = Path(inbox)
        self.parsers = parsers

    def files(self) -> list[Path]:
        if not self.inbox.is_dir():
            return []
        return sorted(
            p for p in self.inbox.rglob("*")
            if p.is_file() and p.suffix.lower() in _ATTACHMENT_LIKE
            and not p.name.startswith(("~$", "."))  # Excel lock files, hidden files
        )

    def fetch_and_normalize(self, business_date: str | None = None) -> NormalizedBatch:
        parsers = load_sources() if self.parsers is None else self.parsers
        batch = NormalizedBatch()
        simulated = read_manifest(self.inbox)
        for path in self.files():
            try:
                table = read_table(path)
                parser = detect_source(table, parsers)
            except (UnreadableFile, NoMatch, Ambiguous) as exc:
                batch.warnings.append(_file_warning(path.name, "unparseable", str(exc)))
                continue
            batch.add_result({"file": path.name, "source": parser.source, "feeds": list(parser.feeds),
                              "simulated": path.name in simulated, "daily": parser.daily}, parser.parse(table))
        return batch
