---
name: ship
description: Full shipping pipeline — lint, test, commit with conventional format, push feature branch, and open a GitHub PR. Stops at any failure.
argument-hint: "[optional: pr description]"
allowed-tools:
  - Bash
  - Read
  - Glob
context:
  - .claude/rules/git.md
  - .claude/rules/testing.md
---

# /ship Skill

You are running the full shipping pipeline. Each step must pass before proceeding to the next. Stop and report on any failure.

## Step 1: Pre-flight Checks

```bash
# Confirm we are NOT on a protected branch
git branch --show-current
```

If the current branch is `main` or `production`, **stop immediately** and tell the user to create a feature branch first:
```bash
git checkout -b feat/<description>
```

## Step 2: Lint

```bash
npm run lint 2>&1 || yarn lint 2>&1 || pnpm lint 2>&1
```

If lint fails, show the errors and stop. Tell the user: "Fix lint errors before shipping."

## Step 3: Tests

```bash
npm test 2>&1 || yarn test 2>&1 || pnpm test 2>&1
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

## Step 6: Open Pull Request

```bash
gh pr create \
  --title "<conventional commit title>" \
  --body "$(cat <<'EOF'
## Summary
<bullet points describing what changed and why>

## Test Plan
- [ ] Lint passes
- [ ] All tests pass
- [ ] Manually verified: <key scenario>

🤖 Shipped with [Claude Code](https://claude.ai/claude-code)
EOF
)"
```

If a PR description was passed as an argument to `/ship`, use it as the Summary section.

## Step 7: Confirm

Output:
```
Shipped!
Branch: <branch-name>
PR: <pr-url>
```

---

**Hard stops (never proceed past these):**
- Lint failure
- Test failure
- Attempted push to `main` or `production`
- Force push (--force) without explicit user authorization
