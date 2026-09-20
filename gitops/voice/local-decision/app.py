from __future__ import annotations

import json
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from rlcd.decide import ChoiceQ, Decider

MODEL_NAME = "local-qwen3-0.6b-rlcd-decision"
MAX_BODY_BYTES = 65_536
MAX_QUESTIONS = 16
MAX_STATE_CHARS = 8_192


class DecisionService:
    def __init__(self, model_dir: str) -> None:
        self._decider = Decider.load(model_dir, device="cpu", fast=False)
        self._inference_lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        self._requests = 0
        self._failures = 0
        self._latency_seconds = 0.0

    def decide(self, payload: Any) -> dict[str, Any]:
        state, names, questions = parse_request(payload)
        started = time.monotonic()
        try:
            with self._inference_lock:
                raw_answers = self._decider.ask(
                    state,
                    questions,
                    max_state_tokens=512,
                    max_question_tokens=256,
                    batch_size=16,
                )
        except Exception:
            with self._metrics_lock:
                self._failures += 1
            raise
        finally:
            elapsed = time.monotonic() - started
            with self._metrics_lock:
                self._requests += 1
                self._latency_seconds += elapsed

        answers: dict[str, Any] = {}
        for name, question, raw in zip(names, questions, raw_answers, strict=True):
            selected = question.options.index(raw["value"])
            choice_names = list(payload["questions"][name]["criteria"])
            answers[name] = {
                "type": "choice",
                "choice": choice_names[selected],
                "confidence": raw["confidence"],
            }
        return {"model": MODEL_NAME, "answers": answers}

    def metrics(self) -> str:
        with self._metrics_lock:
            requests = self._requests
            failures = self._failures
            latency = self._latency_seconds
        return (
            "# HELP jarvis_local_decision_requests_total Decision requests processed.\n"
            "# TYPE jarvis_local_decision_requests_total counter\n"
            f"jarvis_local_decision_requests_total {requests}\n"
            "# HELP jarvis_local_decision_failures_total Failed decision requests.\n"
            "# TYPE jarvis_local_decision_failures_total counter\n"
            f"jarvis_local_decision_failures_total {failures}\n"
            "# HELP jarvis_local_decision_latency_seconds_total Total inference latency.\n"
            "# TYPE jarvis_local_decision_latency_seconds_total counter\n"
            f"jarvis_local_decision_latency_seconds_total {latency:.9f}\n"
        )


def parse_request(payload: Any) -> tuple[str, list[str], list[ChoiceQ]]:
    if not isinstance(payload, dict):
        raise TypeError("request must be an object")
    state = payload.get("state")
    raw_questions = payload.get("questions")
    if not isinstance(state, str) or not state.strip() or len(state) > MAX_STATE_CHARS:
        raise ValueError("state must be a non-empty bounded string")
    if (
        not isinstance(raw_questions, dict)
        or not 1 <= len(raw_questions) <= MAX_QUESTIONS
    ):
        raise ValueError("questions must be a bounded non-empty object")

    names: list[str] = []
    questions: list[ChoiceQ] = []
    for name, spec in raw_questions.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise TypeError("question names and definitions must be objects")
        criteria = spec.get("criteria")
        instructions = spec.get("instructions")
        if spec.get("type") != "choice" or not isinstance(instructions, str):
            raise ValueError("only choice questions are supported")
        if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 26:
            raise ValueError("choice criteria must contain 2 to 26 options")
        options: list[str] = []
        for key, description in criteria.items():
            if not isinstance(key, str) or not isinstance(description, str):
                raise TypeError("choice keys and descriptions must be strings")
            options.append(f"{key}: {description}")
        names.append(name)
        questions.append(ChoiceQ(instructions, options))
    return state.strip(), names, questions


class Handler(BaseHTTPRequestHandler):
    server: DecisionHTTPServer

    def do_GET(self) -> None:
        if self.path in {"/healthz", "/readyz"}:
            self._send_json(HTTPStatus.OK, {"status": "ok", "model": MODEL_NAME})
            return
        if self.path == "/metrics":
            body = self.server.service.metrics().encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/v1/systemone":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY_BYTES:
                raise ValueError("request body size is invalid")
            payload = json.loads(self.rfile.read(length))
            result = self.server.service.decide(payload)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except Exception:  # noqa: BLE001
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "inference failed"}
            )
            return
        self._send_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DecisionHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: DecisionService) -> None:
        super().__init__(address, Handler)
        self.service = service


def main() -> None:
    model_dir = os.environ["MODEL_DIR"]
    port = int(os.environ.get("PORT", "8080"))
    service = DecisionService(model_dir)
    DecisionHTTPServer(("0.0.0.0", port), service).serve_forever()


if __name__ == "__main__":
    main()
