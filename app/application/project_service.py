from app.domain.models.project import Project
from app.infrastructure.sqlite_project_repository import SQLiteProjectRepository


class ProjectService:

    def __init__(self):
        self.repo = SQLiteProjectRepository()


    def list_projects(self):
        return self.repo.list_projects()


    def create_project(self, name, url, gitlab_project_id):

        if self.repo.exists_by_gitlab_project_id(gitlab_project_id):
            raise ValueError(f"Project with gitlab_project_id {gitlab_project_id} already exists")

        project = Project(
            id=None,
            name=name,
            url=url,
            gitlab_project_id=gitlab_project_id,
        )

        self.repo.create_project(project)


    def delete_project(self, project_id):
        self.repo.delete_project(project_id)


    def get_project_by_gitlab_id(self, gitlab_project_id: int) -> Project | None:
        return self.repo.get_project_by_gitlab_id(gitlab_project_id)

    def get_project_by_id(self, project_id: int) -> Project | None:
        projects = self.repo.list_projects()
        return next((p for p in projects if p.id == project_id), None)

    def update_sla(self, project_id: int, sla_days: int | None) -> None:
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        project.sla_days = sla_days
        self.repo.update_project(project)