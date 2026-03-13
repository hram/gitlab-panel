from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.application.project_service import ProjectService
from app.application.stage_service import StageService
from app.application.branch_service import BranchService

router = APIRouter()

templates = Jinja2Templates(directory="templates")

project_service = ProjectService()
stage_service = StageService()
branch_service = BranchService()


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@router.get("/branches")
def branches_page(request: Request):
    return templates.TemplateResponse(
        "branches.html",
        {"request": request},
    )


@router.get("/branches/{project_id}")
def project_branches_page(request: Request, project_id: int):
    project = project_service.get_project_by_gitlab_id(project_id)
    return templates.TemplateResponse(
        "project_branches.html",
        {
            "request": request,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
        },
    )


@router.get("/projects/{project_id}/releases")
def project_releases_page(request: Request, project_id: int):
    project = project_service.get_project_by_gitlab_id(project_id)
    stages = stage_service.list_stages(project_id)
    source_branch = branch_service.get_next_release_source_branch(project_id)
    return templates.TemplateResponse(
        "releases.html",
        {
            "request": request,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "stages": stages,
            "source_branch": source_branch,
        },
    )


@router.get("/projects/{project_id}/stages")
def project_stages_page(request: Request, project_id: int):
    project = project_service.get_project_by_gitlab_id(project_id)
    return templates.TemplateResponse(
        "stages.html",
        {
            "request": request,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
        },
    )