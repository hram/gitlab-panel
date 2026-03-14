from typing import Protocol
from app.domain.models.release_bundle import ReleaseBundle


class ReleaseBundleRepository(Protocol):

    def list_bundles(self) -> list[ReleaseBundle]:
        ...

    def get_bundle_by_id(self, bundle_id: int) -> ReleaseBundle | None:
        ...

    def create_bundle(self, bundle: ReleaseBundle) -> ReleaseBundle:
        ...

    def update_bundle(self, bundle: ReleaseBundle) -> None:
        ...

    def delete_bundle(self, bundle_id: int) -> None:
        ...
