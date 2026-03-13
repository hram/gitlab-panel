from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates

from app.application.release_service import ReleaseService
from app.application.project_service import ProjectService
from app.application.stage_service import StageService
from app.application.branch_service import BranchService
from app.application.commit_check_service import CommitCheckService
from app.infrastructure.config import JIRA_URL


router = APIRouter()

templates = Jinja2Templates(directory="templates")

release_service = ReleaseService()
project_service = ProjectService()
stage_service = StageService()
branch_service = BranchService()
commit_check_service = CommitCheckService()


@router.get("/api/projects/{project_id}/releases")
def list_releases(
    request: Request,
    project_id: int,
):
    releases = release_service.list_releases(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)
    stages = stage_service.list_stages(project_id)
    source_branch = branch_service.get_next_release_source_branch(project_id)

    return templates.TemplateResponse(
        "partials/releases_table.html",
        {
            "request": request,
            "releases": releases,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "stages": stages,
            "error": None,
            "source_branch": source_branch,
            "jira_url": JIRA_URL,
        },
    )


@router.post("/api/projects/{project_id}/releases/create")
def create_release(
    request: Request,
    project_id: int,
    version: str = Form(),
    status: str = Form(),
    stage: str = Form(),
    start_date: str = Form(default=None),
    release_date: str = Form(default=None),
    create_branches: str = Form(default=None),
    source_branch: str = Form(default=None),
    jira_fix_version: str = Form(default=None),
):

    error = None
    warning = None
    created_branches = []

    try:
        release_service.create_release(
            project_id=project_id,
            version=version,
            status=status,
            stage=stage,
            start_date=start_date if start_date else None,
            release_date=release_date if release_date else None,
            jira_fix_version=jira_fix_version if jira_fix_version else None,
        )

        # Если выбран чекбокс "Создать ветки"
        if create_branches == "true" and source_branch:
            try:
                created_branches, warnings = branch_service.create_release_branches(
                    project_id=project_id,
                    version=version,
                    source_branch=source_branch,
                )
                if warnings:
                    warning = "; ".join(warnings)
            except Exception as e:
                warning = f"Не удалось создать ветки: {str(e)}"

    except ValueError as e:
        error = str(e)

    releases = release_service.list_releases(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)
    stages = stage_service.list_stages(project_id)

    return templates.TemplateResponse(
        "partials/releases_table.html",
        {
            "request": request,
            "releases": releases,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "stages": stages,
            "error": error,
            "warning": warning,
            "created_branches": created_branches,
            "jira_url": JIRA_URL,
        },
    )


@router.post("/api/releases/{release_id}/delete")
def delete_release(
    request: Request,
    release_id: int,
    project_id: int,
):

    release_service.delete_release(release_id)

    releases = release_service.list_releases(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)
    stages = stage_service.list_stages(project_id)

    return templates.TemplateResponse(
        "partials/releases_table.html",
        {
            "request": request,
            "releases": releases,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "stages": stages,
            "error": None,
            "jira_url": JIRA_URL,
        },
    )


@router.post("/api/releases/{release_id}/update")
def update_release(
    request: Request,
    release_id: int,
    project_id: int,
    status: str = Form(),
    stage: str = Form(),
    start_date: str = Form(default=None),
    release_date: str = Form(default=None),
    create_mr: str = Form(default=None),
    jira_key: str = Form(default=None),
    jira_fix_version: str = Form(default=None),
):

    error = None
    warning = None
    mr_info = None

    # Получаем текущий релиз для определения старой стадии
    current_release = release_service.get_release_by_id(release_id)
    old_stage = current_release.stage if current_release else None
    version = current_release.version if current_release else None

    # Обновляем релиз
    release_service.update_release(
        release_id,
        status=status,
        stage=stage,
        start_date=start_date if start_date else None,
        release_date=release_date if release_date else None,
        jira_fix_version=jira_fix_version if jira_fix_version else None,
    )

    # Если стадия изменилась и выбрано создание MR
    if create_mr == "true" and jira_key and old_stage != stage and version:
        try:
            mr_result = branch_service.create_feature_branch_and_mr(
                project_id=project_id,
                old_stage=old_stage,
                new_stage=stage,
                version=version,
                jira_key=jira_key,
            )

            if not mr_result['success']:
                error = "; ".join(mr_result['errors'])
            else:
                mr_info = mr_result
                if mr_result['warnings']:
                    warning = "; ".join(mr_result['warnings'])
                if mr_result['mr_created']:
                    warning = f"MR создан: {mr_result['mr_created']['web_url']}"
        except Exception as e:
            warning = f"Ошибка при создании MR: {str(e)}"

    releases = release_service.list_releases(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)
    stages = stage_service.list_stages(project_id)

    return templates.TemplateResponse(
        "partials/releases_table.html",
        {
            "request": request,
            "releases": releases,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "stages": stages,
            "error": error,
            "warning": warning,
            "mr_info": mr_info,
            "jira_url": JIRA_URL,
        },
    )


@router.get("/api/releases/{release_id}/edit")
def edit_release_form(
    request: Request,
    release_id: int,
    project_id: int,
):
    release = release_service.get_release_by_id(release_id)
    stages = stage_service.list_stages(release.project_id) if release else []

    return templates.TemplateResponse(
        "partials/release_edit_form.html",
        {
            "request": request,
            "release": release,
            "stages": stages,
            "project_id": project_id,
        },
    )


@router.get("/api/releases/{release_id}/history")
def release_stage_history(
    request: Request,
    release_id: int,
    project_id: int,
):
    release = release_service.get_release_by_id(release_id)
    history = release_service.get_stage_history(release_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    return templates.TemplateResponse(
        "release_stage_history.html",
        {
            "request": request,
            "release": release,
            "history": history,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
        },
    )


@router.get("/api/projects/{project_id}/releases/check-commits")
def check_releases_commits(
    request: Request,
    project_id: int,
):
    """
    Проверяет наличие коммитов в старых релизах, которых нет в более новых.
    """
    result = commit_check_service.check_commits_for_project(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    return templates.TemplateResponse(
        "partials/commit_check_result.html",
        {
            "request": request,
            "result": result,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
        },
    )
