from __future__ import annotations

import unittest

from scripts.home_assistant.compare import compare_three_way
from scripts.home_assistant.models import DiffStatus, ResourceDocument


class TestHomeAssistantCompare(unittest.TestCase):
    def test_three_way_truth_table_clean(self) -> None:
        doc = ResourceDocument(kind="automation", key="a1", desired={"alias": "A"})
        res = compare_three_way(
            instance="test",
            baseline={"automation/a1": doc},
            git={"automation/a1": doc},
            live={"automation/a1": doc},
        )
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].status, DiffStatus.CLEAN)
        self.assertFalse(res.has_drift)
        self.assertFalse(res.has_conflicts)

    def test_three_way_truth_table_ui_experiment(self) -> None:
        b_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "Original"}
        )
        g_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "Original"}
        )
        l_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "UI Modified"}
        )

        res = compare_three_way(
            instance="test",
            baseline={"automation/a1": b_doc},
            git={"automation/a1": g_doc},
            live={"automation/a1": l_doc},
        )
        self.assertEqual(res.items[0].status, DiffStatus.EXPERIMENT)
        self.assertTrue(res.has_drift)
        self.assertFalse(res.has_conflicts)

    def test_three_way_truth_table_git_change(self) -> None:
        b_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "Original"}
        )
        g_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "Git Modified"}
        )
        l_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "Original"}
        )

        res = compare_three_way(
            instance="test",
            baseline={"automation/a1": b_doc},
            git={"automation/a1": g_doc},
            live={"automation/a1": l_doc},
        )
        self.assertEqual(res.items[0].status, DiffStatus.GIT_CHANGE)
        self.assertTrue(res.has_drift)
        self.assertFalse(res.has_conflicts)

    def test_three_way_truth_table_converged(self) -> None:
        b_doc = ResourceDocument(kind="automation", key="a1", desired={"alias": "Old"})
        g_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "New Same"}
        )
        l_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "New Same"}
        )

        res = compare_three_way(
            instance="test",
            baseline={"automation/a1": b_doc},
            git={"automation/a1": g_doc},
            live={"automation/a1": l_doc},
        )
        self.assertEqual(res.items[0].status, DiffStatus.CONVERGED)
        self.assertFalse(res.has_conflicts)

    def test_three_way_truth_table_conflict(self) -> None:
        b_doc = ResourceDocument(kind="automation", key="a1", desired={"alias": "Old"})
        g_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "Git Modified"}
        )
        l_doc = ResourceDocument(
            kind="automation", key="a1", desired={"alias": "UI Modified Differently"}
        )

        res = compare_three_way(
            instance="test",
            baseline={"automation/a1": b_doc},
            git={"automation/a1": g_doc},
            live={"automation/a1": l_doc},
        )
        self.assertEqual(res.items[0].status, DiffStatus.CONFLICT)
        self.assertTrue(res.has_conflicts)

    def test_additions_truth_table(self) -> None:
        doc = ResourceDocument(
            kind="automation", key="new_one", desired={"alias": "New"}
        )
        # New in Git only
        res_git = compare_three_way(
            instance="test", baseline={}, git={"automation/new_one": doc}, live={}
        )
        self.assertEqual(res_git.items[0].status, DiffStatus.GIT_CHANGE)

        # New in UI only
        res_ui = compare_three_way(
            instance="test", baseline={}, git={}, live={"automation/new_one": doc}
        )
        self.assertEqual(res_ui.items[0].status, DiffStatus.EXPERIMENT)

        # Added on both sides matching
        res_both = compare_three_way(
            instance="test",
            baseline={},
            git={"automation/new_one": doc},
            live={"automation/new_one": doc},
        )
        self.assertEqual(res_both.items[0].status, DiffStatus.CONVERGED)

    def test_deletions_truth_table(self) -> None:
        doc = ResourceDocument(kind="automation", key="del", desired={"alias": "Del"})
        # Deleted in Git
        res_git_del = compare_three_way(
            instance="test",
            baseline={"automation/del": doc},
            git={},
            live={"automation/del": doc},
        )
        self.assertEqual(res_git_del.items[0].status, DiffStatus.GIT_CHANGE)

        # Deleted in UI
        res_ui_del = compare_three_way(
            instance="test",
            baseline={"automation/del": doc},
            git={"automation/del": doc},
            live={},
        )
        self.assertEqual(res_ui_del.items[0].status, DiffStatus.EXPERIMENT)

        # Deleted in Git but modified in UI -> Conflict!
        mod_doc = ResourceDocument(
            kind="automation", key="del", desired={"alias": "Del But Modified"}
        )
        res_conflict = compare_three_way(
            instance="test",
            baseline={"automation/del": doc},
            git={},
            live={"automation/del": mod_doc},
        )
        self.assertEqual(res_conflict.items[0].status, DiffStatus.CONFLICT)

    def test_live_error_is_unknown_not_deletion(self) -> None:
        b_doc = ResourceDocument(
            kind="automation", key="err", desired={"alias": "Test"}
        )
        g_doc = ResourceDocument(
            kind="automation", key="err", desired={"alias": "Test"}
        )
        res = compare_three_way(
            instance="test",
            baseline={"automation/err": b_doc},
            git={"automation/err": g_doc},
            live={},
            errors={"automation/err": "Connection timeout"},
        )
        self.assertEqual(res.items[0].status, DiffStatus.UNKNOWN)
        self.assertIn("Connection timeout", res.items[0].details)


if __name__ == "__main__":
    unittest.main()
