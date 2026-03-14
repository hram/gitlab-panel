from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models.release_bundle_item import ReleaseBundleItem


@dataclass
class ReleaseBundle:
    id: int | None
    name: str
    status: str  # "planned" | "in_progress" | "released" | "cancelled"
    planned_release_date: date | None
    actual_release_date: date | None
    created_at: str
    items: list["ReleaseBundleItem"] = field(default_factory=list)
