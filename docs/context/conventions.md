# Conventions

> Coding conventions for InfraHub. All contributors (human and AI) must follow these.

---

## Canonical Domain Names (never deviate)

| Concept | Correct Name | Never Use |
|---------|-------------|-----------|
| Org root | `center` | org, tenant, root |
| Level 2 | `field` | region, division |
| Level 3 | `department` | dept, unit |
| Level 4 | `team` | group, squad |
| K8s namespace | `project` | namespace (in domain layer) |
| Geographic zone | `site` | zone, region, location |
| CPU/RAM budget | `quota` | limit, budget, capacity |
| Server category | `performance_tier` (`regular` / `high_performance`) | tier, class |
| Server quality high | `high_performance` | hpc, hp (in domain) |
| SLA levels | `bronze` / `silver` / `gold` | small/medium/large, tier1/2/3 |

---

## File & Directory Naming

| Context | Convention | Example |
|---------|-----------|---------|
| Python files | `snake_case.py` | `allocation_service.py`, `server_repo.py` |
| Python test files | `test_<module>.py` | `test_allocation_service.py` |
| TypeScript/React files | `PascalCase.tsx` (components), `camelCase.ts` (utils/hooks/stores) | `AllocationTree.tsx`, `useServers.ts` |
| Directories | `snake_case` (Python), `kebab-case` (frontend) | `repositories/`, `allocation/` |

---

## Python Naming

| Context | Convention | Example |
|---------|-----------|---------|
| Variables | `snake_case` | `team_id`, `cpu_limit` |
| Functions | `snake_case` | `allocate_server_to_field`, `get_team_quota` |
| Classes | `PascalCase` | `AllocationService`, `ServerRepository` |
| Pydantic models | `PascalCase` + `Request`/`Response` suffix | `CreateProjectRequest`, `ServerResponse` |
| SQLAlchemy models | `PascalCase` (singular) | `Center`, `FieldServerAllocation` |
| Constants | `SCREAMING_SNAKE_CASE` | `DEFAULT_PAGE_SIZE`, `MAX_NAMESPACE_LENGTH` |
| Enum members | `SCREAMING_SNAKE_CASE` | `PerformanceTier.HIGH_PERFORMANCE`, `SlaType.GOLD` |
| Boolean variables | `is_`/`has_`/`can_` prefix | `is_active`, `has_quota` |
| Async functions | no special suffix needed | `fetch_servers`, not `fetch_servers_async` |

---

## TypeScript/React Naming

| Context | Convention | Example |
|---------|-----------|---------|
| Variables | `camelCase` | `teamId`, `cpuLimit` |
| Functions | `camelCase` | `allocateServer`, `getTeamQuota` |
| React components | `PascalCase` | `AllocationTree`, `ProjectWizard` |
| Types/Interfaces | `PascalCase` | `ServerResponse`, `Claims` |
| Custom hooks | `use` prefix | `useServers`, `useAllocationTree` |
| Zustand stores | `use` prefix | `useAuthStore` |
| Constants | `SCREAMING_SNAKE_CASE` | `DEFAULT_PAGE_SIZE` |
| Event handlers | `handle` prefix | `handleSubmit`, `handleLoginError` |

---

## Project Structure Conventions

### Backend: Route Organization

One router per domain, mounted at `/api/v1/<domain>`:

```
app/routers/
  auth.py        # POST /api/v1/auth/login
  health.py      # GET /health, GET /health/ready  (no /api/v1 prefix)
  servers.py     # GET /api/v1/servers, etc.
  allocations.py # GET/POST /api/v1/allocations/*
  projects.py    # GET/POST/DELETE /api/v1/projects/*
  calculator.py  # GET/POST /api/v1/calculator/*
```

### Backend: Service Layer

Services contain **business logic and RBAC enforcement only**:
- Receive plain Python objects (domain entities or validated Pydantic inputs), not `Request`/`Response`
- Raise domain errors (`QuotaExceededError`, `ForbiddenError`), never `HTTPException`
- Never access `request.headers` or anything HTTP-specific
- Always accept `claims: Claims` as first argument for authenticated operations
- Check `claims.role` and `claims.scope_id` — raise `ForbiddenError` if mismatch

```python
# Good
async def allocate_server(self, claims: Claims, server_id: UUID, field_id: UUID) -> FieldServerAllocation:
    if claims.role != Role.CENTER_ADMIN:
        raise ForbiddenError("only center_admin can assign servers to fields")
    ...

# Bad — don't check roles in routers
@router.post("/allocations/servers")
async def assign_server(body: AssignServerRequest, claims: Claims = Depends(get_current_user)):
    if claims.role != "center_admin":  # WRONG: role check belongs in service
        raise HTTPException(status_code=403)
```

