---
name: commit
description: Run lint and tests, stage specific files, and create a conventional commit. Refuses to commit if lint or tests fail.
argument-hint: "[optional: files to stage]"
allowed-tools:
  - Bash
  - Read
  - Glob
context:
  - .claude/rules/git.md
---

# /commit Skill

You are performing a safe, conventional commit. Follow these steps exactly.

## Step 1: Check Status

Run `git status` to see what has changed. List the changed files and ask the user to confirm which ones should be staged (unless they specified files in the command argument).

## Step 2: Lint

Run the project linter:
```bash
npm run lint 2>&1 || yarn lint 2>&1 || echo "No lint script found"
```

If lint **fails**, stop immediately. Report the lint errors and tell the user to fix them before committing. Do not proceed.

## Step 3: Tests

Run the test suite:
```bash
npm test 2>&1 || yarn test 2>&1 || echo "No test script found"
```

If tests **fail**, stop immediately. Report the failures and tell the user to fix them before committing. Do not proceed.

## Step 4: Stage Files

Stage the confirmed files specifically (never use `git add -A` or `git add .` without listing what will be included):
```bash
git add <file1> <file2> ...
```

Show the staged diff with `git diff --cached --stat`.

## Step 5: Compose Commit Message

Analyze the staged changes and compose a conventional commit message:

```
<type>(<scope>): <short description in imperative mood>

[optional body: explain WHY, not WHAT]

[optional footer: Closes #<issue>, BREAKING CHANGE: <description>]
```

**Types:** `feat` | `fix` | `docs` | `style` | `refactor` | `test` | `chore` | `perf` | `ci` | `revert`

Present the proposed commit message to the user for confirmation before committing.

## Step 6: Commit

After user confirmation:
```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

<body if any>

<footer if any>
EOF
)"
```

## Step 7: Confirm

Run `git log --oneline -3` to show the commit was created successfully.

---

**Remember:**
- Never use `--no-verify`
- Never commit `.env` files or secrets
- Never commit directly to `main` or `production`
