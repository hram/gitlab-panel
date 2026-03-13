from app.domain.models.commit_check import (
    CommitCheckResult,
    ReleaseCommitCheck,
    CommitInfo,
)
from app.domain.models.release import Release
from app.application.release_service import ReleaseService
from app.providers.gitlab_repository import GitLabRepository


class CommitCheckService:

    def __init__(self):
        self.release_service = ReleaseService()
        self.git_repo = GitLabRepository()

    def check_commits_for_project(self, project_id: int) -> CommitCheckResult:
        """
        Проверяет наличие коммитов в старых релизах, которых нет в более новых.
        
        Логика:
        1. Получаем все релизы проекта
        2. Сортируем от старшего к младшему (по версии)
        3. Проходим от младшего к старшему
        4. Для каждого релиза со статусом "In Progress" проверяем предыдущий (более старый)
        5. Если предыдущий тоже "In Progress" — сравниваем коммиты
        
        Пример:
        - 1.53.0 Released -> пропускаем
        - 1.54.0 In Progress, но 1.53.0 Released -> пропускаем
        - 1.55.0 In Progress, 1.54.0 In Progress -> проверяем коммиты
        - 1.56.0 In Progress, 1.55.0 In Progress -> проверяем коммиты
        """
        releases = self.release_service.list_releases(project_id)
        
        # Сортируем от старшего к младшему
        releases_sorted = sorted(
            releases,
            key=lambda r: self._parse_version(r.version),
            reverse=True,
        )
        
        checks: list[ReleaseCommitCheck] = []
        total_missing = 0
        
        # Проходим от младшего к старшему (индекс растёт)
        for i in range(len(releases_sorted) - 1, -1, -1):
            current = releases_sorted[i]
            
            # Пропускаем если текущий релиз не In Progress
            if current.status != "in_progress":
                continue
            
            # Находим предыдущий (более старый) релиз
            if i == len(releases_sorted) - 1:
                # Это самый старый релиз, не с чем сравнивать
                continue
            
            older_release = releases_sorted[i + 1]
            
            # Пропускаем если предыдущий релиз не In Progress
            if older_release.status != "in_progress":
                continue
            
            # Определяем имена веток
            current_branch = self._get_branch_name(current.stage, current.version)
            older_branch = self._get_branch_name(older_release.stage, older_release.version)
            
            # Проверяем коммиты: ищем коммиты в older_branch, которых нет в current_branch
            # from=current_branch (более новый), to=older_branch (более старый)
            missing_commits_raw = self._get_missing_commits(
                branch_name=older_branch,
                reference_branch=current_branch,
                project_id=project_id,
            )
            
            missing_commits = [
                CommitInfo(
                    id=c['id'],
                    short_id=c['short_id'],
                    title=c['title'],
                    author_name=c['author_name'],
                    created_at=c['created_at'],
                    web_url=c['web_url'],
                )
                for c in missing_commits_raw
                if not self._is_merge_commit(c['title'])
            ]
            
            check = ReleaseCommitCheck(
                release_id=older_release.id,
                version=older_release.version,
                stage=older_release.stage,
                status=older_release.status,
                branch=older_branch,
                newer_branch=current_branch,
                newer_version=current.version,
                has_missing_commits=len(missing_commits) > 0,
                missing_commits=missing_commits,
                missing_count=len(missing_commits),
            )
            
            checks.append(check)
            total_missing += len(missing_commits)
        
        return CommitCheckResult(
            project_id=project_id,
            checks=checks,
            total_missing=total_missing,
        )

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        """Парсит версию X.Y.Z в кортеж для сравнения."""
        parts = version.split('.')
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    def _get_branch_name(self, stage: str, version: str) -> str:
        """Формирует имя ветки по стадии и версии."""
        return f"{stage}/{version}"

    def _is_merge_commit(self, title: str) -> bool:
        """Проверяет, является ли коммит merge-коммитом (начинается с 'Merge branch')."""
        return title.startswith("Merge branch")

    def _get_missing_commits(
        self,
        branch_name: str,
        reference_branch: str,
        project_id: int,
    ) -> list[dict]:
        """Получает коммиты, которые есть в branch_name, но нет в reference_branch."""
        try:
            return self.git_repo.get_commits_in_branch_not_in_reference(
                branch_name=branch_name,
                reference_branch=reference_branch,
                project_id=project_id,
            )
        except Exception:
            # Если ветка не найдена или ошибка сравнения - возвращаем пустой список
            return []
