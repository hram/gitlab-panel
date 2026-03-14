from datetime import date, datetime

from app.domain.models.release_bundle import ReleaseBundle
from app.domain.models.release_bundle_item import ReleaseBundleItem
from app.infrastructure.sqlite_release_bundle_repository import SQLiteReleaseBundleRepository
from app.infrastructure.sqlite_release_bundle_item_repository import SQLiteReleaseBundleItemRepository


class ReleaseBundleService:

    def __init__(self):
        self.bundle_repo = SQLiteReleaseBundleRepository()
        self.item_repo = SQLiteReleaseBundleItemRepository()

    def list_bundles(self) -> list[ReleaseBundle]:
        bundles = self.bundle_repo.list_bundles()
        for bundle in bundles:
            bundle.items = self.item_repo.list_items_by_bundle(bundle.id)
        return bundles

    def get_bundle_by_id(self, bundle_id: int) -> ReleaseBundle | None:
        return self.bundle_repo.get_bundle_by_id(bundle_id)

    def create_bundle(self, name: str, status: str,
                      planned_release_date: str | None = None,
                      actual_release_date: str | None = None) -> ReleaseBundle:
        bundle = ReleaseBundle(
            id=None,
            name=name,
            status=status,
            planned_release_date=self._parse_date(planned_release_date),
            actual_release_date=self._parse_date(actual_release_date),
            created_at=datetime.now().isoformat(),
        )
        return self.bundle_repo.create_bundle(bundle)

    def update_bundle(self, bundle_id: int, name: str, status: str,
                      planned_release_date: str | None = None,
                      actual_release_date: str | None = None) -> None:
        bundle = self.bundle_repo.get_bundle_by_id(bundle_id)
        if not bundle:
            raise ValueError(f"Bundle with id {bundle_id} not found")

        bundle.name = name
        bundle.status = status
        bundle.planned_release_date = self._parse_date(planned_release_date)
        bundle.actual_release_date = self._parse_date(actual_release_date)
        self.bundle_repo.update_bundle(bundle)

    def delete_bundle(self, bundle_id: int) -> None:
        self.item_repo.delete_items_by_bundle(bundle_id)
        self.bundle_repo.delete_bundle(bundle_id)

    def add_item(self, bundle_id: int, project_id: int,
                 release_id: int, role: str | None = None) -> ReleaseBundleItem:
        # Проверка: проект не должен уже быть в бандле
        existing_items = self.item_repo.list_items_by_bundle(bundle_id)
        for item in existing_items:
            if item.project_id == project_id:
                raise ValueError(
                    f"Project {project_id} already exists in bundle {bundle_id}"
                )

        item = ReleaseBundleItem(
            id=None,
            bundle_id=bundle_id,
            project_id=project_id,
            release_id=release_id,
            role=role,
        )
        return self.item_repo.create_item(item)

    def update_item(self, item_id: int, release_id: int,
                    role: str | None = None) -> None:
        item = self.item_repo.get_item_by_id(item_id)
        if not item:
            raise ValueError(f"Item with id {item_id} not found")

        item.release_id = release_id
        item.role = role
        self.item_repo.update_item(item)

    def remove_item(self, item_id: int) -> None:
        self.item_repo.delete_item(item_id)

    def get_items_by_bundle(self, bundle_id: int) -> list[ReleaseBundleItem]:
        return self.item_repo.list_items_by_bundle(bundle_id)

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
