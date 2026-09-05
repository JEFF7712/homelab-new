from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.agent.git_state import GitBaseError, collect_git_state
from scripts.agent.models import ChangeKind, ChangeSource
from tests.agent_helpers import commit, git, make_repository


class GitStateTest(unittest.TestCase):
    def test_clean_checkout_has_stable_empty_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-clean-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_bytes(b"tracked\n")
            commit(repository, "initial")

            first = collect_git_state(repository)
            second = collect_git_state(repository)

        self.assertEqual(first.root, repository.resolve())
        self.assertEqual(first.branch, "main")
        self.assertFalse(first.detached)
        self.assertRegex(first.head or "", r"^[0-9a-f]{40}$")
        self.assertFalse(first.dirty)
        self.assertEqual(first.counts.total, 0)
        self.assertEqual(first.changes, ())
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_collects_all_local_change_sources_with_unusual_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-paths-") as directory:
            repository = make_repository(Path(directory))
            for name in ("staged.txt", "unstaged.txt", "deleted.txt", "old name.txt"):
                (repository / name).write_text(name, encoding="utf-8")
            (repository / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            commit(repository, "initial")

            (repository / "staged.txt").write_bytes(b"index version\n")
            git(repository, "add", "staged.txt")
            (repository / "staged.txt").write_bytes(b"index then worktree\n")
            (repository / "unstaged.txt").write_bytes(b"worktree version\n")
            (repository / "deleted.txt").unlink()
            git(repository, "mv", "old name.txt", "renamed name.txt")
            for name in (
                "space name.txt",
                "tab\tname.txt",
                "line\nbreak.txt",
                "unicode-λ.txt",
                "-leading-dash.txt",
            ):
                (repository / name).write_bytes(name.encode("utf-8"))
            (repository / "ignored").mkdir()
            (repository / "ignored" / "skip.txt").write_bytes(b"ignored")
            (repository / ".agent-state").mkdir()
            (repository / ".agent-state" / "private.json").write_bytes(b"private")

            state = collect_git_state(repository)

        records = {(change.path, change.kind, change.source, change.old_path) for change in state.changes}
        self.assertIn(("staged.txt", ChangeKind.MODIFIED, ChangeSource.INDEX, None), records)
        self.assertIn(("staged.txt", ChangeKind.MODIFIED, ChangeSource.WORKTREE, None), records)
        self.assertIn(("unstaged.txt", ChangeKind.MODIFIED, ChangeSource.WORKTREE, None), records)
        self.assertIn(("deleted.txt", ChangeKind.DELETED, ChangeSource.WORKTREE, None), records)
        self.assertIn(
            ("renamed name.txt", ChangeKind.RENAMED, ChangeSource.INDEX, "old name.txt"),
            records,
        )
        for name in (
            "space name.txt",
            "tab\tname.txt",
            "line\nbreak.txt",
            "unicode-λ.txt",
            "-leading-dash.txt",
        ):
            self.assertIn((name, ChangeKind.UNTRACKED, ChangeSource.UNTRACKED, None), records)
            record = next(change for change in state.changes if change.path == name)
            self.assertEqual(record.path_bytes, name.encode("utf-8"))
        self.assertNotIn("ignored/skip.txt", {change.path for change in state.changes})
        self.assertFalse(any(change.path.startswith(".agent-state") for change in state.changes))
        self.assertIn("old name.txt", state.affected_paths)
        self.assertIn("renamed name.txt", state.affected_paths)
        self.assertEqual(len(records), len(state.changes))
        self.assertEqual(state.counts.index, 2)
        self.assertEqual(state.counts.worktree, 3)
        self.assertEqual(state.counts.untracked, 5)

    def test_only_untracked_files_are_dirty_and_change_the_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-untracked-") as directory:
            repository = make_repository(Path(directory))
            target = repository / "only untracked.txt"
            target.write_bytes(b"first")
            first = collect_git_state(repository)
            target.write_bytes(b"second")
            second = collect_git_state(repository)

        self.assertIsNone(first.head)
        self.assertTrue(first.dirty)
        self.assertEqual(first.counts.untracked, 1)
        self.assertEqual(first.changes[0].kind, ChangeKind.UNTRACKED)
        self.assertNotEqual(first.fingerprint, second.fingerprint)

    def test_fingerprint_detects_worktree_change_without_head_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-fingerprint-") as directory:
            repository = make_repository(Path(directory))
            target = repository / "tracked.txt"
            target.write_bytes(b"committed")
            commit(repository, "initial")
            clean = collect_git_state(repository)
            target.write_bytes(b"working change")
            dirty = collect_git_state(repository)

        self.assertEqual(clean.head, dirty.head)
        self.assertNotEqual(clean.fingerprint, dirty.fingerprint)

    def test_staged_deletion_is_an_index_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-staged-delete-") as directory:
            repository = make_repository(Path(directory))
            target = repository / "delete.txt"
            target.write_bytes(b"tracked")
            commit(repository, "initial")
            git(repository, "rm", "-q", "delete.txt")

            state = collect_git_state(repository)

        self.assertEqual(state.counts.index, 1)
        self.assertEqual(
            (state.changes[0].path, state.changes[0].kind, state.changes[0].source),
            ("delete.txt", ChangeKind.DELETED, ChangeSource.INDEX),
        )

    def test_ignored_and_agent_state_files_do_not_change_the_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-ignored-") as directory:
            repository = make_repository(Path(directory))
            (repository / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            (repository / "tracked.txt").write_bytes(b"tracked")
            commit(repository, "initial")
            clean = collect_git_state(repository)
            (repository / "ignored").mkdir()
            (repository / "ignored" / "skip.txt").write_bytes(b"ignored")
            (repository / ".agent-state").mkdir()
            (repository / ".agent-state" / "state.json").write_bytes(b"state")
            ignored = collect_git_state(repository)

        self.assertEqual(clean.fingerprint, ignored.fingerprint)
        self.assertFalse(ignored.dirty)

    def test_base_collects_committed_changes_from_merge_base(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-base-") as directory:
            repository = make_repository(Path(directory))
            target = repository / "tracked.txt"
            target.write_bytes(b"one")
            commit(repository, "initial")
            base = git(repository, "rev-parse", "HEAD").decode().strip()
            target.write_bytes(b"two")
            commit(repository, "second")

            state = collect_git_state(repository, base=base)

        self.assertTrue(state.base.available)
        self.assertEqual(state.base.reference, base)
        self.assertEqual(state.base.merge_base, base)
        self.assertIn(
            ("tracked.txt", ChangeKind.MODIFIED, ChangeSource.COMMITTED),
            {(change.path, change.kind, change.source) for change in state.changes},
        )
        self.assertEqual(state.counts.committed, 1)
        self.assertFalse(state.dirty)

    def test_invalid_or_unavailable_base_is_actionable_typed_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-invalid-base-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_bytes(b"tracked")
            commit(repository, "initial")
            for base in ("does-not-exist", "origin/missing"):
                with self.subTest(base=base):
                    with self.assertRaises(GitBaseError) as raised:
                        collect_git_state(repository, base=base)

                    self.assertEqual(raised.exception.base, base)
                    self.assertIn("git base", str(raised.exception).lower())
                    self.assertIn("unavailable", str(raised.exception).lower())


if __name__ == "__main__":
    unittest.main()
