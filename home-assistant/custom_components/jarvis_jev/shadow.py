from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

LOCAL_MODEL = "local-qwen3-0.6b-rlcd-decision"


@dataclass(frozen=True)
class ShadowResult:
    payload: dict[str, Any] | None
    latency_seconds: float
    error: str | None = None


async def request_shadow(
    session: Any,
    url: str,
    request: dict[str, Any],
    timeout_seconds: float,
) -> ShadowResult:
    started = time.monotonic()
    try:
        async with asyncio.timeout(timeout_seconds):
            async with session.post(url, json=request) as response:
                if response.status != 200:
                    return ShadowResult(
                        None,
                        time.monotonic() - started,
                        f"http_{response.status}",
                    )
                payload = await response.json()
        if not isinstance(payload, dict) or payload.get("model") != LOCAL_MODEL:
            return ShadowResult(
                None,
                time.monotonic() - started,
                "malformed_response",
            )
        return ShadowResult(payload, time.monotonic() - started)
    except TimeoutError:
        return ShadowResult(None, time.monotonic() - started, "timeout")
    except Exception:  # noqa: BLE001
        return ShadowResult(None, time.monotonic() - started, "request_failed")


def compare_answers(authoritative: Any, shadow: Any) -> tuple[int, int, bool | None]:
    if not isinstance(authoritative, dict) or not isinstance(shadow, dict):
        return 0, 0, None
    authoritative_answers = authoritative.get("answers")
    shadow_answers = shadow.get("answers")
    if not isinstance(authoritative_answers, dict) or not isinstance(
        shadow_answers, dict
    ):
        return 0, 0, None

    compared = 0
    agreed = 0
    for name, expected in authoritative_answers.items():
        observed = shadow_answers.get(name)
        if not isinstance(expected, dict) or not isinstance(observed, dict):
            continue
        expected_choice = expected.get("choice")
        observed_choice = observed.get("choice")
        if not isinstance(expected_choice, str) or not isinstance(observed_choice, str):
            continue
        compared += 1
        agreed += expected_choice == observed_choice
    return agreed, compared, agreed == compared if compared else None
