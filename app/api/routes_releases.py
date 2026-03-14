from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import logging

from app.application.release_service import ReleaseService
from app.application.project_service import ProjectService
from app.application.stage_service import StageService
from app.application.branch_service import BranchService
from app.application.commit_check_service import CommitCheckService
from app.application.jira_progress_service import JiraProgressService
from app.infrastructure.config import JIRA_URL

logger = logging.getLogger(__name__)


router = APIRouter()

templates = Jinja2Templates(directory="templates")

release_service = ReleaseService()
project_service = ProjectService()
stage_service = StageService()
branch_service = BranchService()
commit_check_service = CommitCheckService()
jira_progress_service = JiraProgressService()


@router.get("/api/projects/{project_id}/releases")
def list_releases(
    request: Request,
    project_id: int,
):
    releases = release_service.list_releases(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)
    stages = stage_service.list_stages(project_id)
    source_branch = branch_service.get_next_release_source_branch(project_id)
    
    # Автоматически вычисляем прогресс для релизов с jira_fix_version и статусом "in_progress"
    for release in releases:
        if release.jira_fix_version and release.status == "in_progress":
            try:
                result = jira_progress_service.calculate_release_progress(
                    fix_version=release.jira_fix_version,
                    project_key="TBLT"
                )
                if result["progress"] != release.progress:
                    release_service.update_progress(release.id, result["progress"])
                    logger.info(f"Auto-updated progress for release {release.version}: {release.progress}% -> {result['progress']}%")
            except Exception as e:
                logger.error(f"Error auto-calculating progress for release {release.version}: {e}")
    
    # Перезагружаем список с обновлённым прогрессом
    releases = release_service.list_releases(project_id)

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
    history_with_durations = release_service.calculate_stage_durations(history)
    stages = stage_service.list_stages(project_id)
    project = project_service.get_project_by_gitlab_id(project_id)

    # --- Release Summary ---
    stage_breakdown = []
    for h in history_with_durations:
        if h["duration_days"] is not None and h["old_stage"]:
            stage_breakdown.append({"stage": h["old_stage"], "days": h["duration_days"], "is_current": False})

    # Время в текущей стадии (если релиз ещё в работе и текущая стадия — не последняя)
    if history_with_durations and release and release.status != "released":
        last = history_with_durations[-1]
        final_stage = max(stages, key=lambda s: s.order).name if stages else None
        if last["new_stage"] != final_stage:
            current_days = (datetime.now() - last["changed_at"]).days
            if current_days >= 0:
                stage_breakdown.append({"stage": last["new_stage"], "days": current_days, "is_current": True})

    total_days = sum(s["days"] for s in stage_breakdown)

    return templates.TemplateResponse(
        "release_stage_history.html",
        {
            "request": request,
            "release": release,
            "history": history_with_durations,
            "stages": stages,
            "project_id": project_id,
            "project_name": project.name if project else str(project_id),
            "stage_breakdown": stage_breakdown,
            "total_days": total_days,
            "sla_days": project.sla_days if project else None,
        },
    )


@router.post("/api/releases/{release_id}/history/{history_id}/delete")
def delete_stage_history_entry(
    request: Request,
    release_id: int,
    history_id: int,
):
    """Удаляет запись истории стадии."""
    release_service.delete_stage_history(history_id)

    # Возвращаем обновлённую таблицу
    history = release_service.get_stage_history(release_id)
    history_with_durations = release_service.calculate_stage_durations(history)
    release = release_service.get_release_by_id(release_id)
    stages = stage_service.list_stages(release.project_id) if release else []

    return templates.TemplateResponse(
        "partials/release_history_table.html",
        {
            "request": request,
            "release": release,
            "history": history_with_durations,
            "project_id": release.project_id if release else release_id,
            "stages": stages,
        },
    )


@router.post("/api/releases/{release_id}/history/add")
def add_stage_history_entry(
    request: Request,
    release_id: int,
    old_stage: str = Form(default=None),
    new_stage: str = Form(),
    changed_at: str = Form(),
):
    """Добавляет запись в историю стадии."""
    try:
        release_service.create_stage_history(
            release_id=release_id,
            old_stage=old_stage if old_stage else None,
            new_stage=new_stage,
            changed_at=changed_at,
            project_id=release_service.get_release_by_id(release_id).project_id if release_service.get_release_by_id(release_id) else None,
        )
        error = None
    except Exception as e:
        error = str(e)

    # Возвращаем обновлённую таблицу
    history = release_service.get_stage_history(release_id)
    history_with_durations = release_service.calculate_stage_durations(history)
    release = release_service.get_release_by_id(release_id)

    # Получаем project_id из релиза
    project = project_service.get_project_by_gitlab_id(release.project_id) if release else None
    stages = stage_service.list_stages(release.project_id) if release else []

    return templates.TemplateResponse(
        "partials/release_history_table.html",
        {
            "request": request,
            "release": release,
            "history": history_with_durations,
            "project_id": release.project_id if release else release_id,
            "stages": stages,
            "error": error,
        },
    )


@router.post("/api/releases/{release_id}/calculate-progress")
def calculate_release_progress(
    request: Request,
    release_id: int,
):
    """
    Вычисляет прогресс выполнения релиза на основе задач в Jira.
    Результат сохраняется в базу данных.
    """
    release = release_service.get_release_by_id(release_id)
    
    if not release:
        return JSONResponse(
            status_code=404,
            content={"error": "Релиз не найден"}
        )
    
    if not release.jira_fix_version:
        return JSONResponse(
            status_code=400,
            content={"error": "Jira Fix Version не указан для этого релиза"}
        )
    
    # Получаем проект для определения project_key
    project = project_service.get_project_by_gitlab_id(release.project_id)
    project_key = "TBLT"  # По умолчанию
    
    # Вычисляем прогресс
    result = jira_progress_service.calculate_release_progress(
        fix_version=release.jira_fix_version,
        project_key=project_key
    )
    
    if result["error"]:
        return JSONResponse(
            status_code=500,
            content={"error": result["error"]}
        )
    
    # Сохраняем прогресс в БД
    release_service.update_progress(release_id, result["progress"])
    
    return JSONResponse(content={
        "progress": result["progress"],
        "total_issues": result["total_issues"],
        "processed_issues": result["processed_issues"],
    })


@router.get("/api/projects/{project_id}/releases/import/gitlab-versions")
def get_gitlab_versions(project_id: int):
    """
    Возвращает список уникальных версий релизов из веток GitLab.
    Фильтрует ветки по паттерну <stage>/<semver>, например develop/1.6.0.
    Сортирует по SemVer убыванию (новые сверху).
    """
    import re
    semver_pattern = re.compile(r'^\d+\.\d+\.\d+$')

    try:
        branches = branch_service.list_branches(project_id=project_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    versions = set()
    branch_data = []
    for branch in branches:
        parts = branch.name.split("/")
        if len(parts) == 2:
            stage, version = parts[0], parts[1]
            if semver_pattern.match(version):
                versions.add(version)
                branch_data.append({"stage": stage, "version": version})

    def semver_key(v):
        return tuple(int(x) for x in v.split("."))

    sorted_versions = sorted(versions, key=semver_key, reverse=True)

    return JSONResponse({"versions": sorted_versions, "branch_data": branch_data})


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
