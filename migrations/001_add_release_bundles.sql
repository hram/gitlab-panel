-- Migration: Add release_bundles and release_bundle_items tables
-- Date: 2026-03-14
-- Description: Add support for cross-project delivery tracking

CREATE TABLE IF NOT EXISTS release_bundles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    planned_release_date TEXT,
    actual_release_date TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS release_bundle_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    release_id INTEGER NOT NULL,
    role TEXT,
    FOREIGN KEY (bundle_id) REFERENCES release_bundles(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (release_id) REFERENCES releases(id) ON DELETE CASCADE
);
