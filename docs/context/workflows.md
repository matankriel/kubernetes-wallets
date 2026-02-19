# Workflows

> Standard development workflows for InfraHub.

---

## Feature Development Workflow

```
1. Pick up a story from ralph/prd.json (or assign a GitLab issue)
       │
       ▼
2. Create a feature branch
   git checkout -b feat/<story-id>-<slug>
       │
       ▼
3. Implement the feature
   TDD preferred: write failing test first, then make it pass
       │
       ▼
4. Run simplicity-checker on new code
   "Use the simplicity-checker agent on <changed files>"
       │
       ▼
5. Lint + test locally
   cd src/backend && ruff check . && pytest -x --tb=short
   cd src/frontend && npm run lint && npm test
       │
       ▼
6. If feature has user-facing output → run product-reviewer
   "Use the product-reviewer agent on <changed files>"
       │
       ▼
7. Use /commit skill to create a conventional commit
       │
       ▼
8. Use /ship skill to push and open an MR on GitLab
       │
       ▼
9. Address review feedback
   (fix → commit → push; MR auto-updates)
       │
       ▼
10. Merge after 1 approval + CI passes
    (squash merge to keep main history clean)
       │
       ▼
11. Delete feature branch
       │
       ▼
12. Run ux-researcher post-implementation review
    "Use the ux-researcher agent in post-implementation mode on <feature name>"
```

---

## Bug Fix Workflow

1. Reproduce the bug locally
2. Create a `fix/<description>` branch
3. Use the `debugger` agent: `"Use the debugger agent to fix <bug description>"`
4. Verify the fix includes a regression test
5. Use `/commit` and `/ship`

---

## Code Review Workflow

### As Author
1. Self-review your diff before requesting review
2. Run `code-reviewer`: `"Use the code-reviewer agent to review my changes"`
3. Write a clear MR description: *what* changed and *why*
4. Link the relevant story/issue number

### As Reviewer

Use `/review-pr [number]` to get a structured review, then:
1. Approve if all is good
2. Leave inline comments for specific changes
3. Request changes if P0 (Critical) or P1 (Warning) issues exist

### Review SLA
- P0 (Critical) issues: review within 4 hours
- Regular MRs: review within 1 business day
- Draft MRs: feedback welcome but not required to block

---

## Database Migration Workflow

When a story requires schema changes:

```bash
# 1. Create a new migration
cd src/backend && alembic revision --autogenerate -m "add_column_to_projects"

# 2. Review the generated file
# IMPORTANT: autogenerate is not always perfect — verify the up/down are correct

# 3. Apply locally
alembic upgrade head

# 4. Run tests to confirm nothing broke
pytest -x --tb=short

# 5. Commit the migration file with the feature changes
```

**Rules:**
- Migrations must be backwards-compatible (old app + new schema must work)
- Never drop a column in the same migration that removes it from ORM model — do it in a follow-up deploy
- Test `alembic downgrade -1` succeeds before merging
- Never use `alembic stamp` to skip migrations in production

---

## Project Provisioning Flow (for testing manually)

```bash
# 1. Log in as team_lead
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"team-platform","password":"password"}' \
  | jq -r '.access_token')

# 2. Create a project
curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"payments","site":"berlin","sla_type":"silver","performance_tier":"regular"}'

# 3. Poll status
curl -s http://localhost:8000/api/v1/projects/<project-id> \
  -H "Authorization: Bearer $TOKEN"
# status: provisioning → active (when ArgoCD syncs)
```

---

## Server Allocation Flow (for testing manually)

```bash
# As center_admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')

# 1. Trigger server sync
curl -s -X POST http://localhost:8000/api/v1/admin/sync/servers \
  -H "Authorization: Bearer $TOKEN"

# 2. Assign a server to a field
curl -s -X POST http://localhost:8000/api/v1/allocations/servers \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"server_id":"<uuid>","field_id":"<uuid>"}'

# As field_admin — allocate quota to department
FIELD_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"username":"field-berlin","password":"password"}' | jq -r '.access_token')

curl -s -X POST http://localhost:8000/api/v1/allocations/department-quota \
  -H "Authorization: Bearer $FIELD_TOKEN" \
  -d '{"field_id":"<uuid>","dept_id":"<uuid>","site":"berlin","cpu_limit":80,"ram_gb_limit":256}'
```

---

## Ralph Autonomous Workflow

For stories that can be autonomously implemented:

1. Ensure story is `pending` in `ralph/prd.json` and all dependencies are `done`
2. Run Ralph: `bash ralph/run.sh --once`
3. Ralph picks the next pending story, implements it, pushes a branch, and opens an MR on GitLab
4. Review the log in `ralph/logs/` and the resulting MR code
5. Run `/review-pr` on the created MR before merging
6. After several Ralph sessions, run `pipeline-optimizer` to process FEEDBACK blocks:
   `"Use the pipeline-optimizer agent — <describe what went wrong, or 'do a general audit'>"`

---

## Pipeline Improvement Workflow

Run periodically, or after any session where outputs felt degraded:

```
"Use the pipeline-optimizer agent — <describe what went wrong>"
```

Triggers for running it:
- Ralph produces `FAILED` without a clear reason
- An agent's output is consistently vague or off-topic
- A story keeps failing on the same acceptance criterion
- After adding a new agent or skill

---

## ArgoCD Sync Workflow (manual)

```bash
# Check sync status
argocd app get infrahub-namespaces

# Manual sync (if auto-sync is disabled)
argocd app sync infrahub-namespaces --timeout 120

# Force hard refresh (clears cache)
argocd app sync infrahub-namespaces --force --timeout 120

# Check specific namespace was created
kubectl get namespace <namespace-name>
kubectl get resourcequota -n <namespace-name>
```

---

## Hotfix Workflow

For critical production bugs:

1. Branch from the last known-good tag: `git checkout -b fix/<description> v1.2.3`
2. Fix and test
3. Open MRs into both `main` AND tag the production release
4. After merge: `git tag v1.2.4` and trigger ArgoCD sync to production

---

## Dependency Update Workflow

Since the environment is air-gapped:
1. Coordinate with the platform team to mirror new packages to the internal PyPI/npm mirror
2. Update `pyproject.toml` or `package.json`
3. `pip install -e ".[dev]"` / `npm ci`
4. Run full test suite after each update
5. Check changelogs for breaking changes before major version bumps
