from app.domain.models.project import Project
from app.infrastructure.database import get_connection


class SQLiteProjectRepository:

    def list_projects(self):

        conn = get_connection()

        rows = conn.execute(
            "SELECT * FROM projects ORDER BY name"
        ).fetchall()

        conn.close()

        return [
            Project(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                gitlab_project_id=row["gitlab_project_id"],
            )
            for row in rows
        ]


    def create_project(self, project: Project):

        conn = get_connection()

        conn.execute(
            """
            INSERT INTO projects(name,url,gitlab_project_id)
            VALUES (?,?,?)
            """,
            (project.name, project.url, project.gitlab_project_id),
        )

        conn.commit()
        conn.close()


    def exists_by_gitlab_project_id(self, gitlab_project_id: str) -> bool:

        conn = get_connection()

        row = conn.execute(
            "SELECT 1 FROM projects WHERE gitlab_project_id=?",
            (gitlab_project_id,),
        ).fetchone()

        conn.close()

        return row is not None


    def delete_project(self, project_id: int):

        conn = get_connection()

        conn.execute(
            "DELETE FROM projects WHERE id=?",
            (project_id,),
        )

        conn.commit()
        conn.close()

    def get_project_by_gitlab_id(self, gitlab_project_id: int) -> Project | None:

        conn = get_connection()

        row = conn.execute(
            "SELECT * FROM projects WHERE gitlab_project_id=?",
            (str(gitlab_project_id),),
        ).fetchone()

        conn.close()

        if row:
            return Project(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                gitlab_project_id=row["gitlab_project_id"],
            )

        return None