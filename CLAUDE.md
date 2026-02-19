# CLAUDE.md — InfraHub Navigation Hub

> This file is the single entry point for Claude Code. It answers **What** this project is and **How** to work in it.

---

## What: Project Identity

**Name:** InfraHub
**Purpose:** Centralized, air-gapped, on-prem platform for managing Kubernetes namespaces and bare-metal servers across a large enterprise. The org hierarchy is **Center → Field → Department → Team → Project (namespace)**. Resources (servers + CPU/RAM quotas) flow down this hierarchy; admins at each level allocate to the next. Projects (namespaces) are provisioned via Helm + ArgoCD GitOps.
**Stack:** Python 3.12 + FastAPI (backend), React 18 + TypeScript (frontend), PostgreSQL, LDAP + JWT auth, Helm + ArgoCD GitOps, GitLab CI, Kubernetes (`infrahub-system` namespace)
**Air-gapped:** No external HTTP calls except to the internal bare-metal inventory API (`EXTERNAL_SERVER_API_URL`) and internal ArgoCD (`ARGOCD_URL`).

---

## What: Key Files

| Path | Purpose |
|------|---------|
| `CLAUDE.md` | This file — navigation hub |
| `CLAUDE.local.md` | Personal overrides (gitignored) |
| `.claude/settings.json` | Permissions, hooks, env config |
| `.claude/rules/` | Scoped behavioral rules |
| `.claude/agents/` | Subagent definitions |
| `.claude/skills/` | Slash-command skills |
| `docs/context/` | Detailed context documents |
| `ralph/run.sh` | Autonomous story-implementation loop |
| `ralph/prd.json` | InfraHub story backlog (8 stories) |
| `ralph/prompt.md` | Ralph system prompt (InfraHub constraints) |
| `src/backend/` | Python FastAPI backend |
| `src/frontend/` | React TypeScript frontend |
| `src/helm/` | Managed Helm chart for namespace provisioning |
| `.env.example` | All required environment variables |
| `.gitlab-ci.yml` | GitLab CI pipeline |

---

## What: Architecture Overview

@docs/context/architecture.md

---

## What: Patterns & Conventions Summary

@docs/context/conventions.md

---

## How: Run Commands

```bash
# ── Backend ──────────────────────────────────────────────
# Install backend deps
cd src/backend && pip install -e ".[dev]"

# Run backend dev server
cd src/backend && uvicorn app.main:app --reload --port 8000

# Run backend tests
cd src/backend && pytest -x --tb=short

# Run backend lint
cd src/backend && ruff check .

# Run DB migrations
cd src/backend && alembic upgrade head

# ── Frontend ─────────────────────────────────────────────
# Install frontend deps
cd src/frontend && npm ci

# Run frontend dev server
cd src/frontend && npm run dev

# Run frontend tests
cd src/frontend && npm test

# ── Local dev stack ───────────────────────────────────────
# Start postgres + mock-ldap + backend + frontend
docker-compose up

# ── Ralph ────────────────────────────────────────────────
# Run next pending story
bash ralph/run.sh --once

# Run specific story
bash ralph/run.sh --story STORY-001

# Dry-run: print prompt without calling Claude
bash ralph/run.sh --dry-run

# Run all pending stories
bash ralph/run.sh
```

---

## What: Org Hierarchy

```
Center (e.g. "HQ Center East")
  └── Field (e.g. "Field-Berlin") — contains bare-metal servers at a site
        └── Department (e.g. "Engineering")
              └── Team (e.g. "Platform Team") — mapped to an LDAP group
                    └── Project (Kubernetes namespace, e.g. "platform-team-payments")
```

Resources flow down: Center assigns servers to Fields → Fields allocate CPU/RAM quotas to Departments → Departments allocate to Teams → Teams create Projects (namespaces).

---

## What: RBAC Summary

| Role | Scope | Can Do |
|------|-------|--------|
| `center_admin` | global | assign servers to fields, manage all |
| `field_admin` | `scope_id=field_id` | set dept quotas within their field |
| `dept_admin` | `scope_id=dept_id` | set team quotas within their dept |
| `team_lead` | `scope_id=team_id` | create/delete projects for their team |

JWT: HS256, 15-min expiry, `{sub, role, scope_id, exp}`. No refresh token.

---

## How: Common Tasks

### Coding
- Follow conventions in @docs/context/conventions.md
- Security rules always apply: @.claude/rules/security.md
- Code style: @.claude/rules/code-style.md
- **Never** use sync SQLAlchemy — all DB access is async
- **Never** make HTTP calls to external URLs not in AppSettings
- **Always** use canonical domain names (center/field/department/team/project/site/quota/performance_tier)

### Testing
- Testing standards: @docs/context/testing.md
- Scoped rule: @.claude/rules/testing.md

### Git Workflow
- Git rules: @.claude/rules/git.md
- Full workflow: @docs/context/workflows.md
- Use `/commit` skill for conventional commits
- Use `/ship` skill for full lint → test → commit → MR pipeline
- Remote is **GitLab** — use `glab` not `gh`

### Reviewing
- Use the `code-reviewer` subagent for MR reviews
- Use `/review-pr [number]` skill to fetch and review an MR

### Shipping
- Deployment context: @docs/context/deployment.md
- Run `/ship` to lint, test, commit, push, and open an MR

### Onboarding
- @docs/context/onboarding.md

---

## How Claude Should Behave

- **Plan before acting:** For any task touching more than 2 files, describe the plan first and wait for confirmation.
- **Minimal changes:** Only modify what is necessary. Do not refactor, add comments, or improve code beyond the explicit request.
- **No speculative features:** Do not add error handling, logging, or abstractions for hypothetical future needs.
- **Security first:** Never introduce command injection, SQL injection, XSS, or other OWASP top-10 vulnerabilities.
- **Confirm destructive actions:** Ask before deleting files, dropping data, force-pushing, or modifying CI/CD.
- **Conventional commits:** Always use `type(scope): message` format. Use `/commit` skill.
- **No direct pushes to protected branches:** `main` is protected. Always use feature branches and MRs.
- **Test before shipping:** Never mark a story done or create an MR without running tests.
- **Air-gap compliance:** Never call external URLs at runtime except `EXTERNAL_SERVER_API_URL` and `ARGOCD_URL` from AppSettings.
- **Allocation invariant:** Every quota write must use `SELECT FOR UPDATE` and verify `cpu_used + requested <= cpu_limit` before committing.
- **Agents for specialization:** Use `code-reviewer` for reviews, `debugger` for bug fixes, `spec-writer` for documentation, `ux-researcher` at planning time, `product-reviewer` for developer-tooling UX audits, `simplicity-checker` before merging new code, `pipeline-optimizer` when agent/Ralph outputs degrade.
