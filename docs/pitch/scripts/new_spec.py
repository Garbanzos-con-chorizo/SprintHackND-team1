"""Scaffold an SDD spec folder: docs/pitch/specs/<slug>/spec.md + plan.md.

    python docs/pitch/scripts/new_spec.py 002-close-demo --title "Close demo" --owner Orlando
Never overwrites an existing file.
"""
import argparse
import datetime
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
TEMPLATE = os.path.join(ROOT, ".claude", "skills", "spec", "template.md")
PLAN = """# Plan: {title}

**Spec:** spec.md · **Status:** Draft

## Approach

## Phase 1: … (US1)
- [ ] T001 …
- **Exit criteria:** …
- **Audit:** `…`

## Risks and fallbacks
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--title", required=True)
    ap.add_argument("--owner", default="")
    a = ap.parse_args()
    d = os.path.normpath(os.path.join(ROOT, "docs", "pitch", "specs", a.slug))
    os.makedirs(d, exist_ok=True)
    vals = {"title": a.title, "slug": a.slug, "owner": a.owner, "date": datetime.date.today().isoformat()}
    for name, text in (("spec.md", open(TEMPLATE, encoding="utf-8").read()), ("plan.md", PLAN)):
        p = os.path.join(d, name)
        if os.path.exists(p):
            print(f"kept   {p}")
            continue
        with open(p, "w", encoding="utf-8") as f:
            f.write(text.format(**vals))
        print(f"wrote  {p}")


if __name__ == "__main__":
    main()
