import json as _json

from fastapi import APIRouter, Request, Form, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from app.application.release_bundle_service import ReleaseBundleService
from app.application.project_service import ProjectService
from app.application.release_service import ReleaseService


router = APIRouter()

templates = Jinja2Templates(directory="templates")

bundle_service = ReleaseBundleService()
project_service = ProjectService()
release_service = ReleaseService()


@router.get("/bundles")
def bundles_page(request: Request):
    """Страница управления пакетами релизов."""
    bundles = bundle_service.list_bundles()
    return templates.TemplateResponse(
        "bundles.html",
        {
            "request": request,
            "bundles": bundles,
        },
    )


@router.get("/api/bundles")
def list_bundles(request: Request):
    """API: Список всех пакетов."""
    bundles = bundle_service.list_bundles()
    return templates.TemplateResponse(
        "partials/bundles_table.html",
        {
            "request": request,
            "bundles": bundles,
        },
    )


@router.post("/api/bundles/create")
def create_bundle(
    request: Request,
    name: str = Form(),
    status: str = Form(),
    planned_release_date: str = Form(default=None),
    actual_release_date: str = Form(default=None),
):
    """API: Создание нового пакета."""
    try:
        bundle_service.create_bundle(
            name=name,
            status=status,
            planned_release_date=planned_release_date if planned_release_date else None,
            actual_release_date=actual_release_date if actual_release_date else None,
        )
        error = None
    except ValueError as e:
        error = str(e)

    bundles = bundle_service.list_bundles()
    return templates.TemplateResponse(
        "partials/bundles_table.html",
        {
            "request": request,
            "bundles": bundles,
            "error": error,
        },
    )


@router.post("/api/bundles/create-with-items")
def create_bundle_with_items(
    request: Request,
    name: str = Form(),
    status: str = Form(),
    planned_release_date: str = Form(default=None),
    actual_release_date: str = Form(default=None),
    items: str = Form(default="[]"),
):
    """API: Создание нового пакета с элементами."""
    import json

    try:
        # Добавляем элементы
        items_data = json.loads(items)
        
        # Проверяем на дубликаты проектов
        project_ids = [item["project_id"] for item in items_data]
        if len(project_ids) != len(set(project_ids)):
            raise ValueError("Каждый проект может быть выбран только один раз в пакете")
        
        bundle = bundle_service.create_bundle(
            name=name,
            status=status,
            planned_release_date=planned_release_date if planned_release_date else None,
            actual_release_date=actual_release_date if actual_release_date else None,
        )

        for item in items_data:
            bundle_service.add_item(
                bundle_id=bundle.id,
                project_id=int(item["project_id"]),
                release_id=int(item["release_id"]),
            )

        error = None
    except ValueError as e:
        error = str(e)
    except Exception as e:
        error = str(e)

    bundles = bundle_service.list_bundles()
    return templates.TemplateResponse(
        "partials/bundles_table.html",
        {
            "request": request,
            "bundles": bundles,
            "error": error,
        },
    )


@router.post("/api/bundles/{bundle_id}/delete")
def delete_bundle(request: Request, bundle_id: int):
    """API: Удаление пакета."""
    bundle_service.delete_bundle(bundle_id)
    bundles = bundle_service.list_bundles()
    return templates.TemplateResponse(
        "partials/bundles_table.html",
        {
            "request": request,
            "bundles": bundles,
        },
    )


@router.get("/api/bundles/{bundle_id}/edit")
def edit_bundle_form(request: Request, bundle_id: int):
    """API: Форма редактирования пакета."""
    bundle = bundle_service.get_bundle_by_id(bundle_id)
    if not bundle:
        return templates.TemplateResponse(
            "partials/bundles_table.html",
            {
                "request": request,
                "bundles": bundle_service.list_bundles(),
                "error": f"Пакет с id {bundle_id} не найден",
            },
        )

    return templates.TemplateResponse(
        "partials/bundle_edit_form.html",
        {
            "request": request,
            "bundle": bundle,
            "bundle_id": bundle_id,
        },
    )


