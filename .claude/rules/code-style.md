# Code Style Rules

These rules apply to all code written in this repository.

## General Principles

- **Clarity over cleverness:** Write code that the next developer can understand in 30 seconds.
- **Minimal surface area:** Don't expose more than what callers need.
- **Fail loudly:** Validate at boundaries; don't silently swallow errors.
- **Consistent naming:** Follow the conventions established in `docs/context/conventions.md`.

## Formatting

- Use the project's configured formatter (Prettier, Black, gofmt, etc.) — never manually reformat.
- Max line length: 100 characters (configurable per language in formatter config).
- No trailing whitespace.
- Files end with a single newline.

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Variables / functions | `camelCase` (JS/TS) or `snake_case` (Python) | `getUserById`, `get_user_by_id` |
| Classes / types | `PascalCase` | `UserProfile`, `ApiResponse` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Files | `kebab-case` | `user-profile.ts`, `auth-middleware.py` |
| Directories | `kebab-case` | `api-handlers/`, `data-models/` |
| Environment variables | `SCREAMING_SNAKE_CASE` | `DATABASE_URL`, `API_SECRET` |

## Comments

- **Don't** comment what the code does — name it so it's obvious.
- **Do** comment why a non-obvious decision was made.
- **Do** add TODO comments with a ticket reference: `// TODO(PROJ-123): remove after migration`
- No dead code comments (`// old implementation below`). Delete dead code.

## Functions & Methods

- Single responsibility: one function does one thing.
- Keep functions under 40 lines. Extract helpers if longer.
- Avoid more than 3 levels of nesting — early-return or extract instead.
- Prefer pure functions; limit side effects to well-named, intentional boundaries.

## Error Handling

- Never silently catch and discard errors.
- At system boundaries (HTTP handlers, CLI entry points), log errors with context before returning.
- Internal functions should propagate errors; only handle at the edge.
- Use structured errors with a `code` field where possible for programmatic handling.

## Imports / Dependencies

- No unused imports.
- Group imports: stdlib → third-party → internal (with a blank line between groups).
- Don't add a new dependency for something achievable in < 20 lines of code.
- Pin dependency versions; don't use `*` or `latest`.
