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
- Target: 80% line coverage minimum. Critical paths (auth, payments, data writes) require 95%.

## Test Structure

Follow the **Arrange → Act → Assert** (AAA) pattern:

```
// Arrange
const user = buildUser({ role: "admin" });

// Act
const result = canAccessDashboard(user);

// Assert
expect(result).toBe(true);
```

- One logical assertion per test (multiple `expect` calls are fine if they test the same thing).
- Test names: `"<unit> <action> <expected outcome>"` — e.g., `"getUserById returns null when user not found"`.

## Test Types

| Type | Location | When to write |
|------|----------|--------------|
| Unit | `src/**/__tests__/*.test.*` | Every function / class |
| Integration | `src/**/__tests__/*.integration.test.*` | DB queries, external API calls |
| E2E | `e2e/` | Critical user journeys |

## What to Test

- **Happy path:** the expected use case works.
- **Edge cases:** empty inputs, boundary values, nulls.
- **Failure paths:** what happens when dependencies fail.
- **Authorization:** users can only do what they're allowed to.

## What NOT to Test

- Implementation details (private methods, internal state).
- Framework code you didn't write.
- Type definitions (TypeScript compiler handles this).

## Test Doubles

- Prefer **fakes** (in-memory implementations) over **mocks** for complex collaborators.
- Use **mocks** only for external I/O (HTTP, filesystem, time).
- Never mock the module under test.
- Reset all mocks/spies in `afterEach` or `beforeEach`.

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run a specific test file
npm test -- path/to/file.test.ts
```
