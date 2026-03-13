import sqlite3


def get_connection():
    conn = sqlite3.connect("projects.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            gitlab_project_id TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS releases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            version TEXT NOT NULL,
            status TEXT NOT NULL,
            stage TEXT NOT NULL,
            start_date TEXT,
            release_date TEXT,
            jira_fix_version TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )

    # Добавляем колонку jira_fix_version если её нет (для существующих БД)
    try:
        conn.execute(
            """
            ALTER TABLE releases ADD COLUMN jira_fix_version TEXT
            """
        )
    except sqlite3.OperationalError:
        # Колонка уже существует
        pass

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            stage_order INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS release_stage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            release_id INTEGER NOT NULL,
            old_stage TEXT,
            new_stage TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (release_id) REFERENCES releases(id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()