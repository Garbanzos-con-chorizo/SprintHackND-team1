"""Build a deck from content.json into Slides-artifact files, then lint it.

    python docs/pitch/scripts/build_deck.py docs/pitch/deck/content.json --out <dir>
Prints one line per issue and a summary; exit 1 if any ERROR.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import deckgen  # noqa: E402
import lint_deck  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ids = deckgen.build(a.content, a.out)
    issues = lint_deck.lint(a.content, a.out)
    for level, sid, msg in issues:
        print(f"{level:5} {sid}: {msg}")
    errors = sum(1 for i in issues if i[0] == "ERROR")
    print(f"built {len(ids)} slides -> {os.path.join(a.out, 'project')} | {errors} errors, {len(issues) - errors} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
