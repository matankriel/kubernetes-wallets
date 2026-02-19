# Git Rules

## Branch Strategy

- `main` — production-ready code. **Protected. No direct pushes.**
- Feature branches: `feat/<story-id>-<short-description>` (e.g., `feat/STORY-003-ldap-auth`)
- Bug fixes: `fix/<short-description>` (e.g., `fix/quota-race-condition`)
- Chores: `chore/<short-description>` (e.g., `chore/update-dependencies`)

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

**InfraHub scope examples:**
```
feat(auth): implement LDAP bind + JWT issuance
feat(allocation): enforce quota invariant with SELECT FOR UPDATE
feat(projects): add Helm+ArgoCD provisioning flow
fix(sync): mark servers offline when absent from external API
chore(migrations): add revision 0006 for projects table
```

## Commit Rules

- Commits must be atomic — one logical change per commit.
- Never commit directly to `main`.
- Never use `--no-verify` to skip hooks without explicit user approval.
- Never commit `.env` files, secrets, credentials, or JWT_SECRET values.
- Run tests before committing — use the `/commit` skill which enforces this.
- Reference GitLab issue numbers in commit footers: `Closes #42`.

## Merge Requests (not Pull Requests — this project uses GitLab)

- Every MR must have a description explaining *why* the change is needed.
- MRs must have at least one approval before merging.
- All CI checks must pass (test-backend + test-frontend stages).
- Squash merge to keep main history clean.
- Delete the feature branch after merging.
- Open MRs with `glab mr create`, not `gh pr create`.

## Rebase vs Merge

- Rebase feature branches onto `main` before opening an MR.
- Never rebase shared/published branches.

## Tagging & Releases

- Use semantic versioning: `v<MAJOR>.<MINOR>.<PATCH>`
- Tag releases on `main`: `git tag -a v1.2.0 -m "Release v1.2.0"`
- Push tags explicitly: `git push origin --tags`
