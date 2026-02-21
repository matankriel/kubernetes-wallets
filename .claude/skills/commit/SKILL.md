---
name: commit
description: Run lint and tests, stage specific files, and create a conventional commit. Refuses to commit if lint or tests fail.
argument-hint: "[optional: files to stage]"
allowed-tools:
  - Bash
  - Read
  - Glob
---

# /commit Skill

You are performing a safe, conventional commit for InfraHub. Follow these steps exactly.

## Step 1: Check Status

Run `git status` to see what has changed. List the changed files and ask the user to confirm which ones should be staged (unless they specified files in the command argument).

## Step 2: Lint

Run the appropriate linter based on what files changed:

```bash
# If backend files changed (src/backend/):
cd src/backend && ruff check . 2>&1

# If frontend files changed (src/frontend/):
cd src/frontend && npm run lint 2>&1
```

If lint **fails**, stop immediately. Report the errors and tell the user to fix them before committing. Do not proceed.

## Step 3: Tests

Run the appropriate tests based on what files changed:

```bash
# If backend files changed:
cd src/backend && pytest -x --tb=short 2>&1

# If frontend files changed:
cd src/frontend && npm test 2>&1
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

[optional footer: Closes #<issue>]
```

**Types:** `feat` | `fix` | `docs` | `style` | `refactor` | `test` | `chore` | `perf` | `ci` | `revert`

**InfraHub scope examples:** `auth`, `allocation`, `projects`, `servers`, `migrations`, `frontend`, `helm`, `sync`

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
- Never commit `.env` files, secrets, or JWT_SECRET values
- Never commit directly to `main`
- Never commit `LDAP_BIND_PASSWORD` or any credential
