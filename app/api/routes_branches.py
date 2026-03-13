from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from app.application.branch_service import BranchService
from app.application.project_service import ProjectService


router = APIRouter()

templates = Jinja2Templates(directory="templates")

branch_service = BranchService()
project_service = ProjectService()


@router.get("/api/branches")
def list_branches(
    request: Request,
    search: str = Query(default=""),
    type: str = Query(default="all"),
):

    branches = branch_service.list_branches(search)

    if type != "all":
        branches = [b for b in branches if b.name.startswith(type)]

    return templates.TemplateResponse(
        "branches_list.html",
        {
            "request": request,
            "branches": branches,
        },
    )


@router.get("/api/branches/{project_id}")
def list_project_branches(
    request: Request,
    project_id: int,
    search: str = Query(default=""),
    type: str = Query(default="all"),
):

    branches = branch_service.list_branches_by_releases(search, project_id=project_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    return templates.TemplateResponse(
        "branches_list.html",
        {
            "request": request,
            "branches": branches,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
        },
    )


@router.get("/api/branches/{project_id}/next-release-source")
def get_next_release_source_branch(
    project_id: int,
):
    """
    Возвращает имя ветки, от которой будет создана первая ветка нового релиза.
    """
    source_branch = branch_service.get_next_release_source_branch(project_id)
    return {"source_branch": source_branch}