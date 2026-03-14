from app.domain.models.release_bundle_item import ReleaseBundleItem
from app.domain.models.project import Project
from app.domain.models.release import Release
from app.infrastructure.database import get_connection


class SQLiteReleaseBundleItemRepository:

    def list_items_by_bundle(self, bundle_id: int) -> list[ReleaseBundleItem]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT rbi.id, rbi.bundle_id, rbi.project_id, rbi.release_id, rbi.role,
                   p.name as project_name, p.url as project_url, p.gitlab_project_id,
                   rel.version, rel.status as release_status, rel.stage,
                   rel.start_date, rel.release_date, rel.jira_fix_version, rel.progress
            FROM release_bundle_items rbi
            JOIN projects p ON rbi.project_id = p.gitlab_project_id
            JOIN releases rel ON rbi.release_id = rel.id
            WHERE rbi.bundle_id=?
            """,
            (bundle_id,),
        ).fetchall()
        conn.close()

        items = []
        for row in rows:
            project = Project(
                id=None,  # Внутренний ID не используется, важен gitlab_project_id
                name=row["project_name"],
                url=row["project_url"],
                gitlab_project_id=row["gitlab_project_id"],
            )
            release = Release(
                id=row["release_id"],
                project_id=row["gitlab_project_id"],  # Используем gitlab_project_id для связи
                version=row["version"],
                status=row["release_status"],
                stage=row["stage"],
                start_date=self._parse_date(row["start_date"]),
                release_date=self._parse_date(row["release_date"]),
                jira_fix_version=row["jira_fix_version"],
                progress=row["progress"],
            )
            item = ReleaseBundleItem(
                id=row["id"],
                bundle_id=row["bundle_id"],
                project_id=row["gitlab_project_id"],  # Используем gitlab_project_id
                release_id=row["release_id"],
                role=row["role"],
                project=project,
                release=release,
            )
            items.append(item)

        return items

    def get_item_by_id(self, item_id: int) -> ReleaseBundleItem | None:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM release_bundle_items WHERE id=?",
            (item_id,),
        ).fetchone()
        conn.close()

        if not row:
            return None

        return ReleaseBundleItem(
            id=row["id"],
            bundle_id=row["bundle_id"],
            project_id=row["project_id"],
            release_id=row["release_id"],
            role=row["role"],
        )

    def create_item(self, item: ReleaseBundleItem) -> ReleaseBundleItem:
        conn = get_connection()

        cursor = conn.execute(
            """
            INSERT INTO release_bundle_items(bundle_id, project_id, release_id, role)
            VALUES (?, ?, ?, ?)
            """,
            (item.bundle_id, item.project_id, item.release_id, item.role),
        )

        item.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return item

    def update_item(self, item: ReleaseBundleItem) -> None:
        conn = get_connection()

        conn.execute(
            """
            UPDATE release_bundle_items
            SET bundle_id=?, project_id=?, release_id=?, role=?
            WHERE id=?
            """,
            (item.bundle_id, item.project_id, item.release_id, item.role, item.id),
        )

        conn.commit()
        conn.close()

    def delete_item(self, item_id: int) -> None:
        conn = get_connection()
        conn.execute(
            "DELETE FROM release_bundle_items WHERE id=?",
            (item_id,),
        )
        conn.commit()
        conn.close()

    def delete_items_by_bundle(self, bundle_id: int) -> None:
        conn = get_connection()
        conn.execute(
            "DELETE FROM release_bundle_items WHERE bundle_id=?",
            (bundle_id,),
        )
        conn.commit()
        conn.close()

    def _parse_date(self, value: str | None) -> str | None:
        return value
