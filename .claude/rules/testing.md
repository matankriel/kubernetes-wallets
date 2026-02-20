---
pathScopes:
  - "src/**"
---

# Testing Rules

These rules apply to all code under `src/`.

## Test Coverage Requirements

- **New features:** must ship with tests. No exceptions.
- **Bug fixes:** must include a regression test that would have caught the bug.
- **Refactors:** existing tests must still pass; add tests if coverage drops.
- Target: 80% line coverage minimum. Critical paths (auth, allocation invariant, project provisioning) require 95%.

## Test Structure

Follow the **Arrange → Act → Assert** (AAA) pattern:

```python
# Python example
async def test_quota_exceeded_raises_409():
    # Arrange
    quota = TeamQuotaAllocation(cpu_limit=4, cpu_used=3)

    # Act / Assert
    with pytest.raises(QuotaExceededError, match="insufficient CPU quota"):
        await service.check_and_reserve_quota(claims, quota, required_cpu=2)
```

- One logical assertion per test.
- Test names: `test_<unit>_<action>_<expected_outcome>` — e.g., `test_allocate_server_raises_forbidden_for_field_admin`.

## Test Types & Locations

| Type | Location | When to write |
|------|----------|--------------|
| Unit (backend) | `src/backend/tests/test_*.py` | Every service method, every repo method |
| Unit (frontend) | `src/frontend/src/**/__tests__/*.test.tsx` | Every component, every store |
| Integration (backend) | `src/backend/tests/integration/test_*.py` | DB queries with testcontainers |
| E2E | (future) | Critical user journeys |

## Running Tests

```bash
# Backend unit tests
cd src/backend && pytest -x --tb=short

# Backend with coverage
cd src/backend && pytest --cov=app --cov-report=term-missing

# Specific test
cd src/backend && pytest -k "test_quota_exceeded"

# Integration tests (requires Docker)
cd src/backend && pytest -m integration

# Frontend tests
cd src/frontend && npm test

# Frontend with coverage
cd src/frontend && npm run test:coverage
```

## What to Test

- **Happy path:** the expected use case works end-to-end.
- **Quota boundary:** `cpu_used + requested == cpu_limit` (allowed) and `+1` (rejected).
- **RBAC:** wrong role → `ForbiddenError`; wrong `scope_id` → `ForbiddenError`.
- **Failure paths:** LDAP bind failure, ArgoCD timeout, external API unreachable.
- **Idempotency:** server sync run twice with same data → same DB state.

## What NOT to Test

- Implementation details (which SQL query was run internally).
- Framework code you didn't write (FastAPI routing, SQLAlchemy internals).
- Type annotations (Python type checker handles this).

## InfraHub-Specific Test Doubles

```python
# Use MockLDAPClient for all auth tests
class MockLDAPClient:
    def __init__(self, groups: list[str], should_fail: bool = False): ...
    async def authenticate(self, username: str, password: str) -> list[str]: ...

# Use MockHelmProvisioner for project provisioning tests
class MockHelmProvisioner:
    def __init__(self, should_fail: bool = False): ...
    async def provision(self, project) -> None: ...
```

- Never make real LDAP calls in tests.
- Never make real ArgoCD or Git calls in tests.
- Never call `EXTERNAL_SERVER_API_URL` in tests — mock with `httpx` respx or `unittest.mock`.
- Use `testcontainers[postgres]` for integration tests that need a real DB.

## Test Doubles Priority

- Prefer **fakes** (in-memory implementations) over **mocks** for complex collaborators.
- Use **mocks** only for external I/O (LDAP, ArgoCD, external server API, Git).
- Never mock the module under test.
- Reset all mocks in `pytest` fixtures with `scope="function"` (default).

## Pytest Configuration

In `src/backend/pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["integration: requires Docker + testcontainers (deselect with -m 'not integration')"]
```
