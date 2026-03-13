from datetime import date, datetime
from app.domain.models.release import Release
from app.domain.models.release_stage_history import ReleaseStageHistory
from app.infrastructure.database import get_connection


class SQLiteReleaseRepository:

    def list_releases(self, project_id: int) -> list[Release]:

        conn = get_connection()

        rows = conn.execute(
            "SELECT * FROM releases WHERE project_id = ? ORDER BY version DESC",
            (project_id,),
        ).fetchall()

        conn.close()

        return [
            Release(
                id=row["id"],
                project_id=row["project_id"],
                version=row["version"],
                status=row["status"],
                stage=row["stage"],
                start_date=row["start_date"] if row["start_date"] else None,
                release_date=row["release_date"] if row["release_date"] else None,
                jira_fix_version=row["jira_fix_version"] if row["jira_fix_version"] else None,
                progress=row["progress"] if row["progress"] else 0.0,
            )
            for row in rows
        ]

    def create_release(self, release: Release):

        conn = get_connection()

        conn.execute(
            """
            INSERT INTO releases(project_id, version, status, stage, start_date, release_date, jira_fix_version)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                release.project_id,
                release.version,
                release.status,
                release.stage,
                release.start_date.isoformat() if release.start_date else None,
                release.release_date.isoformat() if release.release_date else None,
                release.jira_fix_version,
            ),
        )

        conn.commit()
        conn.close()

    def exists_by_version(self, project_id: int, version: str) -> bool:

        conn = get_connection()

        row = conn.execute(
            "SELECT 1 FROM releases WHERE project_id=? AND version=?",
            (project_id, version),
        ).fetchone()

        conn.close()

        return row is not None

    def delete_release(self, release_id: int):

        conn = get_connection()

        conn.execute(
            "DELETE FROM releases WHERE id=?",
            (release_id,),
        )

        conn.commit()
        conn.close()

    def get_release_versions(self, project_id: int) -> list[str]:

        conn = get_connection()

        rows = conn.execute(
            "SELECT DISTINCT version FROM releases WHERE project_id = ?",
            (project_id,),
        ).fetchall()

        conn.close()

        return [row["version"] for row in rows]

    def update_release(
        self,
        release_id: int,
        status: str,
        stage: str,
        start_date: date | None = None,
        release_date: date | None = None,
        jira_fix_version: str | None = None,
        old_stage: str | None = None,
    ):

        conn = get_connection()

        conn.execute(
            """
            UPDATE releases
            SET status=?, stage=?, start_date=?, release_date=?, jira_fix_version=?
            WHERE id=?
            """,
            (
                status,
                stage,
                start_date.isoformat() if start_date else None,
                release_date.isoformat() if release_date else None,
                jira_fix_version,
                release_id,
            ),
        )

        # Записываем историю изменения стадии
        if old_stage is not None and old_stage != stage:
            conn.execute(
                """
                INSERT INTO release_stage_history(release_id, old_stage, new_stage, changed_at)
                VALUES (?,?,?,?)
                """,
                (
                    release_id,
                    old_stage,
                    stage,
                    datetime.now().isoformat(),
                ),
            )

        conn.commit()
        conn.close()

    def get_stage_history(self, release_id: int) -> list[ReleaseStageHistory]:

        conn = get_connection()

        rows = conn.execute(
            "SELECT * FROM release_stage_history WHERE release_id = ? ORDER BY changed_at ASC",
            (release_id,),
        ).fetchall()

        conn.close()

        return [
            ReleaseStageHistory(
                id=row["id"],
                release_id=row["release_id"],
                old_stage=row["old_stage"],
                new_stage=row["new_stage"],
                changed_at=datetime.fromisoformat(row["changed_at"]),
            )
            for row in rows
        ]

    def get_release_by_id(self, release_id: int) -> Release | None:

        conn = get_connection()

        row = conn.execute(
            "SELECT * FROM releases WHERE id=?",
            (release_id,),
        ).fetchone()

        conn.close()

        if row is None:
            return None

        return Release(
            id=row["id"],
            project_id=row["project_id"],
            version=row["version"],
            status=row["status"],
            stage=row["stage"],
            start_date=row["start_date"] if row["start_date"] else None,
            release_date=row["release_date"] if row["release_date"] else None,
            jira_fix_version=row["jira_fix_version"] if row["jira_fix_version"] else None,
            progress=row["progress"] if row["progress"] else 0.0,
        )

    def update_progress(self, release_id: int, progress: float):
        """Обновляет прогресс выполнения релиза."""
        conn = get_connection()

        conn.execute(
            "UPDATE releases SET progress=? WHERE id=?",
            (progress, release_id),
        )

        conn.commit()
        conn.close()
