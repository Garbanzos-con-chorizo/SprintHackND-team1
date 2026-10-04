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
        {"id": "a", "layout": "statement", "title": "Send us one *real* month.", "notes": "n"},
        {"id": "b", "layout": "quotes", "title": "Three reports are built by hand", "quotes": [{"label": "x", "text": "y"}], "notes": "n"},
        {"id": "c", "layout": "system", "title": "One program builds all three", "in_label": "In", "inputs": ["a"],
         "core": {"head": "Core"}, "out_label": "Out", "outputs": ["b"], "notes": "n"},
        {"id": "d", "layout": "timeline", "title": "A missing report gets named", "steps": [{"head": "a"}, {"head": "b", "flag": True}], "notes": "n"},
        {"id": "e", "layout": "duo", "title": "What is real and what is simulated",
         "left": {"label": "L", "marked": True, "items": ["a"]}, "right": {"label": "R", "items": ["b"]}, "notes": "n"},
        {"id": "f", "layout": "points", "title": "It checks its own work", "points": ["a", "b"], "notes": "n"},
        {"id": "g", "layout": "closing", "title": "Send us one real month of files.", "then": ["a"], "notes": "n"},
    ]
    assert [i for i in _deck(tmp_path, slides) if i[0] == "ERROR"] == []
    idx = json.load(open(tmp_path / "out" / "project" / "deck.json"))
    assert idx["order"] == list("abcdefg")
    assert idx["faces"] == {}  # no web fonts: system fonts only


def test_lint_catches_repeats_labels_and_placeholders(tmp_path):
    slides = [
        {"id": "a", "layout": "points", "title": "Results", "points": ["[TBD]"]},
        {"id": "b", "layout": "points", "title": "More results here now", "points": ["t"], "notes": "n"},
    ]
    msgs = {(lvl, sid, m.split(" ")[0]) for lvl, sid, m in _deck(tmp_path, slides)}
    assert ("ERROR", "b", "same") in msgs
    assert ("WARN", "a", "title") in msgs
    assert ("WARN", "a", "placeholder") in msgs
    assert ("WARN", "a", "no") in msgs
