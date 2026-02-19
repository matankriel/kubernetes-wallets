---
name: review-pr
description: Fetch a GitHub pull request diff using `gh` and perform a structured code review categorized by Security, Correctness, Quality, and Tests.
argument-hint: "[pr-number]"
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
context:
  - .claude/rules/security.md
  - .claude/rules/code-style.md
  - .claude/rules/testing.md
---

# /review-pr Skill

You are performing a structured pull request review. Follow these steps.

## Step 1: Fetch the PR

If a PR number was provided as an argument, use it. Otherwise, ask for the PR number.

```bash
# Get PR details
gh pr view <number> --json title,body,author,baseRefName,headRefName

# Get the diff
gh pr diff <number>

# Get list of changed files
gh pr view <number> --json files --jq '.files[].path'
```

## Step 2: Understand Context

Read relevant project files to understand conventions:
- `CLAUDE.md` for project overview
- `docs/context/conventions.md` for coding standards
- Any files in `docs/context/` relevant to the changed code

## Step 3: Review by Category

Evaluate the diff against each category:

### Security (P0 — Critical)
- SQL/command injection vectors
- Secrets or credentials in code
- Authorization bypass risks
- XSS via raw user input
- Insecure deserialization

### Correctness (P1 — Warning)
- Logic errors and off-by-one bugs
- Null/undefined handling
- Error paths and exception handling
- Race conditions or concurrency issues
- Data consistency risks

### Quality (P2 — Suggestion)
- Single-responsibility violations (functions > 40 lines)
- Naming clarity
- Dead code or unused imports
- Over-engineering or unnecessary abstractions
- Hardcoded values that should be config

### Tests (P1 — Warning)
- New code without tests
- Tests that test implementation details instead of behavior
- Missing edge case coverage
- No regression test for bug fixes

## Step 4: Output the Review

```
## PR Review: #<number> — <title>
**Author:** <author> | **Branch:** <head> → <base>

### Summary
<2-3 sentences: what the PR does and overall impression>

---

### 🔴 Security Issues (must fix)
<findings or "None found">

### 🟠 Correctness Issues (should fix)
<findings or "None found">

### 🟡 Quality Suggestions (optional)
<findings or "None found">

### 🟢 Test Coverage
<assessment of test completeness>

---

### Verdict
- [ ] Approve
- [ ] Approve with minor suggestions
- [x] Request Changes

**Required before merge:**
1. <specific required change>
```

## Notes

- Always cite file and line number for each finding
- Be specific — "this is wrong" is not actionable
- Acknowledge what's done well with 🟢 praise where warranted
- If the PR is large (> 500 lines), focus on the highest-risk sections first
