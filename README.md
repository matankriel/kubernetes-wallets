# InfraHub

Centralized, air-gapped, on-prem platform for managing Kubernetes namespaces and bare-metal servers across a large enterprise.

---

## What Is InfraHub?

InfraHub gives infrastructure teams a single place to:

- **Inventory** bare-metal servers (synced automatically from an internal API)
- **Allocate** servers and CPU/RAM quotas down an org hierarchy
- **Provision** Kubernetes namespaces (projects) via Helm + ArgoCD GitOps
- **Enforce** resource quotas at every level of the hierarchy

All operations happen entirely on-prem, air-gapped — no calls to cloud providers or the internet.

---

## Org Hierarchy

```
Center
  └── Field  (bare-metal servers live here)
        └── Department
              └── Team  (LDAP group)
                    └── Project  (Kubernetes namespace)
```

Resources flow down:
1. **Center admin** assigns servers to Fields
2. **Field admin** allocates CPU/RAM quotas to Departments (per site)
3. **Dept admin** allocates CPU/RAM quotas to Teams (per site)
4. **Team lead** creates Projects — each project becomes a Kubernetes namespace with a ResourceQuota

The allocation invariant is enforced at every step: `cpu_used + requested ≤ cpu_limit`.

---

## SLA Tiers

| SLA | Regular Servers | High-Performance Servers |
|-----|----------------|------------------------|
| bronze | 2 CPU / 4 Gi RAM | 4 CPU / 8 Gi RAM |
| silver | 4 CPU / 16 Gi RAM | 8 CPU / 32 Gi RAM |
| gold | 8 CPU / 32 Gi RAM | 16 CPU / 64 Gi RAM |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), asyncpg |
| Frontend | React 18, TypeScript, Vite, React Query, Zustand |
| Database | PostgreSQL |
| Auth | LDAP + JWT (HS256, 15-min expiry, no refresh) |
| GitOps | Helm + ArgoCD |
| CI/CD | GitLab CI |
| Runtime | Kubernetes (`infrahub-system` namespace) |

---

## Quick Start (Local Dev)

### Prerequisites

```bash
python >= 3.12    # pyenv recommended
node >= 20        # nvm recommended
docker            # for postgres + mock-ldap
docker-compose
```

### 1. Clone and configure

```bash
git clone <gitlab-repo-url>
cd infrahub
cp .env.example .env
# Edit .env — at minimum set DB_URL, JWT_SECRET, LDAP_* vars
```

### 2. Start the local stack

```bash
docker-compose up -d   # starts postgres + mock-ldap
```

### 3. Set up the backend

```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. Set up the frontend

```bash
cd src/frontend
npm ci
npm run dev   # starts on http://localhost:3000
```

### 5. Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"..."}

curl http://localhost:8000/health/ready
# → {"status":"ok"}
```

---

## Running Tests

```bash
# Backend
cd src/backend && pytest -x --tb=short

# Frontend
cd src/frontend && npm test
```

---

## RBAC / Roles

| LDAP Group CN | Role | Scope |
|--------------|------|-------|
| `infrahub-center-admins` | `center_admin` | global |
| `infrahub-field-admins-<field_id>` | `field_admin` | field |
| `infrahub-dept-admins-<dept_id>` | `dept_admin` | department |
| `infrahub-team-leads-<team_id>` | `team_lead` | team |

---

## Project Structure

```
src/
├── backend/          # Python FastAPI backend
│   ├── pyproject.toml
│   ├── alembic/      # DB migrations
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── models/   # SQLAlchemy ORM
│       ├── schemas/  # Pydantic schemas
│       ├── repositories/
│       ├── services/ # Business logic + allocation invariant
│       ├── routers/  # FastAPI APIRouter
│       ├── auth/     # LDAP client, JWT
│       ├── helm/     # HelmProvisioner
│       └── sync/     # Background server sync
├── frontend/         # React + TypeScript
│   ├── package.json
│   └── src/
│       ├── api/      # Typed fetch wrappers
│       ├── store/    # Zustand auth store (memory only)
│       ├── hooks/    # React Query hooks
│       ├── components/
│       └── pages/
└── helm/             # Managed Helm chart (namespaces + ResourceQuotas)
    ├── Chart.yaml
    ├── values.yaml
    └── templates/

ralph/
├── run.sh            # Autonomous story loop
├── prd.json          # Story backlog
└── prompt.md         # Ralph's system prompt

docs/context/         # Architecture, conventions, testing, deployment docs
.gitlab-ci.yml        # GitLab CI pipeline
docker-compose.yml    # Local dev stack
.env.example          # All required environment variables
```

---

## API Overview

```
POST  /api/v1/auth/login
GET   /health
GET   /health/ready

GET   /api/v1/servers
GET   /api/v1/servers/:id
POST  /api/v1/admin/sync/servers

GET   /api/v1/allocations/tree
POST  /api/v1/allocations/servers
DELETE /api/v1/allocations/servers/:id
POST  /api/v1/allocations/servers/swap
POST  /api/v1/allocations/department-quota
PUT   /api/v1/allocations/department-quota/:id
POST  /api/v1/allocations/team-quota
PUT   /api/v1/allocations/team-quota/:id

GET   /api/v1/projects
GET   /api/v1/projects/:id
POST  /api/v1/projects
DELETE /api/v1/projects/:id

GET   /api/v1/calculator/cpu-conversion
POST  /api/v1/calculator/convert

GET   /api/v1/org/centers|fields|departments|teams
```

Full API docs available at `http://localhost:8000/docs` when running locally.

---

## Development

See [`docs/context/onboarding.md`](docs/context/onboarding.md) for a full contributor guide.

Key conventions are in [`docs/context/conventions.md`](docs/context/conventions.md).

Use [`CLAUDE.md`](CLAUDE.md) as the entry point when working with Claude Code.
