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

    try:
        conn.execute("ALTER TABLE projects ADD COLUMN sla_days INTEGER")
    except sqlite3.OperationalError:
        pass  # колонка уже существует

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
            progress REAL DEFAULT 0,
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

    # Добавляем колонку progress если её нет (для существующих БД)
    try:
        conn.execute(
            """
            ALTER TABLE releases ADD COLUMN progress REAL DEFAULT 0
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

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS release_bundles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            planned_release_date TEXT,
            actual_release_date TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS release_bundle_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            release_id INTEGER NOT NULL,
            role TEXT,
            FOREIGN KEY (bundle_id) REFERENCES release_bundles(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (release_id) REFERENCES releases(id) ON DELETE CASCADE
        )
        """
    )

    # Добавляем колонку sort_order в release_bundles если её нет
    try:
        conn.execute("ALTER TABLE release_bundles ADD COLUMN sort_order INTEGER")
        # Инициализируем sort_order по порядку создания (id)
        conn.execute("UPDATE release_bundles SET sort_order = id WHERE sort_order IS NULL")
    except sqlite3.OperationalError:
        pass  # колонка уже существует

    # Миграция: конвертируем project_id в release_bundle_items из gitlab_project_id → projects.id.
    # Актуально для записей, созданных до исправления бага (хранился gitlab_project_id вместо id).
    conn.execute(
        """
        UPDATE release_bundle_items
        SET project_id = (
            SELECT p.id FROM projects p
            WHERE p.gitlab_project_id = CAST(release_bundle_items.project_id AS TEXT)
        )
        WHERE project_id NOT IN (SELECT id FROM projects)
          AND EXISTS (
            SELECT 1 FROM projects p
            WHERE p.gitlab_project_id = CAST(release_bundle_items.project_id AS TEXT)
        )
        """
    )

    conn.commit()
    conn.close()