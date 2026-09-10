from __future__ import annotations

import unittest
from pathlib import Path

from scripts.roku_bridge import render_bulbs

ROOT = Path(__file__).resolve().parents[1]


class RokuBridgeContractTests(unittest.TestCase):
    def test_broker_user_is_scoped_to_roku_and_discovery(self) -> None:
        appliance = (ROOT / "flake/modules/adguard-netbird-appliance.nix").read_text()

        self.assertIn("roku-bridge = {", appliance)
        self.assertIn(
            'passwordFile = "/persist/secrets/mosquitto-roku-bridge-password"',
            appliance,
        )
        self.assertIn('"readwrite homeassistant/#"', appliance)
        self.assertIn('"readwrite roku/#"', appliance)
        self.assertIn(
            '"/persist/secrets/mosquitto-roku-bridge-password"',
            appliance,
        )

    def test_bridge_runs_as_own_user_with_staged_secrets(self) -> None:
        appliance = (ROOT / "flake/modules/adguard-netbird-appliance.nix").read_text()

        self.assertIn("users.users.roku-bridge", appliance)
        self.assertIn("systemd.services.roku-bridge-secrets", appliance)
        self.assertIn(
            "/persist/secrets/roku-bridge-bulbs.yaml",
            appliance,
        )
        self.assertIn("systemd.services.roku-bridge", appliance)
        self.assertIn('User = "roku-bridge"', appliance)
        self.assertIn("--config /var/lib/roku-bridge/bulbs.yaml", appliance)
        self.assertIn("/light/{slug}/set", appliance)
        self.assertIn("/light/{slug}/state", appliance)
        self.assertIn("device_request", appliance)

    def test_ci_provisions_bridge_secrets_before_activation(self) -> None:
        pipeline = (ROOT / ".gitlab-ci.yml").read_text()

        self.assertIn("python -m scripts.roku_bridge", pipeline)
        self.assertIn("roku-bridge-bulbs.yaml", pipeline)
        self.assertIn("mosquitto-roku-bridge-password", pipeline)
        self.assertIn("printf '%s' \"$ROKU_BRIDGE_MQTT_PASSWORD\"", pipeline)
        self.assertIn("systemctl is-active mosquitto zigbee2mqtt roku-bridge", pipeline)

    def test_secret_renderer_emits_validated_bulbs_yaml(self) -> None:
        rendered = render_bulbs(
            '[{"name": "Desk Lamp", "mac": "7C67AB0A83AB", '
            '"ip": "10.0.20.117", "enr": "0123456789ABCDEF"}]'
        )

        self.assertEqual(
            rendered,
            "bulbs:\n"
            "  - name: Desk Lamp\n"
            "    mac: 7C67AB0A83AB\n"
            "    ip: 10.0.20.117\n"
            "    enr: 0123456789ABCDEF\n",
        )
        with self.assertRaises(ValueError):
            render_bulbs(
                '[{"name": "Bad", "mac": "XYZ", "ip": "10.0.20.117", "enr": "short"}]'
            )
        with self.assertRaises(ValueError):
            render_bulbs("not json")


if __name__ == "__main__":
    unittest.main()
