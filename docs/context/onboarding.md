# Onboarding

> Everything a new contributor needs to get productive on InfraHub.

---

## Prerequisites

Install these tools before starting:

```bash
# Required
python >= 3.12     # Check: python --version  (use pyenv: pyenv install 3.12)
node >= 20.0.0     # Check: node --version    (use nvm: nvm install 20)
docker             # For local postgres + mock-ldap
docker-compose     # Check: docker-compose --version
git >= 2.40.0      # Check: git --version
glab               # GitLab CLI: https://gitlab.com/gitlab-org/cli

# Recommended
claude             # Claude Code CLI: npm install -g @anthropic/claude-code
jq                 # JSON processor (used by Ralph): brew install jq
```

**Note:** This project is air-gapped. All tool installations must be done from internal mirrors or pre-installed base images. Confirm available packages with your platform team.

---

## First-Time Setup

```bash
# 1. Clone the repository (internal GitLab)
git clone git@gitlab.internal:<group>/infrahub.git
cd infrahub

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — see "Local Dev Configuration" below

# 3. Start local infrastructure (postgres + mock-ldap)
docker-compose up -d

# 4. Set up the Python backend
cd src/backend
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head           # Run DB migrations

# 5. Verify backend starts
uvicorn app.main:app --reload --port 8000 &
curl http://localhost:8000/health
# → {"status":"ok","version":"..."}
curl http://localhost:8000/health/ready
# → {"status":"ok"}

# 6. Set up the React frontend
cd ../frontend
npm ci
npm run dev    # Starts on http://localhost:3000

# 7. Run all tests
cd ../backend && pytest -x --tb=short
cd ../frontend && npm test
```

---

## Local Dev Configuration (.env)

Minimum required values for local dev (docker-compose provides postgres and mock-ldap):

```bash
# Database — postgres started by docker-compose
DB_URL=postgresql+asyncpg://infrahub:infrahub@localhost:5432/infrahub

# LDAP — mock-ldap started by docker-compose
LDAP_HOST=localhost
LDAP_PORT=389
LDAP_USE_SSL=false
LDAP_BIND_DN=cn=infrahub-svc,ou=service-accounts,dc=corp,dc=local
LDAP_BIND_PASSWORD=devpassword
LDAP_BASE_DN=dc=corp,dc=local

# Auth
JWT_SECRET=dev-secret-change-in-production-min-32-chars

# ArgoCD — set to a local mock or skip (sync will fail gracefully in dev)
ARGOCD_URL=http://localhost:8001
ARGOCD_TOKEN=dev-token
ARGOCD_APP_NAME=infrahub-namespaces

# External server API — set to a local mock
EXTERNAL_SERVER_API_URL=http://localhost:8002/servers
EXTERNAL_API_TIMEOUT_SECONDS=5
SYNC_INTERVAL_MINUTES=60

# Helm chart repo — point to a local clone
HELM_GIT_REPO_PATH=/tmp/infrahub-helm

# Thresholds
PERFORMANCE_TIER_CPU_THRESHOLD=64
CPU_HP_TO_REGULAR_RATIO=2.0
```

---

## LDAP Test Credentials (mock-ldap in docker-compose)

The local mock-ldap is pre-seeded with these test users:

| Username | Password | Role | Scope |
|----------|----------|------|-------|
| `admin` | `admin` | `center_admin` | global |
| `field-berlin` | `password` | `field_admin` | Field-Berlin ID |
| `dept-eng` | `password` | `dept_admin` | Engineering dept ID |
| `team-platform` | `password` | `team_lead` | Platform team ID |

These exist only in the local mock-ldap (defined in `docker-compose.yml`). Production LDAP credentials come from your team lead.

---

## Repository Tour

