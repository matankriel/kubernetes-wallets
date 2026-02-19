# /standup

Generate a concise standup update based on recent git activity.

## Instructions

1. Run `git log --since="yesterday" --oneline --author="$(git config user.name)"` to get recent commits.

2. Run `git diff --stat HEAD~5 HEAD 2>/dev/null || git diff --stat $(git log --oneline | tail -1 | awk '{print $1}') HEAD` to see what files changed.

3. Check for any open MRs: `glab mr list --author @me --state opened 2>/dev/null || echo "glab not available"`

4. Check for any assigned issues: `glab issue list --assignee @me --state opened 2>/dev/null || echo "glab not available"`

5. Check Ralph story statuses: `jq '[.stories[] | select(.status != "pending") | {id, status, title}]' ralph/prd.json 2>/dev/null`

6. Format the standup in this structure:

---

## Standup — <today's date>

**Yesterday**
- <bullet per logical chunk of work derived from commits>
- Ralph: <any stories completed/failed by the autonomous loop>

**Today**
- <what would logically come next based on open MRs/issues and commit trajectory>
- Next Ralph story: <next pending story from prd.json>

**Blockers**
- <any blockers visible from the git history, MR status, or failed Ralph runs, or "None">

---

Keep bullets concise (one line each). Group related commits into a single bullet. Don't list every commit verbatim.
