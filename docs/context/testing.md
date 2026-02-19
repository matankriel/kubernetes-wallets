# Testing

> Testing strategy, standards, and tooling for InfraHub.

## Test Pyramid

```
         ▲
        /E2E\          Few — test critical user flows end-to-end
       /──────\        (login → allocate → create project)
      /Integr. \       Some — test DB queries with real Postgres
     /──────────\      (testcontainers, skip in CI without DB)
    /    Unit    \     Many, fast, fully mocked
   ──────────────────  (services, repositories, auth logic)
```

**Target ratio:** ~70% unit, ~20% integration, ~10% E2E

---

## Backend Test Tooling

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support (`asyncio_mode = "auto"`) |
| `pytest-cov` | Coverage reporting |
| `httpx` | Async HTTP client for `TestClient` |
| `testcontainers[postgres]` | Real Postgres container for integration tests |

### Running Tests

```bash
# All backend tests
cd src/backend && pytest -x --tb=short

# With coverage
cd src/backend && pytest --cov=app --cov-report=term-missing

# Specific file
cd src/backend && pytest tests/test_allocation_service.py

# Specific test
cd src/backend && pytest -k "test_quota_exceeded"

# Integration tests only (requires Docker)
cd src/backend && pytest -m integration
```

---

## Frontend Test Tooling

| Tool | Purpose |
|------|---------|
| `vitest` | Test runner (Vite-native) |
| `@testing-library/react` | Component testing |
| `@testing-library/user-event` | User interaction simulation |
| `msw` | Mock Service Worker for API mocking in component tests |

### Running Tests

```bash
# All frontend tests
cd src/frontend && npm test

# Watch mode
cd src/frontend && npm run test:watch

# With coverage
cd src/frontend && npm run test:coverage
```

---

## Coverage Thresholds

| Scope | Line | Branch |
|-------|------|--------|
| `app/services/` | 95% | 90% |
| `app/repositories/` | 90% | 85% |
| `app/routers/` | 85% | 80% |
| Global backend | 80% | 75% |

CI fails if coverage drops below thresholds.

---

## Backend Unit Test Pattern

```python
# tests/test_allocation_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.allocation_service import AllocationService
from app.auth.jwt import Claims
from app.errors import QuotaExceededError, ForbiddenError


@pytest.fixture
def claims_center_admin():
    return Claims(sub="alice", role="center_admin", scope_id=None, exp=9999999999)


@pytest.fixture
def mock_allocation_repo():
    repo = MagicMock()
    repo.get_team_quota_for_update = AsyncMock()
    repo.update_team_quota = AsyncMock()
    return repo


@pytest.fixture
def allocation_service(mock_allocation_repo):
    return AllocationService(repo=mock_allocation_repo)


class TestAllocateServerToField:
    async def test_success(self, allocation_service, claims_center_admin):
        server_id = uuid4()
        field_id = uuid4()
        # Arrange
        allocation_service.repo.get_server = AsyncMock(return_value=MagicMock(id=server_id))
        allocation_service.repo.create_field_allocation = AsyncMock(
            return_value=MagicMock(id=uuid4(), server_id=server_id, field_id=field_id)
        )

        # Act
        result = await allocation_service.allocate_server_to_field(
            claims_center_admin, server_id=server_id, field_id=field_id
        )

        # Assert
        assert result.server_id == server_id
        allocation_service.repo.create_field_allocation.assert_awaited_once()

    async def test_forbidden_for_non_center_admin(self, allocation_service):
        claims = Claims(sub="bob", role="field_admin", scope_id=str(uuid4()), exp=9999999999)
        with pytest.raises(ForbiddenError):
            await allocation_service.allocate_server_to_field(claims, uuid4(), uuid4())


class TestCreateProject:
    async def test_quota_exceeded_raises_409(self, allocation_service, mock_allocation_repo):
        claims = Claims(sub="alice", role="team_lead", scope_id=str(uuid4()), exp=9999999999)
        mock_allocation_repo.get_team_quota_for_update.return_value = MagicMock(
            cpu_limit=4, cpu_used=3, ram_gb_limit=16, ram_gb_used=12
        )
        # bronze/regular requires 2 CPU — 3+2 > 4 → QuotaExceededError
        with pytest.raises(QuotaExceededError, match="insufficient CPU quota"):
            await allocation_service.check_and_reserve_quota(
                claims, site="berlin", sla_type="bronze", performance_tier="regular"
            )
```