| Path | What it is |
|------|-----------|
| `CLAUDE.md` | Start here. Claude Code navigation hub. |
| `src/backend/` | Python FastAPI backend |
| `src/backend/pyproject.toml` | Python deps + dev tools config |
| `src/backend/alembic/` | DB migrations |
| `src/backend/app/main.py` | FastAPI app factory |
| `src/backend/app/config.py` | AppSettings — all env vars |
| `src/backend/app/models/` | SQLAlchemy ORM models |
| `src/backend/app/services/` | Business logic (allocation invariant enforced here) |
| `src/backend/app/repositories/` | DB access layer |
| `src/backend/app/routers/` | FastAPI APIRouter definitions |
| `src/backend/app/auth/` | LDAP client + JWT |
| `src/backend/app/helm/` | HelmProvisioner (namespace GitOps) |
| `src/backend/app/sync/` | Background server sync |
| `src/frontend/` | React 18 + TypeScript frontend |
| `src/frontend/src/api/` | Typed fetch wrappers |
| `src/frontend/src/store/` | Zustand auth store |
| `src/frontend/src/components/` | React components |
| `src/frontend/src/pages/` | Top-level page components |
| `src/helm/` | Managed Helm chart (namespace provisioning) |
| `docs/context/` | Architecture, conventions, testing, deployment docs |
| `.claude/` | Claude Code configuration (agents, skills, rules) |
| `ralph/` | Autonomous story implementation pipeline |
| `.env.example` | All required environment variables with descriptions |
| `.gitlab-ci.yml` | GitLab CI pipeline |

---

## Common Tasks

### Run the dev stack
```bash
docker-compose up -d                    # postgres + mock-ldap
cd src/backend && uvicorn app.main:app --reload --port 8000
cd src/frontend && npm run dev          # http://localhost:3000
```

### Run tests
```bash
cd src/backend && pytest -x --tb=short    # Backend unit tests
cd src/frontend && npm test               # Frontend unit tests
```

### Apply DB migrations
```bash
cd src/backend && alembic upgrade head
```

### Create a new migration
```bash
cd src/backend && alembic revision --autogenerate -m "add_column_to_projects"
# Review the generated file in alembic/versions/ before applying
```

### Make a code change
```bash
git checkout -b feat/my-feature
# ... make changes ...
# In Claude Code:
/commit    # Lint, test, and commit
/ship      # Commit, push, and open MR
```

### Get a code review
```bash
# In Claude Code:
/review-pr 42    # Review MR #42
# Or: "Use the code-reviewer agent to review my changes"
```

### Add a story for Ralph
```bash
# Manually edit ralph/prd.json
# Or in Claude Code:
/create-story "Add rate limiting to the server sync endpoint"
```

### Run Ralph autonomously
```bash
bash ralph/run.sh --once       # Implement the next pending story
bash ralph/run.sh              # Loop through all pending stories
bash ralph/run.sh --dry-run    # Preview without running
```

---

## Key Conventions

- **Branches:** `feat/`, `fix/`, `chore/` prefixes. Never push directly to `main`.
- **Commits:** Conventional commits format — use `/commit` skill.
- **MRs:** Must have a description. Must pass CI. Must have 1 approval.
- **Tests:** All new code needs tests. The `/ship` skill enforces this.
- **Domain names:** Use the canonical names table in `docs/context/conventions.md` — never deviate.
- **Async:** All Python DB access is async — never use sync SQLAlchemy.
- **Air-gap:** Never call external URLs at runtime except `EXTERNAL_SERVER_API_URL` and `ARGOCD_URL`.
- **Tokens:** Frontend token is stored in memory (Zustand) only — never localStorage.

---

## Useful Claude Code Commands

```
/commit                   Stage and commit with conventional format
/ship                     Lint → test → commit → push → MR
/review-pr [number]       Review an MR
/create-story [desc]      Add a story to ralph/prd.json
/standup                  Generate a standup from recent git activity
```

---

## Getting Help

- **Architecture questions:** `docs/context/architecture.md`
- **Conventions questions:** `docs/context/conventions.md`
- **Stuck on a bug?** `"Use the debugger agent to help me with [problem]"`
- **Team chat:** `#infrahub-dev` on internal Slack/Teams
- **On-call:** `#infrahub-alerts`
