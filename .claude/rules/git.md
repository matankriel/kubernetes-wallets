# Git Rules

## Branch Strategy

- `main` — production-ready code. **Protected. No direct pushes.**
- `production` — deployed to production. **Protected. No direct pushes.**
- Feature branches: `feat/<short-description>` (e.g., `feat/add-rate-limiting`)
- Bug fixes: `fix/<short-description>` (e.g., `fix/null-pointer-in-login`)
- Chores: `chore/<short-description>` (e.g., `chore/update-dependencies`)
- Releases: `release/<version>` (e.g., `release/v2.1.0`)

## Commit Message Format

Use **Conventional Commits**:

```
<type>(<scope>): <short description>

[optional body]

[optional footer: BREAKING CHANGE, Closes #123]
```

**Types:**
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `style` — formatting, no logic change
- `refactor` — code restructuring, no behavior change
- `test` — adding or updating tests
- `chore` — build, tooling, dependency updates
- `perf` — performance improvements
- `ci` — CI/CD changes
- `revert` — revert a previous commit

**Examples:**
```
feat(auth): add OAuth2 login with GitHub provider

fix(api): return 404 instead of 500 for missing resources

chore(deps): bump express from 4.18.1 to 4.18.2
```

## Commit Rules

- Commits must be atomic — one logical change per commit.
- Never commit directly to `main` or `production`.
- Never use `--no-verify` to skip hooks without explicit user approval.
- Never commit `.env` files, secrets, or credentials.
- Run `npm test` (or equivalent) before committing — use the `/commit` skill which enforces this.
- Reference issue/ticket numbers in commit footers: `Closes #42` or `Refs PROJ-123`.

## Pull Requests

- Every PR must have a description explaining *why* the change is needed.
- PRs must have at least one approval before merging.
- All CI checks must pass.
- Squash merge to keep main history clean (unless preserving commits is intentional).
- Delete branches after merging.

## Rebase vs Merge

- Rebase feature branches onto `main` before opening a PR.
- Never rebase shared/published branches.
- Merge PRs with a merge commit (not fast-forward) so the PR boundary is visible in history.

## Tagging & Releases

- Use semantic versioning: `v<MAJOR>.<MINOR>.<PATCH>`
- Tag releases on `main`: `git tag -a v1.2.0 -m "Release v1.2.0"`
- Push tags explicitly: `git push origin --tags`
