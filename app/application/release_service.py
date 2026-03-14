from datetime import date, datetime
import re
from app.domain.models.release import Release
from app.domain.models.release_stage_history import ReleaseStageHistory
from app.infrastructure.sqlite_release_repository import SQLiteReleaseRepository
from app.application.stage_service import StageService
from app.application.stage_analytics_service import StageAnalyticsService


class ReleaseService:

    def __init__(self):
        self.repo = SQLiteReleaseRepository()
        self.stage_service = StageService()
        self.analytics_service = StageAnalyticsService()

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
        jira_fix_version: str | None = None,
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
            jira_fix_version=jira_fix_version,
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
        jira_fix_version: str | None = None,
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
            jira_fix_version=jira_fix_version,
            old_stage=old_stage,
        )

    def get_stage_history(self, release_id: int) -> list[ReleaseStageHistory]:
        return self.repo.get_stage_history(release_id)

    def get_release_by_id(self, release_id: int) -> Release | None:
        return self.repo.get_release_by_id(release_id)

    def update_progress(self, release_id: int, progress: float):
        """Обновляет прогресс выполнения релиза."""
        self.repo.update_progress(release_id, progress)

    def delete_stage_history(self, history_id: int):
        """Удаляет запись истории стадии."""
        self.repo.delete_stage_history(history_id)

    def create_stage_history(
        self,
        release_id: int,
        old_stage: str | None,
        new_stage: str,
        changed_at: str,
        project_id: int | None = None,
    ):
        """Создаёт запись истории стадии."""
        # Валидация порядка стадий
        if old_stage is not None and project_id is not None:
            self._validate_stage_transition(old_stage, new_stage, project_id)

        self.repo.create_stage_history(
            release_id=release_id,
            old_stage=old_stage,
            new_stage=new_stage,
            changed_at=self._parse_datetime_or_date(changed_at),
        )

    def _validate_stage_transition(self, old_stage: str, new_stage: str, project_id: int):
        """Проверяет, что переход между стадиями допустим (только вперёд)."""
        stages = self.stage_service.list_stages(project_id)
        stage_order = {s.name: s.order for s in stages}

        if old_stage not in stage_order:
            raise ValueError(f"Неизвестная старая стадия: {old_stage}")
        if new_stage not in stage_order:
            raise ValueError(f"Неизвестная новая стадия: {new_stage}")

        if stage_order[new_stage] <= stage_order[old_stage]:
            raise ValueError(
                f"Переход из стадии '{old_stage}' в стадию '{new_stage}' запрещён. "
                f"Стадии могут изменяться только в порядке увеличения order."
            )

    def calculate_stage_durations(self, history: list[ReleaseStageHistory]) -> list[dict]:
        """
        Вычисляет длительность каждой стадии в днях.
        Делегирует универсальному сервису StageAnalyticsService.
        """
        durations = self.analytics_service.calculate_stage_durations(history)
        return [
            {
                'id': d.id,
                'release_id': d.release_id,
                'old_stage': d.old_stage,
                'new_stage': d.new_stage,
                'changed_at': d.changed_at,
                'duration_days': d.duration_days,
            }
            for d in durations
        ]

    def _is_valid_semver(self, version: str) -> bool:
        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    def _parse_date(self, date_str: str) -> date:
        return date.fromisoformat(date_str)

    def _parse_datetime_or_date(self, datetime_str: str) -> datetime:
        """Парсит дату или дату-с-временем. Если только дата — добавляет 00:00:00."""
        try:
            # Пробуем как datetime
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            # Если не вышло — это просто дата, добавляем время
            date_val = date.fromisoformat(datetime_str)
            return datetime(date_val.year, date_val.month, date_val.day, 0, 0, 0)
