from dataclasses import dataclass


@dataclass
class Branch:
    name: str
    commit_sha: str
    protected: bool