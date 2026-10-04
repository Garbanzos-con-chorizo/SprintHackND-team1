import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deckgen  # noqa: E402
import lint_deck  # noqa: E402


def _deck(tmp_path, slides):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"title": "T", "theme": "swiss", "footer": "f", "slides": slides}), encoding="utf-8")
    deckgen.build(str(p), str(tmp_path / "out"))
    return lint_deck.lint(str(p), str(tmp_path / "out"))


def test_every_layout_renders_clean(tmp_path):
    slides = [
        {"id": "a", "layout": "statement", "title": "Send us one real month.", "notes": "n"},
        {"id": "b", "layout": "quotes", "title": "Three reports are built by hand", "quotes": [{"label": "x", "text": "y"}], "notes": "n"},
        {"id": "c", "layout": "hero", "title": "Revenue matches the key to the cent", "number": "$70,753.96", "notes": "n"},
        {"id": "d", "layout": "ledger", "title": "Two gaps are named by day", "rows": [{"status": "s", "label": "l", "amount": "$1"}], "notes": "n"},
        {"id": "e", "layout": "columns", "title": "One engine runs all three reports", "cols": [{"label": "a", "head": "b", "text": "c"}], "notes": "n"},
        {"id": "f", "layout": "table", "title": "Everything simulated is labelled here", "head": ["a", "b"], "rows": [["1", "2"]], "notes": "n"},
    ]
    assert [i for i in _deck(tmp_path, slides) if i[0] == "ERROR"] == []
    idx = json.load(open(tmp_path / "out" / "project" / "deck.json"))
    assert idx["order"] == list("abcdef")


def test_lint_catches_repeats_labels_and_placeholders(tmp_path):
    slides = [
        {"id": "a", "layout": "columns", "title": "Results", "cols": [{"head": "h", "text": "[TBD]"}]},
        {"id": "b", "layout": "columns", "title": "More results here now", "cols": [{"head": "h", "text": "t"}], "notes": "n"},
    ]
    msgs = {(lvl, sid, m.split(" ")[0]) for lvl, sid, m in _deck(tmp_path, slides)}
    assert ("ERROR", "b", "same") in msgs
    assert ("WARN", "a", "title") in msgs
    assert ("WARN", "a", "placeholder") in msgs
    assert ("WARN", "a", "no") in msgs
