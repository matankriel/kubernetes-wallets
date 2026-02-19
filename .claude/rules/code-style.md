# Code Style Rules

These rules apply to all code in InfraHub. Python (backend) and TypeScript (frontend).

## General Principles

- **Clarity over cleverness:** Write code the next developer understands in 30 seconds.
- **Minimal surface area:** Don't expose more than callers need.
- **Fail loudly:** Validate at boundaries; never silently swallow errors.
- **Consistent naming:** Always use the canonical domain names from `docs/context/conventions.md`.

## Formatting

- **Python:** `ruff format` (line length 100). Run: `cd src/backend && ruff check . --fix`
- **TypeScript:** Prettier. Run: `cd src/frontend && npm run lint`
- No trailing whitespace. Files end with a single newline.

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python variables / functions | `snake_case` | `team_id`, `allocate_server_to_field` |
| Python classes | `PascalCase` | `AllocationService`, `ServerRepository` |
| Python Pydantic models | `PascalCase` + `Request`/`Response` | `CreateProjectRequest`, `ServerResponse` |
| Python SQLAlchemy models | `PascalCase` singular | `FieldServerAllocation`, `TeamQuotaAllocation` |
| Python constants / env vars | `SCREAMING_SNAKE_CASE` | `MAX_NAMESPACE_LENGTH`, `DB_URL` |
| TypeScript variables / functions | `camelCase` | `teamId`, `cpuLimit` |
| TypeScript React components | `PascalCase` | `AllocationTree`, `ProjectWizard` |
| TypeScript types / interfaces | `PascalCase` | `Claims`, `ServerResponse` |
| Python files | `snake_case.py` | `allocation_service.py`, `server_repo.py` |
| TypeScript/React files | `PascalCase.tsx` (components), `camelCase.ts` (utils/stores/hooks) | `AllocationTree.tsx`, `useServers.ts` |

## InfraHub-Specific Rules

- **Never** use sync SQLAlchemy (`session.query(...)` without await). All DB is async.
- **Never** use `requests` library. Use `httpx.AsyncClient` only.
- **Never** make HTTP calls to URLs not in `AppSettings` at runtime (air-gap rule).
- **Never** store JWT tokens in `localStorage` or `sessionStorage` — memory only (Zustand).
- **Always** use canonical domain names: `center/field/department/team/project/site/quota/performance_tier`.
- **Always** enforce the allocation invariant with `SELECT FOR UPDATE` before any quota write.
- **Always** check `claims.role` and `claims.scope_id` in the **service layer**, never in routers.

## Functions & Methods

- Single responsibility: one function does one thing.
- Keep functions under 40 lines. Extract helpers if longer.
- Avoid more than 3 levels of nesting — use early-return or extract instead.
- Async functions: `async def` in Python, `async` arrow functions in TypeScript. No mixing.

## Error Handling

- **Python:** Raise typed `InfraHubError` subclasses in service/repository layers. Never `HTTPException` below the router layer.
- **TypeScript:** On 401 from API, clear Zustand auth store and redirect to `/login`.
- Never silently catch and discard errors.
- Never expose stack traces or internal DB errors in API responses.
- Always include `request_id` in error responses (set by middleware).

## Imports / Dependencies

- No unused imports.
- Python import order: stdlib → third-party → internal (with blank line between groups). `ruff` enforces this.
- TypeScript: external packages → internal modules → styles.
- Don't add a new dependency for something achievable in < 20 lines of code.
- All new Python deps go in `pyproject.toml [project.dependencies]`. Dev deps in `[project.optional-dependencies] dev`.

## Comments

- Don't comment *what* the code does — name it so it's obvious.
- Do comment *why* a non-obvious decision was made (especially around the allocation invariant or air-gap constraints).
- No dead code comments. Delete dead code.
