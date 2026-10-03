import json
import pytest

from engine.cli import run
from engine.parsers import Ambiguous, NoMatch, ParseResult, Parser, detect_source, load_sources
from engine.table import UnreadableFile, norm, read_table


class FakeA(Parser):
    source = "fake_a"
    marketplace = "other"
    filename_patterns = (r"fake.?a",)
    required_columns = ("Order ID", "Total")

    def parse(self, table):
        result = ParseResult()
        for n, row in table.rows:
            result.add({"txn_id": f"fake_a:{table.get(row, 'order id')}", "source_row": n,
                        "business_date": "2026-10-02", "marketplace": "other", "source_file": table.name})
        return result


class FakeB(Parser):
    source = "fake_b"
    filename_patterns = (r"fake.?b",)  # name only, no column signature


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_norm_matches_name_variants():
    assert norm("Order ID ") == norm("order_id") == norm("ORDER-ID") == "order id"


def test_reads_csv_skipping_title_lines_blank_rows_and_bom(tmp_path):
    p = tmp_path / "x.csv"
    p.write_bytes("﻿Sales report,,\n\nOrder ID,Total\n1,5.00\n\n2,7.00\n".encode("utf-8"))
    t = read_table(p)
    assert t.header == ["Order ID", "Total"]
    assert [n for n, _ in t.rows] == [1, 2]  # blank row ignored, numbering counts data rows only


def test_reads_semicolon_csv(tmp_path):
    t = read_table(write(tmp_path, "s.csv", "Order ID;Total\n1;5,00\n"))
    assert t.header == ["Order ID", "Total"]


def test_reads_xlsx(tmp_path):
    from openpyxl import Workbook

    wb = Workbook()
    wb.active.append(["Order ID", "Total"])
    wb.active.append(["SG-1", 12.5])
    p = tmp_path / "x.xlsx"
    wb.save(p)
    t = read_table(p)
    assert t.rows[0][1]["Order ID"] == "SG-1"


def test_unreadable_files_raise(tmp_path):
    with pytest.raises(UnreadableFile):
        read_table(write(tmp_path, "empty.csv", ""))
    with pytest.raises(UnreadableFile):
        read_table(write(tmp_path, "notes.pdf", "x"))
    with pytest.raises(UnreadableFile):
        read_table(write(tmp_path, "bad.xlsx", "not a zip"))


def test_detect_by_columns_even_if_file_renamed(tmp_path):
    t = read_table(write(tmp_path, "download (3).csv", "order_id,TOTAL\n1,2\n"))
    assert detect_source(t, [FakeA(), FakeB()]).source == "fake_a"


def test_detect_by_filename_when_no_column_signature(tmp_path):
    t = read_table(write(tmp_path, "FakeB_oct.csv", "anything,here\n1,2\n"))
    assert detect_source(t, [FakeA(), FakeB()]).source == "fake_b"


def test_column_signature_is_a_hard_requirement(tmp_path):
    t = read_table(write(tmp_path, "fake_a.csv", "other,cols\n1,2\n"))
    with pytest.raises(NoMatch):
        detect_source(t, [FakeA()])


def test_ambiguous_when_two_sources_tie(tmp_path):
    class Twin(FakeA):
        source = "twin"

    t = read_table(write(tmp_path, "x.csv", "Order ID,Total\n1,2\n"))
    with pytest.raises(Ambiguous):
        detect_source(t, [FakeA(), Twin()])


def test_filename_plus_columns_beats_columns_alone(tmp_path):
    class Twin(FakeA):
        source = "twin"
        filename_patterns = (r"twin",)

    t = read_table(write(tmp_path, "twin.csv", "Order ID,Total\n1,2\n"))
    assert detect_source(t, [FakeA(), Twin()]).source == "twin"


def test_run_collects_rows_and_warns_instead_of_crashing(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    write(inbox, "fake_a_oct2.csv", "Order ID,Total\nA1,5\nA2,6\n")
    write(inbox, "mystery.csv", "foo,bar\n1,2\n")
    write(inbox, "broken.xlsx", "not a zip")
    write(inbox, "~$lock.xlsx", "ignored")
    out = tmp_path / "out"

    run(inbox, out, "2026-10-02", parsers=[FakeA()])

    lines = (out / "transactions.csv").read_text(encoding="utf-8").splitlines()
    # parse() here only sets txn_id/source_row; the writer fills the rest of the columns blank
    assert len(lines) == 1 + 2
    warnings = json.loads((out / "warnings.json").read_text(encoding="utf-8"))
    assert {w["source_file"] for w in warnings} == {"mystery.csv", "broken.xlsx"}
    assert all(w["kind"] == "unparseable" for w in warnings)


def test_builtin_registry_loads_without_error():
    load_sources()  # engine/sources/ modules import cleanly and have unique source names
