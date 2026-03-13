from typing import Protocol
from app.domain.models.stage import Stage


class StageRepository(Protocol):

    def list_stages(self, project_id: int) -> list[Stage]:
        ...

    def create_stage(self, stage: Stage) -> None:
        ...

    def delete_stage(self, stage_id: int) -> None:
        ...
