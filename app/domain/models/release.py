from dataclasses import dataclass
from datetime import date


@dataclass
class Release:
    id: int | None
    project_id: int
    version: str
    status: str  # "in_progress" | "released"
    stage: str   # "develop" | "alpha" | "beta" | "prod"
    start_date: date | None
    release_date: date | None
    jira_fix_version: str | None = None
    progress: float = 0.0
