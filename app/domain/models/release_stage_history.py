from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReleaseStageHistory:
    id: int | None
    release_id: int
    old_stage: str | None
    new_stage: str
    changed_at: datetime
