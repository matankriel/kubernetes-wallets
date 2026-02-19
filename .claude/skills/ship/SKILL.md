---
name: ship
description: Full shipping pipeline — lint, test, commit with conventional format, push feature branch, and open a GitLab Merge Request. Stops at any failure.
argument-hint: "[optional: mr description]"
allowed-tools:
  - Bash
  - Read
  - Glob
context:
  - .claude/rules/git.md
  - .claude/rules/testing.md
---

# /ship Skill

You are running the full InfraHub shipping pipeline. Each step must pass before proceeding. Stop and report on any failure.

## Step 1: Pre-flight Checks

```bash
git branch --show-current
```

If the current branch is `main`, **stop immediately** and tell the user to create a feature branch first:
```bash
git checkout -b feat/<story-id>-<description>
```

## Step 2: Lint

```bash
# Backend (if src/backend/ files changed)
cd src/backend && ruff check . 2>&1

# Frontend (if src/frontend/ files changed)
cd src/frontend && npm run lint 2>&1
```

If lint fails, show the errors and stop. Tell the user: "Fix lint errors before shipping."

## Step 3: Tests

```bash
# Backend
cd src/backend && pytest -x --tb=short 2>&1

# Frontend (if applicable)
cd src/frontend && npm test 2>&1
```

If tests fail, show the failures and stop. Tell the user: "Fix failing tests before shipping."

## Step 4: Commit

Review `git status` and `git diff --cached --stat`. Stage all modified tracked files:
```bash
git add -u
```

Compose a conventional commit message based on the changes. Show the message and ask for confirmation before committing.

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

<body if provided or derived from changes>
EOF
)"
```

## Step 5: Push

```bash
git push -u origin $(git branch --show-current)
```

If the push is rejected (diverged history), stop and report. Do not force-push without explicit user instruction.

## Step 6: Open Merge Request (GitLab)

```bash
glab mr create \
  --title "<conventional commit title>" \
  --description "$(cat <<'EOF'
## Summary
<bullet points describing what changed and why>

## Test Plan
- [ ] Backend lint (ruff) passes
- [ ] Backend tests (pytest) pass
- [ ] Frontend lint passes (if applicable)
- [ ] Frontend tests pass (if applicable)
- [ ] Manually verified: <key scenario>

🤖 Shipped with [Claude Code](https://claude.ai/claude-code)
EOF
)"
```

If `glab` is unavailable, push the branch and output:
```
Branch pushed: <branch-name>
Open MR manually at: <gitlab-url>/-/merge_requests/new?merge_request[source_branch]=<branch>
```

If an MR description was passed as an argument to `/ship`, use it as the Summary section.

## Step 7: Confirm

Output:
```
Shipped!
Branch: <branch-name>
MR: <mr-url>
```

---

**Hard stops (never proceed past these):**
- Lint failure
- Test failure
- Attempted push to `main`
- Force push (`--force`) without explicit user authorization
