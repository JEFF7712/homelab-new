from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ChangeKind(str, Enum):
    ADDED = "added"
    COPIED = "copied"
    DELETED = "deleted"
    MODIFIED = "modified"
    RENAMED = "renamed"
    TYPE_CHANGED = "type_changed"
    UNMERGED = "unmerged"
    UNTRACKED = "untracked"


class ChangeSource(str, Enum):
    INDEX = "index"
    WORKTREE = "worktree"
    UNTRACKED = "untracked"
    COMMITTED = "committed"


@dataclass(frozen=True)
class ChangedPath:
    path: str
    path_bytes: bytes
    kind: ChangeKind
    source: ChangeSource
    old_path: str | None = None
    old_path_bytes: bytes | None = None


@dataclass(frozen=True)
class ChangeCounts:
    index: int
    worktree: int
    untracked: int
    committed: int

    @property
    def staged(self) -> int:
        return self.index

    @property
    def unstaged(self) -> int:
        return self.worktree

    @property
    def total(self) -> int:
        return self.index + self.worktree + self.untracked + self.committed


@dataclass(frozen=True)
class GitBase:
    available: bool
    reference: str | None
    resolved: str | None
    merge_base: str | None


@dataclass(frozen=True)
class GitState:
    root: Path
    branch: str | None
    detached: bool
    head: str | None
    base: GitBase
    counts: ChangeCounts
    changes: tuple[ChangedPath, ...]
    dirty: bool
    fingerprint: str

    @property
    def affected_paths(self) -> tuple[str, ...]:
        paths = {change.path for change in self.changes}
        paths.update(change.old_path for change in self.changes if change.old_path)
        return tuple(sorted(paths))
