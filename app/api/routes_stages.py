from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response

from app.application.stage_service import StageService
from app.application.project_service import ProjectService


router = APIRouter()

templates = Jinja2Templates(directory="templates")

stage_service = StageService()
project_service = ProjectService()


@router.get("/api/projects/{project_id}/stages")
def list_stages(
    request: Request,
    project_id: int,
):
    stages = stage_service.list_stages(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    return templates.TemplateResponse(
        "partials/stages_table.html",
        {
            "request": request,
            "stages": stages,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "error": None,
        },
    )


@router.post("/api/projects/{project_id}/stages/create")
def create_stage(
    request: Request,
    project_id: int,
    name: str = Form(),
    order: int = Form(),
):

    try:
        stage_service.create_stage(
            project_id=project_id,
            name=name,
            order=order,
        )
        error = None
    except ValueError as e:
        error = str(e)

    stages = stage_service.list_stages(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    response = templates.TemplateResponse(
        "partials/stages_table.html",
        {
            "request": request,
            "stages": stages,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "error": error,
        },
    )
    response.headers["HX-Trigger"] = "addStage"
    return response


@router.post("/api/projects/{project_id}/stages/import")
def import_stages(
    request: Request,
    project_id: int,
    source_project_id: int = Form(),
):
    source_stages = stage_service.list_stages(source_project_id)
    for s in source_stages:
        try:
            stage_service.create_stage(
                project_id=project_id,
                name=s.name,
                order=s.order,
            )
        except Exception:
            pass

    stages = stage_service.list_stages(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    return templates.TemplateResponse(
        "partials/stages_table.html",
        {
            "request": request,
            "stages": stages,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "error": None,
        },
    )


@router.post("/api/projects/{project_id}/stages/{stage_id}/delete")
def delete_stage(
    request: Request,
    project_id: int,
    stage_id: int,
):

    stage_service.delete_stage(stage_id)

    stages = stage_service.list_stages(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    response = templates.TemplateResponse(
        "partials/stages_table.html",
        {
            "request": request,
            "stages": stages,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "error": None,
        },
    )
    response.headers["HX-Trigger"] = "addStage"
    return response
