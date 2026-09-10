from __future__ import annotations

import unittest
from pathlib import Path

from scripts.zigbee_gateway import render_secret

ROOT = Path(__file__).resolve().parents[1]


class ZigbeeGatewayContractTests(unittest.TestCase):
    def test_coordinator_is_stable_and_state_is_persistent(self) -> None:
        appliance = (ROOT / "flake/modules/adguard-netbird-appliance.nix").read_text()

        self.assertIn("services.zigbee2mqtt", appliance)
        self.assertIn('adapter = "ember"', appliance)
        self.assertIn(
            "usb-SONOFF_SONOFF_Dongle_Lite_MG21_048030cb64a2ef11b809926661ce3355-if00-port0",
            appliance,
        )
        self.assertIn('network_key = "!secret.yaml network_key"', appliance)
        self.assertIn('"/var/lib/zigbee2mqtt"', appliance)

    def test_ci_provisions_runtime_secrets_before_activation(self) -> None:
        pipeline = (ROOT / ".gitlab-ci.yml").read_text()

        self.assertIn("deploy_zigbee_gateway:", pipeline)
        self.assertIn("python -m scripts.zigbee_gateway", pipeline)
        self.assertIn("zigbee2mqtt-secret.yaml", pipeline)
        self.assertIn("mosquitto-home-assistant-password", pipeline)
        self.assertIn('printf \'%s\' "$HOME_ASSISTANT_MQTT_PASSWORD"', pipeline)
        self.assertIn("systemctl is-active mosquitto zigbee2mqtt", pipeline)

    def test_secret_renderer_emits_a_stable_network_key(self) -> None:
        secret = render_secret("00" * 16, "mqtt-password")

        self.assertEqual(
            secret,
            '{"mqtt_user": "zigbee2mqtt", "mqtt_password": "mqtt-password", '
            '"network_key": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}',
        )
        with self.assertRaises(ValueError):
            render_secret("not-a-network-key", "mqtt-password")


if __name__ == "__main__":
    unittest.main()
