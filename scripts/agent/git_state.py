from __future__ import annotations

import hashlib
import os
from pathlib import Path
import posixpath
import subprocess

from .models import ChangeCounts, ChangedPath, ChangeKind, ChangeSource, GitBase, GitState


class GitStateError(RuntimeError):
    pass


class GitBaseError(GitStateError):
    def __init__(self, base: str, message: str) -> None:
        self.base = base
        super().__init__(message)


def _git(
    *arguments: str,
    cwd: Path | None = None,
    allow_failure: bool = False,
) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 and not allow_failure:
        message = os.fsdecode(result.stderr).strip() or "git command failed"
        raise GitStateError(message)
    return result.stdout


def _normalise_path(path: bytes) -> bytes:
    normalised = posixpath.normpath(path)
    if normalised == b".":
        raise GitStateError("git returned an empty repository path")
    return normalised.removeprefix(b"./")


def _excluded(path: bytes) -> bool:
    return path == b".agent-state" or path.startswith(b".agent-state/")


def _kind(status: bytes) -> ChangeKind:
    code = status[:1]
    return {
        b"A": ChangeKind.ADDED,
        b"C": ChangeKind.COPIED,
        b"D": ChangeKind.DELETED,
        b"M": ChangeKind.MODIFIED,
        b"R": ChangeKind.RENAMED,
        b"T": ChangeKind.TYPE_CHANGED,
        b"U": ChangeKind.UNMERGED,
    }.get(code, ChangeKind.MODIFIED)


def _decode_path(path: bytes) -> str:
    return os.fsdecode(path)


def _parse_name_status(output: bytes, source: ChangeSource) -> list[ChangedPath]:
    fields = output.split(b"\0")
    changes: list[ChangedPath] = []
    index = 0
    while index < len(fields) - 1:
        status = fields[index]
        index += 1
        if not status:
            continue
        kind = _kind(status)
        if kind in (ChangeKind.RENAMED, ChangeKind.COPIED):
            old_path = _normalise_path(fields[index])
            path = _normalise_path(fields[index + 1])
            index += 2
            if _excluded(old_path) or _excluded(path):
                continue
            changes.append(
                ChangedPath(
                    path=_decode_path(path),
                    path_bytes=path,
                    kind=kind,
                    source=source,
                    old_path=_decode_path(old_path),
                    old_path_bytes=old_path,
                )
            )
            continue
        path = _normalise_path(fields[index])
        index += 1
        if _excluded(path):
            continue
        changes.append(
            ChangedPath(
                path=_decode_path(path),
                path_bytes=path,
                kind=kind,
                source=source,
            )
        )
    return changes


def _untracked(root: Path) -> list[ChangedPath]:
    output = _git("ls-files", "--others", "--exclude-standard", "-z", cwd=root)
    changes = []
    for raw_path in output.split(b"\0"):
        if not raw_path:
            continue
        path = _normalise_path(raw_path)
        if _excluded(path):
            continue
        changes.append(
            ChangedPath(
                path=_decode_path(path),
                path_bytes=path,
                kind=ChangeKind.UNTRACKED,
                source=ChangeSource.UNTRACKED,
            )
        )
    return changes


def _base_state(root: Path, head: str | None, base: str | None) -> GitBase:
    if base is None:
        return GitBase(False, None, None, None)
    if head is None:
        raise GitBaseError(base, f"Git base '{base}' is unavailable because HEAD has no commit")
    resolved = _git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}", cwd=root, allow_failure=True)
    if not resolved:
        raise GitBaseError(base, f"Git base '{base}' is unavailable. Fetch or choose a valid commit.")
    resolved_base = resolved.rstrip(b"\n").decode("ascii")
    merge_base = _git("merge-base", resolved_base, head, cwd=root, allow_failure=True)
    if not merge_base:
        raise GitBaseError(base, f"Git base '{base}' has no merge base with HEAD.")
    return GitBase(True, base, resolved_base, merge_base.rstrip(b"\n").decode("ascii"))


def _content(root: Path, change: ChangedPath) -> bytes | None:
    if change.kind == ChangeKind.DELETED:
        return None
    if change.source in (ChangeSource.WORKTREE, ChangeSource.UNTRACKED):
        target = root / os.fsdecode(change.path_bytes)
        try:
            return target.read_bytes()
        except FileNotFoundError:
            return None
    revision = ":./" if change.source == ChangeSource.INDEX else "HEAD:./"
    return _git("show", f"{revision}{_decode_path(change.path_bytes)}", cwd=root)


def _fingerprint(root: Path, head: str | None, base: GitBase, changes: tuple[ChangedPath, ...]) -> str:
    digest = hashlib.sha256()
    digest.update(b"agent-git-state-v1\0")
    for value in (head, base.resolved, base.merge_base):
        digest.update((value or "").encode("ascii"))
        digest.update(b"\0")
    for change in changes:
        digest.update(change.source.value.encode("ascii"))
        digest.update(b"\0")
        digest.update(change.kind.value.encode("ascii"))
        digest.update(b"\0")
        digest.update(change.old_path_bytes or b"")
        digest.update(b"\0")
        digest.update(change.path_bytes)
        digest.update(b"\0")
        content = _content(root, change)
        digest.update(b"missing\0" if content is None else hashlib.sha256(content).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def _counts(changes: tuple[ChangedPath, ...]) -> ChangeCounts:
    return ChangeCounts(
        index=sum(change.source == ChangeSource.INDEX for change in changes),
        worktree=sum(change.source == ChangeSource.WORKTREE for change in changes),
        untracked=sum(change.source == ChangeSource.UNTRACKED for change in changes),
        committed=sum(change.source == ChangeSource.COMMITTED for change in changes),
    )


def collect_git_state(cwd: Path | None = None, base: str | None = None) -> GitState:
    root_output = _git("rev-parse", "--show-toplevel", cwd=cwd)
    root = Path(os.fsdecode(root_output.rstrip(b"\n"))).resolve()
    head_output = _git("rev-parse", "--verify", "HEAD", cwd=root, allow_failure=True)
    head = head_output.rstrip(b"\n").decode("ascii") if head_output else None
    branch_output = _git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=root, allow_failure=True)
    branch = os.fsdecode(branch_output).strip() if branch_output else None
    git_base = _base_state(root, head, base)

    changes = _parse_name_status(
        _git("diff", "--cached", "--name-status", "-z", "-M", cwd=root),
        ChangeSource.INDEX,
    )
    changes.extend(
        _parse_name_status(
            _git("diff", "--name-status", "-z", "-M", cwd=root),
            ChangeSource.WORKTREE,
        )
    )
    changes.extend(_untracked(root))
    if git_base.available and git_base.merge_base:
        changes.extend(
            _parse_name_status(
                _git(
                    "diff",
                    "--name-status",
                    "-z",
                    "-M",
                    git_base.merge_base,
                    "HEAD",
                    cwd=root,
                ),
                ChangeSource.COMMITTED,
            )
        )

    deduplicated = {
        (change.source, change.kind, change.old_path_bytes, change.path_bytes): change
        for change in changes
    }
    ordered = tuple(
        sorted(
            deduplicated.values(),
            key=lambda change: (
                change.source.value,
                change.kind.value,
                change.old_path_bytes or b"",
                change.path_bytes,
            ),
        )
    )
    counts = _counts(ordered)
    return GitState(
        root=root,
        branch=branch,
        detached=branch is None,
        head=head,
        base=git_base,
        counts=counts,
        changes=ordered,
        dirty=counts.total > 0,
        fingerprint=_fingerprint(root, head, git_base, ordered),
    )
