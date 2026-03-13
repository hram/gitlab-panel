from dataclasses import dataclass


@dataclass
class CommitInfo:
    """Информация о коммите."""
    id: str
    short_id: str
    title: str
    author_name: str
    created_at: str
    web_url: str


@dataclass
class BranchCommitCheck:
    """Результат проверки коммитов между двумя ветками."""
    older_branch: str
    newer_branch: str
    version: str
    has_missing_commits: bool
    missing_commits: list[CommitInfo]
    missing_count: int


@dataclass
class ReleaseCommitCheck:
    """Результат проверки для релиза."""
    release_id: int
    version: str
    stage: str
    status: str
    branch: str
    newer_branch: str | None
    newer_version: str | None
    has_missing_commits: bool
    missing_commits: list[CommitInfo]
    missing_count: int


@dataclass
class CommitCheckResult:
    """Общий результат проверки коммитов для проекта."""
    project_id: int
    checks: list[ReleaseCommitCheck]
    total_missing: int
