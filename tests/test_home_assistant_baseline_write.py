"""Regression tests for cluster baseline writes.

The baseline payload exceeds 128KB, so ``kubectl apply`` (which mirrors the
whole manifest into the ``last-applied-configuration`` annotation) breaches
the 256KB annotation cap. Saves must use replace-or-create instead.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from scripts.home_assistant.client import HomeAssistantClient

ANNOTATION_LIMIT = 262144


def _run_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    res = MagicMock()
    res.returncode = returncode
    res.stdout = stdout
    res.stderr = stderr
    return res


def _large_baseline(size: int = 200_000) -> dict:
    return {
        "content_hash": "abc123",
        "source_commit": "deadbeef",
        "resources": {"automation/x": {"padding": "p" * size}},
    }


class BaselineWriteTest(unittest.TestCase):
    def _client(self) -> HomeAssistantClient:
        return HomeAssistantClient(base_url="http://127.0.0.1:8123", token="t")

    def test_save_uses_replace_not_apply(self) -> None:
        client = self._client()
        baseline = _large_baseline()
        readback = json.dumps(baseline)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _run_result(0, stdout="replaced"),
                _run_result(
                    0,
                    stdout=json.dumps({"data": {"baseline.json": readback}}),
                ),
            ]
            client.save_cluster_baseline("test-instance", baseline)
        commands = [call.args[0][:2] for call in mock_run.call_args_list]
        self.assertIn(["kubectl", "replace"], commands)
        self.assertNotIn(["kubectl", "apply"], commands)

    def test_save_falls_back_to_create_when_missing(self) -> None:
        client = self._client()
        baseline = _large_baseline()
        readback = json.dumps(baseline)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _run_result(1, stderr="configmaps not found"),
                _run_result(0, stdout="created"),
                _run_result(
                    0,
                    stdout=json.dumps({"data": {"baseline.json": readback}}),
                ),
            ]
            client.save_cluster_baseline("test-instance", baseline)
        commands = [call.args[0][:2] for call in mock_run.call_args_list]
        self.assertEqual(
            [c[1] for c in commands],
            ["replace", "create", "-n"],
        )

    def test_manifest_annotations_stay_under_cap(self) -> None:
        client = self._client()
        baseline = _large_baseline()
        seen_manifests: list[dict] = []
        readback = json.dumps(baseline)

        def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
            if cmd[:2] in (["kubectl", "replace"], ["kubectl", "create"]):
                seen_manifests.append(json.loads(kwargs["input"]))  # type: ignore[arg-type]
                return _run_result(0, stdout="ok")
            return _run_result(
                0, stdout=json.dumps({"data": {"baseline.json": readback}})
            )

        with patch("subprocess.run", side_effect=fake_run):
            client.save_cluster_baseline("test-instance", baseline)
        self.assertEqual(len(seen_manifests), 1)
        annotations = seen_manifests[0]["metadata"].get("annotations", {})
        self.assertNotIn(
            "kubectl.kubernetes.io/last-applied-configuration", annotations
        )
        total = sum(len(k) + len(v) for k, v in annotations.items())
        self.assertLess(total, ANNOTATION_LIMIT)


if __name__ == "__main__":
    unittest.main()
