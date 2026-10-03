"""Parser interface, registry and source detection.

To add a new source of input, drop one module in engine/sources/ with a Parser subclass
decorated with @register. Nothing else changes: it is discovered automatically, detected by
its filename pattern and/or required columns, and its `source` / `marketplace` values flow into
the output files. Example (see engine/tests/test_detection.py for a working one):

    @register
    class CashMonkey(Parser):
        source = "cashmonkey"
        marketplace = "other"
        filename_patterns = (r"cash.?monkey",)
        required_columns = ("transaction id", "amount", "date")

        def parse(self, table):
            result = ParseResult()
            for row_no, row in table.rows:
                ...  # build a contract row (engine.contract.COLUMNS) and result.add(...)
            return result

A new `source` value also needs a line in docs/contracts/transaction.md (the enum) and, if the
pulse should expect a file from it every day, in EXPECTED_SOURCES in engine/contract.py.
"""
import importlib
import pkgutil
import re
from dataclasses import dataclass, field

from .contract import WARNING_KINDS
from .table import Table, norm


@dataclass
class ParseResult:
    rows: list[dict] = field(default_factory=list)       # contract rows (engine.contract.COLUMNS)
    warnings: list[dict] = field(default_factory=list)   # contract warnings

    def add(self, row: dict) -> None:
        self.rows.append(row)

    def warn(self, table: Table, source_row: int, kind: str, reason: str) -> None:
        assert kind in WARNING_KINDS, f"unknown warning kind {kind!r}"
        self.warnings.append(
            {"source_file": table.name, "source_row": source_row, "kind": kind, "reason": reason}
        )


class Parser:
    """One subclass per source. Subclasses set the attributes and implement parse()."""

    source: str = ""             # value for the `source` column; also the key in source_status.json
    marketplace: str = "other"   # default `marketplace` bucket for this source
    filename_patterns: tuple[str, ...] = ()   # regexes, searched case-insensitively in the file name
    # Columns that must all be present (matched normalized). An entry can be a tuple of alternative
    # names, any one of which satisfies it: ("order id", ("buyer username", "buyer")).
    required_columns: tuple = ()

    def detect(self, table: Table) -> int:
        """Return 0 if this parser does not recognize the file, else a score (higher = surer).

        Columns are stronger evidence than the file name, since people rename downloads.
        Override only for sources that need something custom.
        """
        def present(entry) -> bool:
            names = (entry,) if isinstance(entry, str) else entry
            return any(norm(n) in table.norm_header for n in names)

        columns_ok = bool(self.required_columns) and all(present(c) for c in self.required_columns)
        name_ok = any(re.search(p, table.name, re.IGNORECASE) for p in self.filename_patterns)
        if self.required_columns and not columns_ok:
            return 0  # a declared column signature is a hard requirement
        if columns_ok:
            return 3 if name_ok else 2
        return 1 if name_ok else 0

    def parse(self, table: Table) -> ParseResult:
        raise NotImplementedError(f"{type(self).__name__}.parse is not implemented")


_REGISTRY: list[type[Parser]] = []


def register(cls: type[Parser]) -> type[Parser]:
    if not cls.source:
        raise ValueError(f"{cls.__name__} must set `source`")
    if any(c.source == cls.source for c in _REGISTRY):
        raise ValueError(f"source {cls.source!r} is already registered")
    _REGISTRY.append(cls)
    return cls


def load_sources() -> list[Parser]:
    """Import every module in engine/sources/ (which registers its parsers) and instantiate all."""
    from . import sources

    for mod in pkgutil.iter_modules(sources.__path__):
        importlib.import_module(f"{sources.__name__}.{mod.name}")
    return [cls() for cls in _REGISTRY]


class NoMatch(Exception):
    pass


class Ambiguous(Exception):
    pass


def detect_source(table: Table, parsers: list[Parser]) -> Parser:
    """Pick the parser for a table. Raises NoMatch, or Ambiguous when two sources tie."""
    scored = sorted(((p.detect(table), p) for p in parsers), key=lambda s: -s[0])
    scored = [s for s in scored if s[0] > 0]
    if not scored:
        raise NoMatch("no source recognizes this file")
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        names = ", ".join(p.source for score, p in scored if score == scored[0][0])
        raise Ambiguous(f"file matches several sources equally: {names}")
    return scored[0][1]
