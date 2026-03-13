from dataclasses import dataclass


@dataclass
class Stage:
    id: int | None
    project_id: int
    name: str
    order: int
