#!/bin/sh
set -e

# Initialise the Helm chart directory as a local git repo for local-dev use.
# GitArgoProvisioner writes values.yaml and runs `git commit` here.
# The `git push` step will fail (no real remote) — that is expected in local dev.
# ArgoCD sync will also fail without a real ArgoCD — project rows will stay
# in status=provisioning, which is fine for local testing.
if [ ! -d "/app/helm-repo/.git" ]; then
    git -C /app/helm-repo init -b main
    git -C /app/helm-repo config user.email "infrahub@local"
    git -C /app/helm-repo config user.name "InfraHub Local"
    git -C /app/helm-repo add -A
    git -C /app/helm-repo commit -m "chore: init local helm-repo" --allow-empty
fi

# Run Alembic migrations before starting the server.
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
