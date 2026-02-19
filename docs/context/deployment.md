# Deployment

> On-prem Kubernetes deployment, GitLab CI pipeline, ArgoCD GitOps, and runbooks for InfraHub.

---

## Environments

| Environment | Purpose | URL | Deploy trigger |
|-------------|---------|-----|----------------|
| `local` | Development | `localhost:8000` (API), `localhost:3000` (UI) | `docker-compose up` |
| `staging` | Integration testing | `infrahub-staging.internal` | Auto on merge to `main` |
| `production` | Live | `infrahub.internal` | Manual ArgoCD promotion |

All environments are on-prem, air-gapped. No cloud provider access.

---

## CI/CD Pipeline (GitLab CI)

```
Push to feature branch
        │
        ▼
  GitLab CI: test stage
  ├── test-backend  (python:3.12 image, pytest)
  └── test-frontend (node:20 image, vitest)
        │
        ▼ (on MR approval + CI pass → merge to main)
  GitLab CI: build stage
  ├── docker build backend → push to internal registry
  └── docker build frontend → push to internal registry
        │
        ▼
  GitLab CI: deploy-staging stage
  ├── argocd app set infrahub-system --helm-set backend.image.tag=$CI_COMMIT_SHA
  └── argocd app sync infrahub-system --timeout 120
        │
        ▼ (manual ArgoCD promotion)
  Deploy to production
  ├── argocd app sync infrahub-production --timeout 120
  └── Health checks pass
```

`.gitlab-ci.yml` excerpt:

```yaml
stages: [test, build, deploy]

test-backend:
  stage: test
  image: python:3.12
  script:
    - cd src/backend && pip install -e ".[dev]" && pytest -x --tb=short

test-frontend:
  stage: test
  image: node:20
  script:
    - cd src/frontend && npm ci && npm test

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA src/backend/
    - docker build -t $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA src/frontend/
    - docker push $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA
  only: [main]

deploy-staging:
  stage: deploy
  script:
    - argocd app set infrahub-system
        --helm-set backend.image.tag=$CI_COMMIT_SHA
        --helm-set frontend.image.tag=$CI_COMMIT_SHA
    - argocd app sync infrahub-system --timeout 120
  only: [main]
```

---

## Kubernetes Deployment

InfraHub runs in the `infrahub-system` namespace on the managed cluster.

```
infrahub-system/
  ├── backend    Deployment (FastAPI + uvicorn)
  ├── frontend   Deployment (nginx serving built React app)
  ├── postgres   StatefulSet (persistent volume)
  └── secrets    DB_URL, JWT_SECRET, LDAP_BIND_PASSWORD, ARGOCD_TOKEN
```

