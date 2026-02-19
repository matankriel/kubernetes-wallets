# Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Users (Browser)                           │
│                  (air-gapped internal network)                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP (internal only)
┌──────────────────────────▼───────────────────────────────────────┐
│                   React Frontend (port 3000)                     │
│          Vite + React 18 + TypeScript + React Query              │
│          Auth token in memory (Zustand) — never persisted        │
└──────────────────────────┬───────────────────────────────────────┘
                           │ REST /api/v1/*
┌──────────────────────────▼───────────────────────────────────────┐
│                  FastAPI Backend (port 8000)                     │
│                  Python 3.12, async SQLAlchemy                   │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   Routers   │  │   Services   │  │   Repositories         │  │
│  │ (HTTP only) │→ │(biz logic +  │→ │(async SQLAlchemy,      │  │
│  │             │  │ auth enforce)│  │ SELECT FOR UPDATE)     │  │
│  └─────────────┘  └──────────────┘  └──────────┬─────────────┘  │
│                                                 │                │
│  ┌──────────────────┐  ┌───────────────────┐   │                │
│  │  LDAPClient ABC  │  │  HelmProvisioner  │   │                │
│  │  RealLDAPClient  │  │  GitArgoProvisioner│  │                │
│  └──────────────────┘  └───────────────────┘   │                │
│                                                 │                │
│  ┌──────────────────────────────────────────────▼─────────────┐ │
│  │         APScheduler (background server sync job)           │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────┬──────────────────────┬────────────────────┬────────────┘
         │                      │                    │
┌────────▼──────┐  ┌────────────▼────────┐  ┌───────▼──────────┐
│  PostgreSQL   │  │  Internal LDAP      │  │  ArgoCD (internal)│
│  (primary DB) │  │  ldap.internal:636  │  │  argocd.internal  │
└───────────────┘  └─────────────────────┘  └──────────────────┘
                                                      │
                                             ┌────────▼──────────┐
                                             │  GitLab (internal)│
                                             │  Helm chart repo  │
                                             └───────────────────┘

┌────────────────────────────────────────────────────────────────┐
│              Bare-Metal Inventory API (read-only)              │
│              baremetal-api.internal                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### FastAPI Backend

**Entry point:** `src/backend/app/main.py` — FastAPI app factory with lifespan context manager.

**Layer structure (strict, no skipping):**
```
Router → Service → Repository → Database
```

- **Routers** (`app/routers/`): HTTP concerns only — parse request, call service, return response. No business logic.
- **Services** (`app/services/`): Business logic + RBAC enforcement. Receive/return domain objects. Raise domain errors (`ForbiddenError`, `QuotaExceededError`), not HTTP exceptions.
- **Repositories** (`app/repositories/`): Async SQLAlchemy queries. Use `SELECT FOR UPDATE` on quota rows for atomic invariant checks.
- **Models** (`app/models/`): SQLAlchemy ORM models (org.py, server.py, allocation.py, project.py).
- **Schemas** (`app/schemas/`): Pydantic request/response schemas (one file per domain).

### LDAP Authentication Flow

```
POST /api/v1/auth/login
  1. Bind LDAP with user credentials (verifies password)
  2. Re-bind as service account (LDAP_BIND_DN)
  3. Search user's memberOf attribute → list of group CNs
  4. Map group CNs to (role, scope_id):
       infrahub-center-admins         → center_admin, scope_id=None
       infrahub-field-admins-<id>     → field_admin,  scope_id=<id>
       infrahub-dept-admins-<id>      → dept_admin,   scope_id=<id>
       infrahub-team-leads-<id>       → team_lead,    scope_id=<id>
  5. Issue JWT: {sub, role, scope_id, exp=now+15min}, HS256
  6. Return {access_token, token_type: "bearer", expires_in: 900}
```

If LDAP bind fails → 401 `INVALID_CREDENTIALS`.
If user has no `infrahub-*` group → 403 `NO_ROLE_ASSIGNED`.

### Server Sync

```
APScheduler (every SYNC_INTERVAL_MINUTES)
  → sync_servers(session, http_client)
      → GET EXTERNAL_SERVER_API_URL  (internal bare-metal API, air-gapped)
      → For each server in response:
          - Classify performance_tier:
              cpu >= PERFORMANCE_TIER_CPU_THRESHOLD → high_performance
              else                                  → regular
          - Upsert into servers table (name-keyed)
          - Touch synced_at timestamp
      → Mark servers absent from response as status=offline
      → Return {synced, updated, marked_offline}
```

Manual trigger: `POST /api/v1/admin/sync/servers` (center_admin only).

### Project Provisioning Flow (Helm + ArgoCD)

```
POST /api/v1/projects
  1. Validate JWT: role=team_lead, scope_id=team_id
  2. Load team quota for requested site
  3. Map (sla_type, performance_tier) → (required_cpu, required_ram):
       bronze/regular=2/4   bronze/hp=4/8
       silver/regular=4/16  silver/hp=8/32
       gold/regular=8/32    gold/hp=16/64
  4. BEGIN TRANSACTION
       SELECT team_quota FOR UPDATE
       Assert cpu_used + required_cpu <= cpu_limit  (else 409)
       INSERT project (status=provisioning, namespace_name=<generated>)
       UPDATE team_quota SET cpu_used += required_cpu, ram_gb_used += required_ram
     COMMIT
  5. HelmProvisioner.provision(project):
       a. Add namespace entry to src/helm/values.yaml
       b. git add + git commit + git push → GitLab
       c. POST ArgoCD sync: ARGOCD_URL/api/v1/applications/{ARGOCD_APP_NAME}/sync
  6. Spawn asyncio background poller (10s interval, 5min timeout):
       GET ArgoCD app status
       Synced+Healthy  → UPDATE project status=active
       Timeout         → UPDATE project status=failed, ROLLBACK quota usage
```

namespace_name format: `<team_id>-<project_name>` (lowercased, alphanumeric + hyphens, max 63 chars).

### Allocation Invariant

Enforced in the **service layer** using `SELECT FOR UPDATE`:

```
Field level:  sum(dept.cpu_limit for field+site) ≤ sum(server.cpu allocated to field at site)
Dept level:   sum(team.cpu_limit for dept+site)  ≤ dept.cpu_limit for that site
```

Both CPU and RAM are checked. Violations raise `QuotaExceededError` (HTTP 409, code=`QUOTA_EXCEEDED`).

---

## Data Layer

### PostgreSQL Schema (key relationships)

```
centers
  └── fields (center_id FK)
        └── departments (field_id FK)
              └── teams (department_id FK)
                    └── projects (team_id FK)
                    └── team_quota_allocations (team_id FK)
              └── department_quota_allocations (department_id FK)
        └── field_server_allocations (field_id FK)
servers
  └── field_server_allocations (server_id UNIQUE FK)
```

All PKs are UUIDs generated by `gen_random_uuid()` (pgcrypto extension).

### Async SQLAlchemy

- `app/database.py`: `AsyncEngine`, `AsyncSessionLocal`, `get_db()` FastAPI dependency
- All queries use `await session.execute(...)` — no sync calls
- Multi-step writes use `async with session.begin()` for explicit transactions

---

## Cross-Cutting Concerns

| Concern | Approach |
|---------|---------|
| Authentication | JWT Bearer, validated in `get_current_user` FastAPI dependency |
| Authorization | Role + scope_id check in **service layer** (never in routers) |
| Logging | Structured JSON with `request_id` on every line |
| Error handling | `InfraHubError` hierarchy → global exception handler → `{error: {code, message, request_id}}` |
| Request tracing | UUID4 `request_id` per request via middleware, propagated via `contextvars` |
| Configuration | `AppSettings(BaseSettings)` — fails fast on missing required vars at startup |
| Secrets | Environment variables injected at runtime (Kubernetes Secrets) — never in code |
| DB migrations | Alembic incremental revisions only — never DDL in application code |
| Air-gap | No runtime HTTP calls except `EXTERNAL_SERVER_API_URL` + `ARGOCD_URL` from AppSettings |
| Token storage | Frontend: memory only (Zustand) — never localStorage/sessionStorage |

---

## Deployment Architecture

See `docs/context/deployment.md` for full details.

**Summary:**
```
GitLab MR merge → GitLab CI (test → build → push to registry) → ArgoCD syncs infrahub-system namespace
```