---

## Backend Integration Test Pattern (testcontainers)

```python
# tests/integration/test_server_repo.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.repositories.server_repo import ServerRepository


@pytest.fixture(scope="module")
async def pg_session():
    with PostgresContainer("postgres:16") as pg:
        engine = create_async_engine(pg.get_connection_url().replace("postgresql://", "postgresql+asyncpg://"))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            yield session
        await engine.dispose()


@pytest.mark.integration
async def test_upsert_server_is_idempotent(pg_session):
    repo = ServerRepository(pg_session)
    server_data = {
        "name": "srv-001", "vendor": "Dell", "site": "berlin",
        "deployment_cluster": "cluster-a", "cpu": 32, "ram_gb": 128,
        "serial_number": "SN001", "product": "PowerEdge R750",
        "performance_tier": "regular", "status": "active",
    }

    # First upsert
    await repo.upsert_from_external([server_data])
    # Second upsert (same data)
    await repo.upsert_from_external([server_data])

    servers = await repo.list_servers()
    # Should only be one server, not two
    assert len([s for s in servers if s.name == "srv-001"]) == 1
```

Mark integration tests with `@pytest.mark.integration`. In CI without Docker, these are skipped.

Pytest config in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["integration: requires Docker + testcontainers"]
```

---

## Frontend Unit Test Pattern

```typescript
// src/frontend/src/store/__tests__/auth.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAuthStore } from '../auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, claims: null })
  })

  it('stores token and claims on set', () => {
    const { result } = renderHook(() => useAuthStore())
    act(() => {
      result.current.setAuth('my.jwt.token', {
        sub: 'alice', role: 'center_admin', scope_id: null, exp: 9999999999
      })
    })
    expect(result.current.token).toBe('my.jwt.token')
    expect(result.current.claims?.role).toBe('center_admin')
  })

  it('clears token and claims on logout', () => {
    const { result } = renderHook(() => useAuthStore())
    act(() => {
      result.current.setAuth('token', { sub: 'a', role: 'team_lead', scope_id: 'x', exp: 1 })
      result.current.clearAuth()
    })
    expect(result.current.token).toBeNull()
    expect(result.current.claims).toBeNull()
  })
})
```

```typescript
// src/frontend/src/components/__tests__/AllocationTree.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AllocationTree } from '../allocation/AllocationTree'

const mockTree = {
  centers: [{
    id: '1', name: 'HQ East',
    fields: [{
      id: '2', name: 'Field-Berlin', cpu_limit: 100, cpu_used: 40,
      departments: []
    }]
  }]
}

describe('AllocationTree', () => {
  it('renders center and field nodes', () => {
    render(<AllocationTree data={mockTree} />)
    expect(screen.getByText('HQ East')).toBeInTheDocument()
    expect(screen.getByText('Field-Berlin')).toBeInTheDocument()
  })

  it('shows usage bar text for field', () => {
    render(<AllocationTree data={mockTree} />)
    expect(screen.getByText(/40.*100/)).toBeInTheDocument()
  })
})
```

---

## What Makes a Good Test

**Good:**
- Tests behavior and outcomes, not implementation details
- Has a single reason to fail
- Uses descriptive names: `"raises QuotaExceededError when cpu_used + requested exceeds cpu_limit"`
- Is deterministic (no `time.sleep`, no random data without seeding)
- Independent — does not rely on execution order or shared mutable state

**Bad:**
- Tests that a function was called, not that the right thing happened
- Mocking the thing under test
- Tests that pass even when the acceptance criterion is not met
- Vague names: `"test create project"`

---

## Mock Patterns

### MockLDAPClient (for auth tests)

```python
class MockLDAPClient:
    def __init__(self, groups: list[str], should_fail: bool = False):
        self._groups = groups
        self._should_fail = should_fail

    async def authenticate(self, username: str, password: str) -> list[str]:
        if self._should_fail:
            raise LDAPAuthError("Invalid credentials")
        return self._groups
```

### MockHelmProvisioner (for project tests)

```python
class MockHelmProvisioner:
    def __init__(self, should_fail: bool = False):
        self.provisioned: list = []
        self._should_fail = should_fail

    async def provision(self, project) -> None:
        if self._should_fail:
            raise ProvisioningError("git push failed")
        self.provisioned.append(project)
```