ArgoCD manages `infrahub-system` from the Helm chart in `src/helm/` (for InfraHub's own deployment) and `infrahub-namespaces` (the managed chart that provisions project namespaces).

---

## Helm Chart Structure (Namespace Provisioning)

```
src/helm/
├── Chart.yaml
├── values.yaml          # Updated by HelmProvisioner on each project create
└── templates/
    ├── namespace.yaml         # Kubernetes Namespace
    ├── resource-quota.yaml    # ResourceQuota
    └── role-binding.yaml      # RoleBinding (team LDAP group → namespace)
```

`values.yaml` format (managed programmatically by `HelmProvisioner`):

```yaml
namespaces:
  - name: platform-team-payments
    teamId: "uuid..."
    resourceQuota:
      cpu: "4"
      memory: "16Gi"
  - name: data-team-analytics
    teamId: "uuid..."
    resourceQuota:
      cpu: "8"
      memory: "32Gi"
```

**Never** edit `values.yaml` manually in production — it is owned by the `HelmProvisioner`.

---

## Health Checks

```bash
# Backend health (unauthenticated)
curl http://infrahub.internal/health
# → {"status":"ok","version":"1.2.3"}

# Backend readiness (DB connected)
curl http://infrahub.internal/health/ready
# → {"status":"ok"}   or   {"status":"unavailable","detail":"..."}
```

Kubernetes liveness probe: `GET /health`
Kubernetes readiness probe: `GET /health/ready`

---

## Rollback

### Application rollback (ArgoCD)

```bash
# List recent syncs
argocd app history infrahub-system

# Roll back to a previous revision
argocd app rollback infrahub-system <revision-id>

# Or pin to a specific image tag
argocd app set infrahub-system --helm-set backend.image.tag=<previous-sha>
argocd app sync infrahub-system
```

### Database rollback (Alembic)

```bash
# Check current revision
cd src/backend && alembic current

# Roll back one step
cd src/backend && alembic downgrade -1

# Roll back to specific revision
cd src/backend && alembic downgrade 0003_servers
```

**Important:** Alembic migrations must be backwards-compatible — the old app version must run against the new schema, and vice versa. Never drop a column in the same migration that removes it from the ORM model.

---

## Database Migrations in CI/CD

Migrations run automatically on deploy **before** new pods start serving traffic:

1. A Kubernetes Job (`alembic upgrade head`) runs in the `infrahub-system` namespace
2. The Job completes successfully before the `backend` Deployment rollout begins
3. If the migration Job fails, the deploy is blocked and the old version keeps running

---

## Secrets Management

Secrets are stored in Kubernetes Secrets (on-prem cluster), injected as environment variables:

| Secret | Kubernetes Secret Name | Key |
|--------|----------------------|-----|
| Database URL | `infrahub-db` | `DB_URL` |
| JWT secret | `infrahub-jwt` | `JWT_SECRET` |
| LDAP bind password | `infrahub-ldap` | `LDAP_BIND_PASSWORD` |
| ArgoCD token | `infrahub-argocd` | `ARGOCD_TOKEN` |

**Never** commit secrets to Git. **Never** hardcode them in `AppSettings` defaults.

```bash
# Create/update a secret (kubectl)
kubectl create secret generic infrahub-jwt \
  --from-literal=JWT_SECRET="$(openssl rand -hex 32)" \
  -n infrahub-system \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## Environment Variables (full list)

See `.env.example` for the authoritative list with descriptions. Key variables:

```bash
# Database
DB_URL=postgresql+asyncpg://infrahub:password@postgres:5432/infrahub

# LDAP
LDAP_HOST=ldap.internal
LDAP_PORT=636
LDAP_USE_SSL=true
LDAP_BIND_DN=cn=infrahub-svc,ou=service-accounts,dc=corp,dc=local
LDAP_BIND_PASSWORD=<from secret>
LDAP_BASE_DN=dc=corp,dc=local

# Auth
JWT_SECRET=<from secret>

# ArgoCD
ARGOCD_URL=https://argocd.internal
ARGOCD_TOKEN=<from secret>
ARGOCD_APP_NAME=infrahub-namespaces

# External server inventory
EXTERNAL_SERVER_API_URL=https://baremetal-api.internal
EXTERNAL_API_TIMEOUT_SECONDS=30
SYNC_INTERVAL_MINUTES=60

# Helm chart git repo (mounted in container)
HELM_GIT_REPO_PATH=/app/helm-repo

# Performance tier classification
PERFORMANCE_TIER_CPU_THRESHOLD=64

# CPU calculator
CPU_HP_TO_REGULAR_RATIO=2.0
```

---

## Monitoring & Alerting

| Signal | Tool | Threshold |
|--------|------|-----------|
| Error rate | Internal Prometheus + Grafana | > 1% for 5 min → PagerDuty |
| p99 latency | Prometheus | > 2s for 5 min → Slack |
| Failed deploys | GitLab CI notifications | Any failure → Slack `#infrahub-alerts` |
| ArgoCD sync errors | ArgoCD notifications | Any → Slack `#infrahub-alerts` |

---

## On-Call Runbook

1. Check `#infrahub-alerts` for alert details
2. `curl https://infrahub.internal/health/ready` — check DB connectivity
3. `argocd app get infrahub-system` — check ArgoCD sync status
4. Check recent GitLab CI pipeline runs for deploy failures
5. If needed, roll back (see Rollback section above)
6. Post incident summary in `#infrahub-incidents` after resolution
