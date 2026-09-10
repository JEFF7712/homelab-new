from __future__ import annotations

import json
import os
import sys


def render_secret(network_key: str, mqtt_password: str) -> str:
    if len(network_key) != 32 or any(
        character not in "0123456789abcdefABCDEF" for character in network_key
    ):
        raise ValueError("ZIGBEE2MQTT_NETWORK_KEY must be 32 hexadecimal characters")

    return json.dumps(
        {
            "mqtt_user": "zigbee2mqtt",
            "mqtt_password": mqtt_password,
            "network_key": list(bytes.fromhex(network_key)),
        }
    )


def main() -> int:
    try:
        secret = render_secret(
            os.environ["ZIGBEE2MQTT_NETWORK_KEY"],
            os.environ["ZIGBEE2MQTT_MQTT_PASSWORD"],
        )
    except (KeyError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2

    print(secret)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
