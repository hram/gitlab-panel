from app.domain.models.stage import Stage
from app.infrastructure.database import get_connection


class SQLiteStageRepository:

    def list_stages(self, project_id: int) -> list[Stage]:

        conn = get_connection()

        rows = conn.execute(
            "SELECT * FROM stages WHERE project_id = ? ORDER BY stage_order ASC",
            (project_id,),
        ).fetchall()

        conn.close()

        return [
            Stage(
                id=row["id"],
                project_id=row["project_id"],
                name=row["name"],
                order=row["stage_order"],
            )
            for row in rows
        ]

    def create_stage(self, stage: Stage):

        conn = get_connection()

        conn.execute(
            """
            INSERT INTO stages(project_id, name, stage_order)
            VALUES (?,?,?)
            """,
            (
                stage.project_id,
                stage.name,
                stage.order,
            ),
        )

        conn.commit()
        conn.close()

    def delete_stage(self, stage_id: int):

        conn = get_connection()

        conn.execute(
            "DELETE FROM stages WHERE id=?",
            (stage_id,),
        )

        conn.commit()
        conn.close()
