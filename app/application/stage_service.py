from app.domain.models.stage import Stage
from app.infrastructure.sqlite_stage_repository import SQLiteStageRepository


class StageService:

    def __init__(self):
        self.repo = SQLiteStageRepository()

    def list_stages(self, project_id: int) -> list[Stage]:
        return self.repo.list_stages(project_id)

    def create_stage(self, project_id: int, name: str, order: int) -> Stage:
        stage = Stage(
            id=None,
            project_id=project_id,
            name=name,
            order=order,
        )
        self.repo.create_stage(stage)
        return stage

    def delete_stage(self, stage_id: int) -> None:
        self.repo.delete_stage(stage_id)
