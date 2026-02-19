# /standup

Generate a concise standup update based on recent git activity.

## Instructions

1. Run `git log --since="yesterday" --oneline --author="$(git config user.name)"` to get recent commits.

2. Run `git diff --stat HEAD~5 HEAD 2>/dev/null || git diff --stat $(git log --oneline | tail -1 | awk '{print $1}') HEAD` to see what files changed.

3. Check for any open PRs: `gh pr list --author @me --state open 2>/dev/null || echo "gh not available"`

4. Check for any assigned issues: `gh issue list --assignee @me --state open 2>/dev/null || echo "gh not available"`

5. Format the standup in this structure:

---

## Standup — <today's date>

**Yesterday**
- <bullet per logical chunk of work derived from commits>

**Today**
- <what would logically come next based on open PRs/issues and commit trajectory>

**Blockers**
- <any blockers visible from the git history or PR status, or "None">

---

Keep bullets concise (one line each). Group related commits into a single bullet. Don't list every commit verbatim.
