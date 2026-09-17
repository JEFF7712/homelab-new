from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_exporter_module() -> dict:
    docs = list(
        yaml.safe_load_all(
            (REPO_ROOT / "gitops" / "voice" / "exporter.yaml").read_text()
        )
    )
    code = next(
        doc["data"]["exporter.py"]
        for doc in docs
        if doc.get("kind") == "ConfigMap"
        and doc["metadata"]["name"] == "jarvis-exporter-code"
    )
    module: dict = {"__name__": "jarvis_exporter_under_test"}
    exec(compile(code, "exporter.py", "exec"), module)
    return module


EXPORTER = load_exporter_module()


class ExporterRenderTest(unittest.TestCase):
    def test_counter_render(self) -> None:
        counter = EXPORTER["Counter"]("demo_total", "Demo.", ("satellite",))
        counter.labels("x").inc()
        counter.labels("x").inc(2.0)
        text = "\n".join(counter.render())
        self.assertIn('demo_total{satellite="x"} 3.0', text)

    def test_histogram_buckets(self) -> None:
        histogram = EXPORTER["Histogram"]("demo_seconds", "Demo.", ("satellite",))
        bound = histogram.labels("x")
        bound.observe(0.3)
        bound.observe(5.0)
        text = "\n".join(histogram.render())
        self.assertIn('demo_seconds_bucket{satellite="x",le="0.25"} 0', text)
        self.assertIn('demo_seconds_bucket{satellite="x",le="0.5"} 1', text)
        self.assertIn('demo_seconds_bucket{satellite="x",le="+Inf"} 2', text)
        self.assertIn('demo_seconds_count{satellite="x"} 2', text)

    def test_entity_ids_from(self) -> None:
        parse = EXPORTER["entity_ids_from"]
        self.assertEqual(parse({"entity_id": "light.a"}), ["light.a"])
        self.assertEqual(parse({"entity_id": ["light.a", 7]}), ["light.a"])
        self.assertEqual(parse({}), [])


class TurnTrackerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = EXPORTER["Metrics"]("sat")
        self.tracker = EXPORTER["TurnTracker"](self.metrics, "sat")

    def drive(self, *states: str, start: float = 1000.0, step: float = 1.0) -> None:
        now = start
        for state in states:
            self.tracker.observe_state(
                state, now, lambda areas: areas[0] if areas else "unknown"
            )
            now += step

    def test_happy_path_records_all_stages(self) -> None:
        self.drive("listening", "processing", "responding", "idle")
        text = self.metrics.render()
        self.assertIn('jarvis_requests_total{satellite="sat"} 1.0', text)
        self.assertIn('jarvis_stt_latency_seconds_count{satellite="sat"} 1', text)
        self.assertIn('jarvis_llm_latency_seconds_count{satellite="sat"} 1', text)
        self.assertIn('jarvis_tts_latency_seconds_count{satellite="sat"} 1', text)
        self.assertIn('jarvis_requests_by_room_total{room="unknown"} 1.0', text)
        self.assertNotIn('jarvis_failed_requests_total{satellite="sat"', text)

    def test_abandoned_turn_counts_failed(self) -> None:
        self.drive("listening", "processing", "idle")
        text = self.metrics.render()
        self.assertIn("jarvis_requests_total", text)
        self.assertIn(
            'jarvis_failed_requests_total{satellite="sat",stage="processing"} 1.0', text
        )
        self.assertNotIn('jarvis_requests_total{satellite="sat"} 1.0', text)

    def test_tool_calls_only_count_while_processing(self) -> None:
        self.tracker.observe_state("listening", 1000.0, None)
        self.tracker.observe_service_call(["light.a"])
        self.tracker.observe_state("processing", 1001.0, None)
        self.tracker.observe_service_call(["light.a", "light.b"])
        text = self.metrics.render()
        self.assertIn('jarvis_tool_calls_total{satellite="sat"} 1.0', text)

    def test_room_from_first_area(self) -> None:
        areas = {"light.a": "kitchen", "light.b": "living_room"}
        self.tracker.observe_state("listening", 1000.0, None)
        self.tracker.observe_state("processing", 1001.0, None)
        self.tracker.observe_service_call(["light.b"])
        self.tracker.observe_state("responding", 1002.0, None)
        self.tracker.observe_state(
            "idle",
            1003.0,
            lambda ids: areas.get(ids[0], "unknown") if ids else "unknown",
        )
        text = self.metrics.render()
        self.assertIn('jarvis_requests_by_room_total{room="living_room"} 1.0', text)

    def test_fast_turn_records_fast_class(self) -> None:
        self.drive("listening", "processing", "responding", "idle")
        text = self.metrics.render()
        self.assertIn(
            'jarvis_turn_speed_class_total{satellite="sat",class="fast"} 1.0', text
        )

    def test_slow_turn_records_slow_class(self) -> None:
        self.drive("listening", "processing", "responding", "idle", step=3.0)
        text = self.metrics.render()
        self.assertIn(
            'jarvis_turn_speed_class_total{satellite="sat",class="slow"} 1.0', text
        )

    def test_speed_threshold_is_configurable(self) -> None:
        metrics = EXPORTER["Metrics"]("sat")
        tracker = EXPORTER["TurnTracker"](metrics, "sat", fast_max_seconds=10.0)
        now = 1000.0
        for state in ("listening", "processing", "responding", "idle"):
            tracker.observe_state(state, now, None)
            now += 3.0
        text = metrics.render()
        self.assertIn(
            'jarvis_turn_speed_class_total{satellite="sat",class="fast"} 1.0', text
        )

    def test_seed_suppresses_partial_turn(self) -> None:
        self.tracker.seed("processing")
        self.tracker.observe_state("responding", 1001.0, None)
        self.tracker.observe_state("idle", 1002.0, None)
        text = self.metrics.render()
        self.assertNotIn('jarvis_requests_total{satellite="sat"} 1.0', text)


if __name__ == "__main__":
    unittest.main()
