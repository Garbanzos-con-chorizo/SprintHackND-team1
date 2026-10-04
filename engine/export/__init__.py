"""Exports of the KPI file (docs/contracts/kpi.md): CSV now, PDF and email next. They render, never compute."""
from .kpi_csv import COLUMNS, kpi_rows, write_kpi_csv

__all__ = ["COLUMNS", "kpi_rows", "write_kpi_csv"]
