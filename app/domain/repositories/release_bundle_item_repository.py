from typing import Protocol
from app.domain.models.release_bundle_item import ReleaseBundleItem


class ReleaseBundleItemRepository(Protocol):

    def list_items_by_bundle(self, bundle_id: int) -> list[ReleaseBundleItem]:
        ...

    def get_item_by_id(self, item_id: int) -> ReleaseBundleItem | None:
        ...

    def create_item(self, item: ReleaseBundleItem) -> ReleaseBundleItem:
        ...

    def update_item(self, item: ReleaseBundleItem) -> None:
        ...

    def delete_item(self, item_id: int) -> None:
        ...

    def delete_items_by_bundle(self, bundle_id: int) -> None:
        ...
