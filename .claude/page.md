---
name: page
description: Notify a teammate across sessions that work is ready for pickup. Use this when you've completed a task and want to hand it off — specify the teammate name and optionally the branch. Sends a PushNotification alert and updates their status file "Requests to me" section so they see it next session. Teammates on the Pulse project are victor, dani, orlando.
compatibility: Requires PushNotification and status file write access to docs/members/
---

# /page — Notify teammate of handoff

When your work is done and another team member needs to pick it up, page them to create awareness across sessions and computers.

## Usage

```
/page <teammate> [<branch>] [<note>]
```

**Parameters:**
- `<teammate>` — Name of team member (victor, dani, orlando)
- `<branch>` (optional) — Git branch name, e.g. `victor/internal-api`. If omitted, the page includes only the note.
- `<note>` (optional) — Brief context, e.g. "V2.6 done, ready for merge" (max ~50 words)

**Examples:**
```
/page orlando victor/internal-api
/page dani dani/kpi-files "Schema done, sample files attached"
/page victor "Check docs/decisions/008 amendment"
```

## What happens

1. **Identify yourself** from `git config user.name` (or ask if unclear)
2. **Update their status file** — Append to `docs/members/<teammate>.md` under "Requests to me" (append-only):
   ```
   - [from <You>, <timestamp>] <branch>: <note>
   ```
   If no branch: `- [from <You>, <timestamp>] <note>`

3. **Send PushNotification** — Alert them across computers:
   ```
   <You> paged you on branch <branch>
   <note>
   ```
   (If no branch, just the note)

4. **Create TaskCreate chip** (optional) — If they're not actively reading their status, a background task chip makes it visible in their session queue:
   ```
   Title: "Pickup: <branch>" or "Pickup: <note>"
   Description: "From <You>: ready on <branch>"
   ```

5. **Commit and push** — Stage the status file change, commit with message `docs: <teammate> requested page on <branch>`, and push (so it's live when they pull).

## Rules

- **Always append to status files, never rewrite.** Other agents may also append; reads and writes should not conflict.
- **Timestamp format:** `YYYY-MM-DD HH:MM` in the timezone of your session (e.g. `2026-10-03 14:30`)
- **Branch name is optional** — If you're paging about a general update (not tied to a branch), omit it.
- **Keep notes brief** — ~50 words max. If there's a lot of context, say "see PR #X" or "check decision 008".
- **Verify the teammate exists** — Only victor, dani, orlando are valid. If unclear, ask.

## Example workflow

You finish V2.6 (internal API pull), push the branch, then:

```
/page dani victor/internal-api "V2.6 done, snapshot rows into internal_daily"
```

Result:
- `docs/members/dani.md` gets: `- [from Victor, 2026-10-03 14:45] victor/internal-api: V2.6 done, snapshot rows into internal_daily`
- Dani's computer gets a notification: "Victor paged you on victor/internal-api: V2.6 done, snapshot rows into internal_daily"
- A background task chip appears in Dani's next Claude session (if one is running): "Pickup: victor/internal-api — From Victor: ready"
- The change is committed and pushed so it's live when Dani pulls `main`

## Integration with handoff protocol

This skill complements the `/handoff` protocol:
- **`/handoff`** — Personal exit ritual: commit, push, update your own status file with what's done/blocked/next
- **`/page <teammate>`** — Alert them that their turn is up: update their inbox, send notifications

Run both when you're done:
```
/handoff
/page orlando victor/internal-api
```
