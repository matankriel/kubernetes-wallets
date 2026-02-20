"""Helm + ArgoCD namespace provisioner.

HelmProvisioner ABC defines the interface; GitArgoProvisioner is the real
implementation that:
  1. Updates src/helm/values.yaml (namespaces list)
  2. git commit + push to GitLab
  3. POST ArgoCD sync API

Tests inject MockHelmProvisioner to avoid filesystem/git/network I/O.
"""

import asyncio
import logging
import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

from app.config import settings
from app.models.project import Project

log = logging.getLogger(__name__)


class HelmProvisioner(ABC):
    @abstractmethod
    async def provision(self, project: Project) -> None: ...

    @abstractmethod
    async def deprovision(self, project: Project) -> None: ...


class GitArgoProvisioner(HelmProvisioner):
    """Writes namespace entry into Helm values.yaml, git-pushes, then syncs ArgoCD."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client
        self._repo_path = Path(settings.HELM_GIT_REPO_PATH)

    # ── internal helpers ───────────────────────────────────────────────────

    def _values_path(self) -> Path:
        return self._repo_path / "values.yaml"

    def _add_namespace_entry(self, project: Project) -> None:
        """Append a namespace block to values.yaml (YAML-safe, no deps on PyYAML)."""
        entry = (
            f"  - name: {project.namespace_name}\n"
            f"    teamId: {project.team_id}\n"
            f"    resourceQuota:\n"
            f"      cpu: {project.quota_cpu}\n"
            f"      memory: {project.quota_ram_gb}Gi\n"
        )
        values_path = self._values_path()
        text = values_path.read_text() if values_path.exists() else "namespaces:\n"
        if "namespaces:" not in text:
            text = "namespaces:\n" + text
        values_path.write_text(text + entry)

    def _remove_namespace_entry(self, namespace_name: str) -> None:
        """Remove the block for a specific namespace from values.yaml."""
        values_path = self._values_path()
        if not values_path.exists():
            return
        lines = values_path.read_text().splitlines(keepends=True)
        filtered: list[str] = []
        skip_next = 0
        for i, line in enumerate(lines):
            if f"  - name: {namespace_name}" in line:
                # Remove this line and the next 4 (teamId, resourceQuota, cpu, memory)
                skip_next = 4
                continue
            if skip_next > 0:
                skip_next -= 1
                continue
            filtered.append(line)
        values_path.write_text("".join(filtered))

    def _git(self, *args: str) -> None:
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._repo_path),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")

    async def _argocd_sync(self) -> None:
        url = (
            f"{settings.ARGOCD_URL.rstrip('/')}"
            f"/api/v1/applications/{settings.ARGOCD_APP_NAME}/sync"
        )
        resp = await self._client.post(
            url,
            headers={"Authorization": f"Bearer {settings.ARGOCD_TOKEN}"},
            json={},
        )
        resp.raise_for_status()

    # ── public interface ───────────────────────────────────────────────────

    async def provision(self, project: Project) -> None:
        self._add_namespace_entry(project)
        self._git("add", "values.yaml")
        self._git("commit", "-m", f"feat(namespaces): provision {project.namespace_name}")
        self._git("push")
        await self._argocd_sync()

    async def deprovision(self, project: Project) -> None:
        if project.namespace_name:
            self._remove_namespace_entry(project.namespace_name)
            self._git("add", "values.yaml")
            self._git("commit", "-m", f"chore(namespaces): remove {project.namespace_name}")
            self._git("push")
            await self._argocd_sync()


# ── ArgoCD status poller ────────────────────────────────────────────────────

_POLL_INTERVAL_SECONDS = 10
_POLL_TIMEOUT_SECONDS = 300


async def poll_argocd_until_synced(
    http_client: httpx.AsyncClient,
    project_id: str,
    session_factory,
) -> None:
    """Background task: poll ArgoCD until namespace is synced or timeout."""
    url = (
        f"{settings.ARGOCD_URL.rstrip('/')}"
        f"/api/v1/applications/{settings.ARGOCD_APP_NAME}"
    )
    headers = {"Authorization": f"Bearer {settings.ARGOCD_TOKEN}"}
    elapsed = 0

    while elapsed < _POLL_TIMEOUT_SECONDS:
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        elapsed += _POLL_INTERVAL_SECONDS
        try:
            resp = await http_client.get(url, headers=headers)
            resp.raise_for_status()
            body = resp.json()
            sync_status = body.get("status", {}).get("sync", {}).get("status", "")
            health_status = body.get("status", {}).get("health", {}).get("status", "")
            if sync_status == "Synced" and health_status == "Healthy":
                await _set_project_status(session_factory, project_id, "active")
                return
        except Exception:
            log.exception("ArgoCD poll error for project %s", project_id)

    # Timeout — mark failed
    log.error("ArgoCD sync timed out for project %s", project_id)
    await _set_project_status(session_factory, project_id, "failed")


async def _set_project_status(session_factory, project_id: str, status: str) -> None:
    from app.repositories.project_repo import ProjectRepository

    async with session_factory() as session:
        async with session.begin():
            repo = ProjectRepository(session)
            await repo.update_status(project_id, status)


# ── Namespace name generator ────────────────────────────────────────────────

def make_namespace_name(team_id: str, project_name: str) -> str:
    """Generate a valid Kubernetes namespace name (<= 63 chars, DNS-1123 subdomain)."""
    raw = f"{team_id}-{project_name}"
    sanitized = re.sub(r"[^a-z0-9-]", "-", raw.lower())
    sanitized = re.sub(r"-+", "-", sanitized).strip("-")
    return sanitized[:63]
