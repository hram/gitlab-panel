from typing import Protocol
from app.domain.models.release import Release


class ReleaseRepository(Protocol):

    def list_releases(self, project_id: int) -> list[Release]:
        ...

    def create_release(self, release: Release) -> None:
        ...

    def delete_release(self, release_id: int) -> None:
        ...

    def exists_by_version(self, project_id: int, version: str) -> bool:
        ...

    def get_release_versions(self, project_id: int) -> list[str]:
        ...
