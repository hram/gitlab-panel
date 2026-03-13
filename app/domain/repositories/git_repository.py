from typing import Protocol
from app.domain.models.branch import Branch


class GitRepository(Protocol):

    def list_branches(self, search: str | None = None, project_id: int | None = None) -> list[Branch]:
        ...

    def get_branch_commits(self, branch_name: str, project_id: int | None = None) -> list[dict]:
        """Получает список коммитов указанной ветки."""
        ...

    def get_commits_in_branch_not_in_reference(
        self,
        branch_name: str,
        reference_branch: str,
        project_id: int | None = None,
    ) -> list[dict]:
        """Получает коммиты, которые есть в branch_name, но нет в reference_branch."""
        ...