@router.post("/api/bundles/{bundle_id}/update")
async def update_bundle(
    request: Request,
    bundle_id: int,
    name: str = Form(),
    status: str = Form(),
    planned_release_date: str = Form(default=None),
    actual_release_date: str = Form(default=None),
):
    """API: Обновление пакета."""
    from typing import List
    error = None
    try:
        bundle_service.update_bundle(
            bundle_id=bundle_id,
            name=name,
            status=status,
            planned_release_date=planned_release_date if planned_release_date else None,
            actual_release_date=actual_release_date if actual_release_date else None,
        )

        # Добавляем новые элементы (new_project/new_release могут быть множественными)
        form_data = await request.form()
        new_projects = form_data.getlist("new_project")
        new_releases = form_data.getlist("new_release")

        for project_id_str, release_id_str in zip(new_projects, new_releases):
            if project_id_str and release_id_str:
                bundle_service.add_item(
                    bundle_id=bundle_id,
                    project_id=int(project_id_str),
                    release_id=int(release_id_str),
                )
    except ValueError as e:
        error = str(e)

    bundles = bundle_service.list_bundles()
    return templates.TemplateResponse(
        "partials/bundles_table.html",
        {
            "request": request,
            "bundles": bundles,
            "error": error,
        },
    )


@router.post("/api/bundles/{bundle_id}/items/add")
def add_bundle_item(
    request: Request,
    bundle_id: int,
    project_id: int = Form(),
    release_id: int = Form(),
    role: str = Form(default=None),
):
    """API: Добавление элемента в пакет."""
    try:
        bundle_service.add_item(
            bundle_id=bundle_id,
            project_id=project_id,
            release_id=release_id,
            role=role if role else None,
        )
        error = None
    except ValueError as e:
        error = str(e)

    bundle = bundle_service.get_bundle_by_id(bundle_id)
    return templates.TemplateResponse(
        "partials/bundle_edit_form.html",
        {
            "request": request,
            "bundle": bundle,
            "bundle_id": bundle_id,
            "error": error,
        },
    )


@router.post("/api/bundles/items/{item_id}/delete")
def delete_bundle_item(
    request: Request,
    item_id: int,
    bundle_id: int,
):
    """API: Удаление элемента из пакета."""
    bundle_service.remove_item(item_id)
    bundle = bundle_service.get_bundle_by_id(bundle_id)
    return templates.TemplateResponse(
        "partials/bundle_edit_form.html",
        {
            "request": request,
            "bundle": bundle,
            "bundle_id": bundle_id,
        },
    )


@router.post("/api/bundles/items/{item_id}/update")
def update_bundle_item(
    request: Request,
    item_id: int,
    release_id: int = Form(),
):
    """API: Обновление релиза в элементе пакета."""
    try:
        bundle_service.update_item(item_id=item_id, release_id=release_id)
    except ValueError as e:
        pass  # Игнорируем ошибки
    return JSONResponse(content={"success": True})


@router.get("/api/bundles/{bundle_id}/projects/available")
def get_available_projects(request: Request, bundle_id: int):
    """API: Получить проекты, ещё не добавленные в пакет."""
    bundle = bundle_service.get_bundle_by_id(bundle_id)
    existing_project_ids = {item.project_id for item in bundle.items} if bundle else set()

    all_projects = project_service.list_projects()
    available_projects = [p for p in all_projects if p.id not in existing_project_ids]

    return templates.TemplateResponse(
        "partials/bundle_project_options.html",
        {
            "request": request,
            "projects": available_projects,
        },
    )


@router.get("/api/bundles/new-projects/available")
def get_all_projects(request: Request):
    """API: Получить все проекты (для нового пакета)."""
    all_projects = project_service.list_projects()

    return templates.TemplateResponse(
        "partials/bundle_project_options.html",
        {
            "request": request,
            "projects": all_projects,
        },
    )


@router.post("/api/bundles/reorder")
async def reorder_bundles(request: Request):
    """API: Сохранить новый порядок пакетов."""
    data = await request.json()
    ids = data.get("ids", [])
    bundle_service.reorder_bundles(ids)
    return JSONResponse(content={"success": True})


@router.get("/api/projects/{project_id}/releases/in-progress")
def get_project_releases_in_progress(request: Request, project_id: int):
    """API: Получить релизы проекта со статусом 'in_progress'."""
    releases = release_service.list_releases(project_id)
    in_progress_releases = [r for r in releases if r.status == "in_progress"]

    return templates.TemplateResponse(
        "partials/bundle_release_options.html",
        {
            "request": request,
            "releases": in_progress_releases,
            "project_id": project_id,
        },
    )
