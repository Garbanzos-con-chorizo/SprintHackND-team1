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
    ap.add_argument("--html", help="also write one offline HTML file to present and record (e.g. docs/pitch/deck/deck.html)")
    ap.add_argument("--preview", action="store_true", help="also screenshot every slide to <out>/preview/")
    a = ap.parse_args()
    ids = deckgen.build(a.content, a.out)
    issues = lint_deck.lint(a.content, a.out)
    for level, sid, msg in issues:
        print(f"{level:5} {sid}: {msg}")
    if a.html:
        import export_html
        print(f"html: {export_html.export(a.out, a.html)}")
    if a.preview:
        import preview
        shots = preview.preview(a.out)
        print(f"preview: {len(shots)} PNGs + contact.html in {os.path.join(a.out, 'preview')}")
    errors = sum(1 for i in issues if i[0] == "ERROR")
    print(f"built {len(ids)} slides -> {os.path.join(a.out, 'project')} | {errors} errors, {len(issues) - errors} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
