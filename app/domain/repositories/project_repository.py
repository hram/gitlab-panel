from typing import Protocol
from app.domain.models.project import Project


class ProjectRepository(Protocol):

    def list_projects(self) -> list[Project]:
        ...

    def create_project(self, project: Project) -> None:
        ...

    def delete_project(self, project_id: int) -> None:
        ...