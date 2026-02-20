"""Project (Kubernetes namespace) endpoints.

GET    /api/v1/projects         — list projects (scoped by role)
GET    /api/v1/projects/{id}    — single project
POST   /api/v1/projects         — create project (team_lead)
DELETE /api/v1/projects/{id}    — soft-delete project (team_lead)
"""

import httpx
from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.auth.jwt import Claims
from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.helm.provisioner import GitArgoProvisioner
from app.schemas.project import CreateProjectRequest, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _get_provisioner() -> GitArgoProvisioner:
    # In tests, override this dependency with MockHelmProvisioner
    client = httpx.AsyncClient(timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS)
    return GitArgoProvisioner(client)


def _service(
    session=Depends(get_db),
    provisioner: GitArgoProvisioner = Depends(_get_provisioner),
) -> ProjectService:
    return ProjectService(
        session=session,
        provisioner=provisioner,
        http_client=httpx.AsyncClient(timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS),
        session_factory=AsyncSessionLocal,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    claims: Claims = Depends(get_current_user),
    svc: ProjectService = Depends(_service),
) -> list[ProjectResponse]:
    return await svc.list_projects(claims)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    claims: Claims = Depends(get_current_user),
    svc: ProjectService = Depends(_service),
) -> ProjectResponse:
    return await svc.get_project(claims, project_id)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest,
    claims: Claims = Depends(get_current_user),
    svc: ProjectService = Depends(_service),
) -> ProjectResponse:
    return await svc.create_project(
        claims,
        name=body.name,
        site=body.site,
        sla_type=body.sla_type,
        performance_tier=body.performance_tier,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    claims: Claims = Depends(get_current_user),
    svc: ProjectService = Depends(_service),
) -> None:
    await svc.delete_project(claims, project_id)
