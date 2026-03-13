import gitlab

from app.domain.models.branch import Branch
from app.infrastructure.config import (
    GITLAB_URL,
    GITLAB_TOKEN,
    GITLAB_PROJECT_ID,
)


class GitLabRepository:

    def __init__(self, project_id: int | None = None):
        self.gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN)
        if project_id:
            self.project = self.gl.projects.get(project_id)
        else:
            self.project = self.gl.projects.get(GITLAB_PROJECT_ID)

    def list_branches(self, search: str | None = None, project_id: int | None = None) -> list[Branch]:

        params = {
            "get_all": True
        }

        if search:
            params["search"] = search

        if project_id:
            project = self.gl.projects.get(project_id)
        else:
            project = self.project

        branches = project.branches.list(**params)

        result = []

        for b in branches:
            result.append(
                Branch(
                    name=b.name,
                    commit_sha=b.commit["id"],
                    protected=b.protected,
                )
            )

        return result

    def create_branch(self, branch_name: str, ref: str) -> dict:
        """
        Создаёт новую ветку от указанной ref (ветка, commit, tag).
        Возвращает информацию о созданной ветке.
        Raises: gitlab.GitlabCreateError если ветка уже существует или ошибка создания.
        """
        try:
            new_branch = self.project.branches.create({
                'branch': branch_name,
                'ref': ref
            })
            return {
                'name': new_branch.name,
                'commit_sha': new_branch.commit['id'],
                'protected': new_branch.protected
            }
        except gitlab.GitlabCreateError as e:
            raise Exception(f"Не удалось создать ветку '{branch_name}': {str(e)}")

    def get_project(self, project_id: int):
        """Возвращает проект GitLab по ID."""
        return self.gl.projects.get(project_id)

    def create_merge_request(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
        squash: bool = False,
    ) -> dict | None:
        """
        Создаёт Merge Request в GitLab.
        Возвращает информацию о MR или None если не удалось.
        """
        try:
            mr = self.project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description,
                'squash': squash,
                'remove_source_branch': True,
            })
            return {
                'id': mr.id,
                'iid': mr.iid,
                'title': mr.title,
                'web_url': mr.web_url,
                'source_branch': mr.source_branch,
                'target_branch': mr.target_branch,
            }
        except Exception as e:
            raise Exception(f"Не удалось создать MR: {str(e)}")

    def enable_merge_when_pipeline_succeeds(self, mr_iid: int) -> bool:
        """
        Устанавливает флаг 'Merge when pipeline succeeds' для указанного MR.
        Возвращает True если успешно, False если ошибка.
        """
        try:
            mr = self.project.mergerequests.get(mr_iid)
            mr.merge(merge_when_pipeline_succeeds=True)
            return True
        except Exception as e:
            return False

    def get_merge_request_commits(self, mr_iid: int) -> list[dict]:
        """
        Получает список коммитов для указанного Merge Request.
        Возвращает список коммитов в формате GitLab API.
        """
        try:
            mr = self.project.mergerequests.get(mr_iid)
            commits = mr.commits()
            return [
                {
                    'id': c.id,
                    'short_id': c.short_id,
                    'title': c.title,
                    'message': c.message,
                    'author_name': c.author_name,
                    'author_email': c.author_email,
                    'created_at': c.created_at,
                    'web_url': c.web_url,
                }
                for c in commits
            ]
        except Exception as e:
            raise Exception(f"Не удалось получить коммиты MR {mr_iid}: {str(e)}")

    def get_branch_commits(self, branch_name: str, project_id: int | None = None) -> list[dict]:
        """
        Получает список коммитов указанной ветки.
        Возвращает список коммитов в формате GitLab API.
        """
        try:
            if project_id:
                project = self.gl.projects.get(project_id)
            else:
                project = self.project

            commits = project.commits.list(
                ref_name=branch_name,
                get_all=True,
                order='topo'
            )

            return [
                {
                    'id': c.id,
                    'short_id': c.short_id,
                    'title': c.title,
                    'message': c.message,
                    'author_name': c.author_name,
                    'author_email': c.author_email,
                    'created_at': c.created_at,
                    'web_url': c.web_url,
                }
                for c in commits
            ]
        except Exception as e:
            raise Exception(f"Не удалось получить коммиты ветки '{branch_name}': {str(e)}")

    def get_commits_in_branch_not_in_reference(
        self,
        branch_name: str,
        reference_branch: str,
        project_id: int | None = None,
    ) -> list[dict]:
        """
        Получает коммиты, которые есть в branch_name, но нет в reference_branch.
        Использует GitLab API для сравнения веток.
        """
        try:
            if project_id:
                project = self.gl.projects.get(project_id)
            else:
                project = self.project

            # Получаем коммиты через compare API
            comparison = project.repository_compare(
                from_=reference_branch,
                to=branch_name,
            )

            # comparison['commits'] содержит коммиты, которые есть в 'to', но нет в 'from'
            commits = comparison.get('commits', [])

            return [
                {
                    'id': c['id'],
                    'short_id': c['short_id'],
                    'title': c['title'],
                    'message': c.get('message', ''),
                    'author_name': c.get('author_name', ''),
                    'author_email': c.get('author_email', ''),
                    'created_at': c.get('created_at', ''),
                    'web_url': c.get('web_url', ''),
                }
                for c in commits
            ]
        except Exception as e:
            raise Exception(
                f"Не удалось сравнить ветки '{branch_name}' и '{reference_branch}': {str(e)}"
            )