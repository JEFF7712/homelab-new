from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

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

        records = {
            (change.path, change.kind, change.source, change.old_path)
            for change in state.changes
        }
        self.assertIn(
            ("staged.txt", ChangeKind.MODIFIED, ChangeSource.INDEX, None), records
        )
        self.assertIn(
            ("staged.txt", ChangeKind.MODIFIED, ChangeSource.WORKTREE, None), records
        )
        self.assertIn(
            ("unstaged.txt", ChangeKind.MODIFIED, ChangeSource.WORKTREE, None), records
        )
        self.assertIn(
            ("deleted.txt", ChangeKind.DELETED, ChangeSource.WORKTREE, None), records
        )
        self.assertIn(
            (
                "renamed name.txt",
                ChangeKind.RENAMED,
                ChangeSource.INDEX,
                "old name.txt",
            ),
            records,
        )
        for name in (
            "space name.txt",
            "tab\tname.txt",
            "line\nbreak.txt",
            "unicode-λ.txt",
            "-leading-dash.txt",
        ):
            self.assertIn(
                (name, ChangeKind.UNTRACKED, ChangeSource.UNTRACKED, None), records
            )
            record = next(change for change in state.changes if change.path == name)
            self.assertEqual(record.path_bytes, name.encode("utf-8"))
        self.assertNotIn("ignored/skip.txt", {change.path for change in state.changes})
        self.assertFalse(
            any(change.path.startswith(".agent-state") for change in state.changes)
        )
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

    def test_fingerprint_detects_mode_only_tracked_file_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-mode-") as directory:
            repository = make_repository(Path(directory))
            target = repository / "script.sh"
            target.write_bytes(b"#!/bin/sh\necho committed\n")
            target.chmod(0o644)
            commit(repository, "initial")
            clean = collect_git_state(repository)
            target.write_bytes(b"#!/bin/sh\necho staged\n")
            git(repository, "add", "script.sh")
            target.write_bytes(b"#!/bin/sh\necho worktree\n")
            target.chmod(0o644)
            non_executable = collect_git_state(repository)
            target.chmod(0o755)

            executable = collect_git_state(repository)

        self.assertNotEqual(clean.fingerprint, non_executable.fingerprint)
        self.assertNotEqual(non_executable.fingerprint, executable.fingerprint)
        self.assertIn(
            ("script.sh", ChangeKind.MODIFIED, ChangeSource.WORKTREE),
            {
                (change.path, change.kind, change.source)
                for change in executable.changes
            },
        )

    def test_staged_deletion_is_an_index_change(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-git-staged-delete-"
        ) as directory:
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

    def test_conflicted_index_has_a_stable_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-conflict-") as directory:
            repository = make_repository(Path(directory))
            target = repository / "conflict.txt"
            target.write_bytes(b"initial")
            commit(repository, "initial")
            git(repository, "checkout", "-qb", "other")
            target.write_bytes(b"other")
            commit(repository, "other")
            git(repository, "checkout", "-q", "main")
            target.write_bytes(b"main")
            commit(repository, "main")
            result = subprocess.run(
                ["git", "merge", "other"],
                cwd=repository,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)

            first = collect_git_state(repository)
            second = collect_git_state(repository)

        self.assertTrue(first.dirty)
        self.assertIn(
            ("conflict.txt", ChangeKind.UNMERGED, ChangeSource.INDEX),
            {(change.path, change.kind, change.source) for change in first.changes},
        )
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_worktree_symlink_target_is_fingerprinted_without_following_it(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-symlink-") as directory:
            repository = make_repository(Path(directory))
            (repository / "base-target").write_bytes(b"same content")
            (repository / "first-target").write_bytes(b"same content")
            (repository / "second-target").write_bytes(b"same content")
            link = repository / "link"
            link.symlink_to("base-target")
            commit(repository, "initial")
            link.unlink()
            link.symlink_to("first-target")
            first = collect_git_state(repository)
            link.unlink()
            link.symlink_to("second-target")

            second = collect_git_state(repository)

        self.assertNotEqual(first.fingerprint, second.fingerprint)
        self.assertIn(
            ("link", ChangeKind.MODIFIED, ChangeSource.WORKTREE),
            {(change.path, change.kind, change.source) for change in second.changes},
        )

    def test_worktree_symlink_to_directory_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-symlink-dir-") as directory:
            repository = make_repository(Path(directory))
            (repository / "first-directory").mkdir()
            (repository / "second-directory").mkdir()
            link = repository / "directory-link"
            link.symlink_to("first-directory", target_is_directory=True)
            commit(repository, "initial")
            link.unlink()
            link.symlink_to("second-directory", target_is_directory=True)

            state = collect_git_state(repository)

        self.assertTrue(state.dirty)
        self.assertIn(
            ("directory-link", ChangeKind.MODIFIED, ChangeSource.WORKTREE),
            {(change.path, change.kind, change.source) for change in state.changes},
        )

    def test_modified_gitlink_does_not_read_its_directory_as_a_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-gitlink-") as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            make_repository(nested)
            (nested / "tracked.txt").write_bytes(b"first")
            commit(nested, "first")
            (nested / "tracked.txt").write_bytes(b"second")
            commit(nested, "second")
            repository = root / "super"
            repository.mkdir()
            make_repository(repository)
            git(
                repository,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(nested),
                "module",
            )
            git(repository / "module", "checkout", "-q", "HEAD~1")
            commit(repository, "initial submodule")
            clean = collect_git_state(repository)
            git(repository / "module", "checkout", "-q", "main")

            changed = collect_git_state(repository)

        self.assertNotEqual(clean.fingerprint, changed.fingerprint)
        self.assertIn(
            ("module", ChangeKind.MODIFIED, ChangeSource.WORKTREE),
            {(change.path, change.kind, change.source) for change in changed.changes},
        )

    def test_dirty_gitlink_fingerprint_includes_nested_file_content(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-git-gitlink-content-"
        ) as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            make_repository(nested)
            nested_target = nested / "tracked.txt"
            nested_target.write_bytes(b"committed")
            commit(nested, "initial")
            repository = root / "super"
            repository.mkdir()
            make_repository(repository)
            git(
                repository,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(nested),
                "module",
            )
            commit(repository, "initial submodule")
            module_target = repository / "module" / "tracked.txt"
            module_target.write_bytes(b"first dirty content")
            first = collect_git_state(repository)
            module_target.write_bytes(b"second dirty content")

            second = collect_git_state(repository)

        self.assertNotEqual(first.fingerprint, second.fingerprint)

    def test_untracked_only_gitlink_is_dirty_and_fingerprints_nested_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-git-gitlink-untracked-"
        ) as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            make_repository(nested)
            (nested / "tracked.txt").write_bytes(b"committed")
            commit(nested, "initial")
            repository = root / "super"
            repository.mkdir()
            make_repository(repository)
            git(
                repository,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(nested),
                "module",
            )
            commit(repository, "initial submodule")
            clean = collect_git_state(repository)
            target = repository / "module" / "untracked.txt"
            target.write_bytes(b"first untracked content")
            first = collect_git_state(repository)
            target.write_bytes(b"second untracked content")

            second = collect_git_state(repository)

        self.assertFalse(clean.dirty)
        self.assertTrue(first.dirty)
        self.assertNotEqual(clean.fingerprint, first.fingerprint)
        self.assertNotEqual(first.fingerprint, second.fingerprint)
        self.assertIn(
            ("module", ChangeKind.MODIFIED, ChangeSource.WORKTREE),
            {(change.path, change.kind, change.source) for change in first.changes},
        )

    def test_untracked_depth_two_gitlink_is_detected_without_ignored_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-git-gitlink-depth-two-"
        ) as directory:
            root = Path(directory)
            deepest = root / "deepest"
            deepest.mkdir()
            make_repository(deepest)
            (deepest / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            (deepest / "tracked.txt").write_bytes(b"committed")
            commit(deepest, "initial")
            middle = root / "middle"
            middle.mkdir()
            make_repository(middle)
            git(
                middle,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(deepest),
                "deep",
            )
            commit(middle, "initial nested submodule")
            repository = root / "super"
            repository.mkdir()
            make_repository(repository)
            git(
                repository,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(middle),
                "middle",
            )
            git(
                repository / "middle",
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "update",
                "--init",
                "-q",
            )
            commit(repository, "initial nested submodule")
            clean = collect_git_state(repository)
            nested = repository / "middle" / "deep"
            (nested / "ignored").mkdir()
            (nested / "ignored" / "skip.txt").write_bytes(b"ignored")
            (nested / ".agent-state").mkdir()
            (nested / ".agent-state" / "state.json").write_bytes(b"state")
            ignored = collect_git_state(repository)
            target = nested / "untracked.txt"
            target.write_bytes(b"first untracked content")
            first = collect_git_state(repository)
            target.write_bytes(b"second untracked content")

            second = collect_git_state(repository)

        self.assertFalse(clean.dirty)
        self.assertFalse(ignored.dirty)
        self.assertEqual(clean.fingerprint, ignored.fingerprint)
        self.assertTrue(first.dirty)
        self.assertNotEqual(clean.fingerprint, first.fingerprint)
        self.assertNotEqual(first.fingerprint, second.fingerprint)
        self.assertIn(
            ("middle", ChangeKind.MODIFIED, ChangeSource.WORKTREE),
            {(change.path, change.kind, change.source) for change in first.changes},
        )

    def test_repository_root_with_newline_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-git-root-") as directory:
            repository = Path(directory) / "repository\n"
            repository.mkdir()
            make_repository(repository)
            (repository / "tracked.txt").write_bytes(b"tracked")
            commit(repository, "initial")

            state = collect_git_state(repository)

        self.assertEqual(state.root, repository.resolve())


if __name__ == "__main__":
    unittest.main()
