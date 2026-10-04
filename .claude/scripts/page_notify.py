#!/usr/bin/env python3
"""
Page notification helper: updates status file and coordinates notifications.
Usage: python page_notify.py <teammate> [branch] [note]
"""

import sys
import subprocess
from datetime import datetime
from pathlib import Path

VALID_TEAMMATES = {"victor", "dani", "orlando"}
REPO_ROOT = Path(__file__).parent.parent.parent

def get_caller_name():
    """Get current git user name."""
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error reading git config: {e}")
        sys.exit(1)

def append_to_status_file(teammate, caller, timestamp, branch, note):
    """Append to docs/members/<teammate>.md under 'Requests to me'."""
    status_file = REPO_ROOT / "docs" / "members" / f"{teammate}.md"

    if not status_file.exists():
        print(f"Error: Status file not found: {status_file}")
        sys.exit(1)

    # Read the current content
    content = status_file.read_text()

    # Build the entry
    if branch and note:
        entry = f"- [from {caller}, {timestamp}] **{branch}**: {note}"
    elif branch:
        entry = f"- [from {caller}, {timestamp}] **{branch}**"
    else:
        entry = f"- [from {caller}, {timestamp}] {note}"

    # Find "Requests to me" section and append
    lines = content.split("\n")
    requests_idx = -1
    for i, line in enumerate(lines):
        if "Requests to me" in line:
            requests_idx = i
            break

    if requests_idx == -1:
        # Create the section if it doesn't exist
        if not content.endswith("\n"):
            content += "\n"
        content += "\n## Requests to me (append only: `- [from X, time] request`)\n"
        content += entry + "\n"
    else:
        # Find the end of the existing entries and append
        insert_idx = requests_idx + 2  # After the heading and blank line
        while insert_idx < len(lines) and lines[insert_idx].startswith("-"):
            insert_idx += 1
        lines.insert(insert_idx, entry)
        content = "\n".join(lines)

    # Write back
    status_file.write_text(content)
    print(f"✓ Updated {status_file.relative_to(REPO_ROOT)}")

    return entry

def main():
    if len(sys.argv) < 2:
        print("Usage: page_notify.py <teammate> [branch] [note]")
        print(f"Valid teammates: {', '.join(VALID_TEAMMATES)}")
        sys.exit(1)

    teammate = sys.argv[1].lower()
    branch = sys.argv[2] if len(sys.argv) > 2 else None
    note = sys.argv[3] if len(sys.argv) > 3 else None

    # Validate teammate
    if teammate not in VALID_TEAMMATES:
        print(f"Error: Invalid teammate '{teammate}'. Valid options: {', '.join(VALID_TEAMMATES)}")
        sys.exit(1)

    # Get caller info
    caller = get_caller_name()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n📧 Paging {teammate}...")
    print(f"   From: {caller}")
    print(f"   Branch: {branch or '(none)'}")
    print(f"   Note: {note or '(none)'}")
    print(f"   Time: {timestamp}\n")

    # Update status file
    entry = append_to_status_file(teammate, caller, timestamp, branch, note)

    # Commit and push
    try:
        subprocess.run(
            ["git", "add", f"docs/members/{teammate}.md"],
            cwd=REPO_ROOT,
            check=True
        )

        commit_msg = f"docs: {teammate} paged by {caller}"
        if branch:
            commit_msg += f" on {branch}"

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=REPO_ROOT,
            check=True
        )

        subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=REPO_ROOT,
            check=True
        )
        print(f"✓ Committed and pushed")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Git operation failed: {e}")
        print("  (Status file was updated locally but not pushed)")
        return 1

    # Summary
    print(f"\n✓ Page sent to {teammate}!")
    print(f"  → Status file updated")
    print(f"  → Entry: {entry}")
    print(f"  → Notification will arrive on their next session pull")

    return 0

if __name__ == "__main__":
    sys.exit(main())
