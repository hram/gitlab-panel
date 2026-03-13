from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates

from app.application.project_service import ProjectService


router = APIRouter()

templates = Jinja2Templates(directory="templates")

service = ProjectService()


@router.get("/projects")
def projects_page(request: Request):

    projects = service.list_projects()

    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": projects, "error": None},
    )


@router.post("/projects/create")
def create_project(
    request: Request,
    name: str = Form(),
    url: str = Form(),
    gitlab_project_id: str = Form(),
):

    try:
        service.create_project(name, url, gitlab_project_id)
        error = None
    except ValueError as e:
        error = str(e)

    projects = service.list_projects()

    return templates.TemplateResponse(
        "partials/projects_table.html",
        {
            "request": request,
            "projects": projects,
            "error": error
        }
    )


@router.post("/projects/delete/{project_id}")
def delete_project(request: Request, project_id: int):

    service.delete_project(project_id)

    projects = service.list_projects()

    return templates.TemplateResponse(
        "partials/projects_table.html",
        {
            "request": request,
            "projects": projects
        }
    )