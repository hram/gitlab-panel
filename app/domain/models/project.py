from dataclasses import dataclass


@dataclass
class Project:
    id: int | None
    name: str
    url: str
    gitlab_project_id: str
    sla_days: int | None = None