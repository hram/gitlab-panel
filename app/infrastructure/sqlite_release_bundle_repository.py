from datetime import date

from app.domain.models.release_bundle import ReleaseBundle
from app.domain.models.release_bundle_item import ReleaseBundleItem
from app.infrastructure.database import get_connection


class SQLiteReleaseBundleRepository:

    def list_bundles(self) -> list[ReleaseBundle]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM release_bundles ORDER BY created_at DESC"
        ).fetchall()
        conn.close()

        return [
            ReleaseBundle(
                id=row["id"],
                name=row["name"],
                status=row["status"],
                planned_release_date=self._parse_date(row["planned_release_date"]),
                actual_release_date=self._parse_date(row["actual_release_date"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_bundle_by_id(self, bundle_id: int) -> ReleaseBundle | None:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM release_bundles WHERE id=?",
            (bundle_id,),
        ).fetchone()
        conn.close()

        if not row:
            return None

        bundle = ReleaseBundle(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            planned_release_date=self._parse_date(row["planned_release_date"]),
            actual_release_date=self._parse_date(row["actual_release_date"]),
            created_at=row["created_at"],
        )

        items = self._get_bundle_items(bundle_id)
        bundle.items = items

        return bundle

    def create_bundle(self, bundle: ReleaseBundle) -> ReleaseBundle:
        conn = get_connection()

        cursor = conn.execute(
            """
            INSERT INTO release_bundles(name, status, planned_release_date, actual_release_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                bundle.name,
                bundle.status,
                self._format_date(bundle.planned_release_date),
                self._format_date(bundle.actual_release_date),
                bundle.created_at,
            ),
        )

        bundle.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return bundle

    def update_bundle(self, bundle: ReleaseBundle) -> None:
        conn = get_connection()

        conn.execute(
            """
            UPDATE release_bundles
            SET name=?, status=?, planned_release_date=?, actual_release_date=?
            WHERE id=?
            """,
            (
                bundle.name,
                bundle.status,
                self._format_date(bundle.planned_release_date),
                self._format_date(bundle.actual_release_date),
                bundle.id,
            ),
        )

        conn.commit()
        conn.close()

    def delete_bundle(self, bundle_id: int) -> None:
        conn = get_connection()
        conn.execute(
            "DELETE FROM release_bundles WHERE id=?",
            (bundle_id,),
        )
        conn.commit()
        conn.close()

    def _get_bundle_items(self, bundle_id: int) -> list[ReleaseBundleItem]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT id, bundle_id, project_id, release_id, role
            FROM release_bundle_items
            WHERE bundle_id=?
            """,
            (bundle_id,),
        ).fetchall()
        conn.close()

        return [
            ReleaseBundleItem(
                id=row["id"],
                bundle_id=row["bundle_id"],
                project_id=row["project_id"],
                release_id=row["release_id"],
                role=row["role"],
            )
            for row in rows
        ]

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _format_date(self, value: date | None) -> str | None:
        if not value:
            return None
        return value.isoformat()
