from datetime import date, datetime
import re
from app.domain.models.release import Release
from app.domain.models.release_stage_history import ReleaseStageHistory
from app.infrastructure.sqlite_release_repository import SQLiteReleaseRepository


class ReleaseService:

    def __init__(self):
        self.repo = SQLiteReleaseRepository()

    def list_releases(self, project_id: int):
        return self.repo.list_releases(project_id)

    def create_release(
        self,
        project_id: int,
        version: str,
        status: str,
        stage: str,
        start_date: str | None = None,
        release_date: str | None = None,
    ):

        if not self._is_valid_semver(version):
            raise ValueError(f"Invalid version format: {version}. Must be X.Y.Z (SemVer)")

        if self.repo.exists_by_version(project_id, version):
            raise ValueError(f"Release with version {version} already exists for this project")

        start = self._parse_date(start_date) if start_date else None
        release = self._parse_date(release_date) if release_date else None

        release_obj = Release(
            id=None,
            project_id=project_id,
            version=version,
            status=status,
            stage=stage,
            start_date=start,
            release_date=release,
        )

        self.repo.create_release(release_obj)

    def delete_release(self, release_id: int):
        self.repo.delete_release(release_id)

    def update_release(
        self,
        release_id: int,
        status: str,
        stage: str,
        start_date: str | None = None,
        release_date: str | None = None,
    ):
        # Получаем текущий релиз для сохранения old_stage
        current_release = self.repo.get_release_by_id(release_id)
        old_stage = current_release.stage if current_release else None

        self.repo.update_release(
            release_id,
            status=status,
            stage=stage,
            start_date=self._parse_date(start_date) if start_date else None,
            release_date=self._parse_date(release_date) if release_date else None,
            old_stage=old_stage,
        )

    def get_stage_history(self, release_id: int) -> list[ReleaseStageHistory]:
        return self.repo.get_stage_history(release_id)

    def get_release_by_id(self, release_id: int) -> Release | None:
        return self.repo.get_release_by_id(release_id)

    def _is_valid_semver(self, version: str) -> bool:
        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    def _parse_date(self, date_str: str) -> date:
        return date.fromisoformat(date_str)
