"""Summarize what an audit of one plan phase must check.

    python docs/pitch/scripts/audit_phase.py docs/pitch/specs/001-pitch-deck --phase 1
Lists the phase's tasks (done/open), its exit criteria, open [NEEDS CLARIFICATION]
markers in spec and plan, and which criteria have no evidence line yet in
audit-phaseN.md. Exit 1 if anything is open.
"""
import argparse
import os
import re
import sys


def phase_block(plan, n):
    m = re.search(rf"^## Phase {n}\b.*?(?=^## |\Z)", plan, flags=re.M | re.S)
    return m.group(0) if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec_dir")
    ap.add_argument("--phase", type=int, required=True)
    a = ap.parse_args()
    spec = open(os.path.join(a.spec_dir, "spec.md"), encoding="utf-8").read()
    plan = open(os.path.join(a.spec_dir, "plan.md"), encoding="utf-8").read()
    block = phase_block(plan, a.phase)
    if not block:
        sys.exit(f"no '## Phase {a.phase}' in plan.md")
    open_tasks = re.findall(r"^- \[ \] (.+)$", block, flags=re.M)
    done = re.findall(r"^- \[x\] (.+)$", block, flags=re.M | re.I)
    criteria = sorted(set(re.findall(r"\b((?:AC|SC|R)-\d{3})\b", block)))
    markers = re.findall(r"\[NEEDS CLARIFICATION[^\]]*\]", spec + plan)
    audit_path = os.path.join(a.spec_dir, f"audit-phase{a.phase}.md")
    evidence = open(audit_path, encoding="utf-8").read() if os.path.exists(audit_path) else ""
    missing = [c for c in criteria if not re.search(rf"(PASS|FAIL|PARTIAL)\W+{c}\b", evidence)]
    print(f"phase {a.phase}: {len(done)} tasks done, {len(open_tasks)} open")
    for t in open_tasks:
        print(f"  OPEN  {t}")
    print(f"criteria: {', '.join(criteria) or 'none listed'}")
    for c in missing:
        print(f"  NO EVIDENCE  {c}")
    for m in markers:
        print(f"  MARKER  {m}")
    sys.exit(1 if open_tasks or missing or markers else 0)


if __name__ == "__main__":
    main()
