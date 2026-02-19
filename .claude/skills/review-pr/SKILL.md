---
name: review-pr
description: Fetch a GitLab Merge Request diff using `glab` and perform a structured code review categorized by Security, Correctness, Quality, and Tests.
argument-hint: "[mr-number]"
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

You are performing a structured Merge Request review for InfraHub. Follow these steps.

## Step 1: Fetch the MR

If an MR number was provided as an argument, use it. Otherwise, ask for the MR number.

```bash
# Get MR details
glab mr view <number>

# Get the diff
glab mr diff <number>
```

If `glab` is unavailable, ask the user to paste the diff directly.

## Step 2: Understand Context

Read relevant project files to understand conventions:
- `CLAUDE.md` for project overview
- `docs/context/conventions.md` for coding standards
- Any files in `docs/context/` relevant to the changed code

## Step 3: Review by Category

Evaluate the diff against each category:

### Security (P0 — Critical)
- SQL injection via f-string queries (must use SQLAlchemy parameterized queries)
- JWT secret or LDAP credentials in code
- Authorization bypass: role/scope_id check missing or in router instead of service layer
- External HTTP call to a URL not from `AppSettings` (air-gap violation)
- Token stored in `localStorage`/`sessionStorage` (must be memory-only in Zustand)

### Correctness (P1 — Warning)
- Allocation invariant not enforced with `SELECT FOR UPDATE`
- Sync SQLAlchemy used instead of async (`session.query()` without await)
- Race condition in quota update (two concurrent requests both passing the invariant check)
- Missing `await` on async DB calls
- Null/None handling in repository return values
- Error paths and exception handling gaps
- Wrong HTTP status code returned for a domain error

### Quality (P2 — Suggestion)
- Canonical domain name violated (e.g., using `namespace` instead of `project`, `region` instead of `field`)
- Business logic placed in router instead of service layer
- DB access directly in router (bypassing repository)
- Functions > 40 lines
- Hardcoded values that should come from `AppSettings`
- Dead code or unused imports

### Tests (P1 — Warning)
- New service method without a unit test
- Allocation invariant boundary not tested (`cpu_used + requested == limit` and `+1`)
- RBAC not tested (wrong role / wrong scope_id)
- MockLDAPClient or MockHelmProvisioner not used where real calls would be made
- Integration test missing `@pytest.mark.integration` marker

## Step 4: Output the Review

```
## MR Review: !<number> — <title>
**Author:** <author> | **Branch:** <head> → <base>

### Summary
<2-3 sentences: what the MR does and overall impression>

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
- Be specific — "allocation invariant not checked" not just "missing check"
- Acknowledge what's done well with 🟢 praise where warranted
- If the MR is large (> 500 lines), focus on the highest-risk sections first
