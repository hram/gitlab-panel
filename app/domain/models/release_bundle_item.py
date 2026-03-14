from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models.release_bundle import ReleaseBundle
    from app.domain.models.project import Project
    from app.domain.models.release import Release


@dataclass
class ReleaseBundleItem:
    id: int | None
    bundle_id: int
    project_id: int
    release_id: int
    role: str | None = None  # "primary" | "dependent" | "optional"
    bundle: "ReleaseBundle | None" = None
    project: "Project | None" = None
    release: "Release | None" = None