### Backend: Repository Pattern

All database access goes through repositories:
- One repository class per primary domain table / aggregate root
- Methods accept plain Python objects and return SQLAlchemy model instances or domain objects
- Repositories never raise `HTTPException` — only database exceptions propagate
- Quota row reads that will be followed by a write use `SELECT ... FOR UPDATE`:

```python
# In repository (correct)
async def get_team_quota_for_update(self, team_id: UUID, site: str) -> TeamQuotaAllocation:
    result = await self.session.execute(
        select(TeamQuotaAllocation)
        .where(TeamQuotaAllocation.team_id == team_id, TeamQuotaAllocation.site == site)
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"No quota found for team {team_id} at site {site}")
    return row
```

### Frontend: File Organization

```
src/frontend/src/
  api/          # Typed fetch wrappers — one file per domain
  store/        # Zustand stores (auth.ts only — no localStorage)
  hooks/        # React Query hooks — one file per domain
  components/   # Reusable components organized by domain
  pages/        # Top-level route components
```

---

## Error Handling Convention

### Error Hierarchy (Python)

```python
InfraHubError(Exception)
├── NotFoundError          → 404
├── UnauthorizedError      → 401  (code: UNAUTHORIZED)
├── ForbiddenError         → 403  (code: FORBIDDEN)
├── QuotaExceededError     → 409  (code: QUOTA_EXCEEDED)
├── ConflictError          → 409  (code: CONFLICT)
└── ValidationError        → 422  (code: VALIDATION_ERROR)
```

### Error Response Format (API)

```json
{
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "Team 'platform-team' at site 'berlin' has insufficient CPU quota. Requested: 8, Available: 4.",
    "request_id": "req_3f7a..."
  }
}
```

Rules:
- Services raise typed errors with descriptive messages
- Routers never catch domain errors — the global handler does
- Never return stack traces to clients
- Always include `request_id` (set by request middleware, retrieved via `contextvars`)

---

## API Response Conventions

### Success responses

```json
{
  "data": { ... }
}
```

### Paginated responses

```json
{
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 143,
    "has_next_page": true
  }
}
```

### Default pagination

`page=1`, `page_size=50`, max `page_size=200`.

---

## Async Rules (Python)

- **All** SQLAlchemy calls are async (`await session.execute(...)`)
- **Never** use synchronous SQLAlchemy (`session.query(...)`, `.all()` without await)
- **Never** use `requests` — use `httpx.AsyncClient`
- Background tasks use `asyncio.create_task()` or APScheduler `AsyncIOScheduler`

---

## Security Rules

- **Never** store credentials, tokens, or secrets in code or config files
- **Never** use `eval()`, `exec()`, or `subprocess` with user-controlled input
- **Never** construct SQL strings with f-strings — use SQLAlchemy parameterized queries
- **Never** expose internal error details (stack traces, DB errors) in API responses
- **Always** validate JWT in `get_current_user` dependency before any protected route handler runs
- **Always** check `claims.scope_id` in service layer for scoped roles (field_admin, dept_admin, team_lead)

---

## Environment Variable Conventions

- All env vars use `SCREAMING_SNAKE_CASE`
- All env vars are documented in `.env.example` with descriptions and example values
- `AppSettings(BaseSettings)` fails fast on startup if required vars are missing
- Naming: `<SERVICE>_<SETTING>` (e.g., `LDAP_HOST`, `ARGOCD_URL`, `DB_URL`)

---

## Date & Time

- Store timestamps as UTC (`TIMESTAMPTZ`) in PostgreSQL
- Transmit timestamps as ISO 8601 strings: `"2024-01-15T10:30:00Z"`
- Use Python `datetime.now(timezone.utc)` — never `datetime.utcnow()` (deprecated)
- Frontend: use `Intl.DateTimeFormat` for display — never manual string parsing

---

## Logging Conventions

Every log line must include:
- `level`: `debug` | `info` | `warn` | `error`
- `request_id`: trace ID for the current request (from `contextvars`)
- `message`: human-readable description
- Relevant context fields (`team_id`, `server_id`, etc.)

```json
{
  "level": "error",
  "request_id": "req_3f7a...",
  "team_id": "uuid...",
  "message": "Quota exceeded when creating project",
  "requested_cpu": 8,
  "available_cpu": 4
}
```

Never log: passwords, LDAP bind passwords, JWT secrets, JWT tokens.
