from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "home-assistant" / "custom_components" / "jarvis_jev"


def load_shadow():
    package = types.ModuleType("jarvis_jev")
    package.__path__ = [str(PACKAGE_DIR)]
    sys.modules["jarvis_jev"] = package
    spec = importlib.util.spec_from_file_location(
        "jarvis_jev.shadow", PACKAGE_DIR / "shadow.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["jarvis_jev.shadow"] = module
    spec.loader.exec_module(module)
    return module


shadow = load_shadow()


class FakeResponse:
    def __init__(self, status: int, payload: object, delay: float = 0) -> None:
        self.status = status
        self.payload = payload
        self.delay = delay

    async def __aenter__(self):
        if self.delay:
            await asyncio.sleep(self.delay)
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def json(self) -> object:
        return self.payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def post(self, url: str, json: object) -> FakeResponse:
        return self.response


def payload(choice: str) -> dict:
    return {
        "model": shadow.LOCAL_MODEL,
        "answers": {
            "action": {
                "type": "choice",
                "choice": choice,
                "confidence": 0.8,
            }
        },
    }


class JevShadowTest(unittest.IsolatedAsyncioTestCase):
    async def test_success_returns_local_payload(self) -> None:
        result = await shadow.request_shadow(
            FakeSession(FakeResponse(200, payload("turn_off"))),
            "http://local",
            {"state": "private transcript"},
            1,
        )
        self.assertIsNone(result.error)
        self.assertEqual(result.payload["answers"]["action"]["choice"], "turn_off")

    async def test_timeout_and_malformed_output_are_isolated(self) -> None:
        timeout = await shadow.request_shadow(
            FakeSession(FakeResponse(200, payload("turn_off"), delay=0.02)),
            "http://local",
            {},
            0.001,
        )
        malformed = await shadow.request_shadow(
            FakeSession(FakeResponse(200, {"model": "wrong"})),
            "http://local",
            {},
            1,
        )
        self.assertEqual(timeout.error, "timeout")
        self.assertEqual(malformed.error, "malformed_response")

    def test_comparison_reports_field_agreement_without_transcript(self) -> None:
        authoritative = {
            "answers": {
                "action": {"choice": "turn_off"},
                "target": {"choice": "kitchen_lights"},
            }
        }
        local = payload("turn_off")
        local["answers"]["target"] = {"choice": "bedroom_lights"}
        self.assertEqual(
            shadow.compare_answers(authoritative, local),
            (1, 2, False),
        )


if __name__ == "__main__":
    unittest.main()
