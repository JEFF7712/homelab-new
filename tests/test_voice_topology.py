from __future__ import annotations

import unittest

from scripts import voice_topology


class VoiceTopologyTest(unittest.TestCase):
    def test_report_contains_gateway_order_and_service_targets(self) -> None:
        report = voice_topology.build_report()
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(
            report["desired"]["gateways"]["stt"]["backends"][0]["name"], "nemotron"
        )
        self.assertEqual(
            report["desired"]["gateways"]["tts"]["backends"][1]["name"], "piper"
        )
        self.assertEqual(
            report["desired"]["ha_pipeline"]["conversation_agent"], "Jarvis Jev Router"
        )
        self.assertEqual(report["live"]["status"], "unknown")

    def test_desired_invariants_pass(self) -> None:
        self.assertEqual(voice_topology.check(voice_topology.build_report()), [])


if __name__ == "__main__":
    unittest.main()
