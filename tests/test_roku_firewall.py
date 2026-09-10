from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TFVARS = ROOT / "tofu/opnsense/homelab.auto.tfvars"


def rule_block(name: str) -> str:
    text = TFVARS.read_text()
    start = text.index(f"{name} = {{")
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start : pos + 1]
    raise AssertionError(f"unbalanced braces in rule {name}")


class RokuBulbFirewallTests(unittest.TestCase):
    def test_pinhole_precedes_private_block(self) -> None:
        pinhole = rule_block("infrastructure-allow-roku-bulbs")
        block = rule_block("infrastructure-block-private")

        def seq(block_text: str) -> int:
            match = re.search(r"sequence\s*=\s*(\d+)", block_text)
            self.assertIsNotNone(match)
            assert match is not None
            return int(match.group(1))

        self.assertLess(seq(pinhole), seq(block))

    def test_pinhole_is_narrow(self) -> None:
        pinhole = rule_block("infrastructure-allow-roku-bulbs")

        self.assertIn('"pass"', pinhole)
        self.assertIn('"TCP"', pinhole)
        self.assertIn("10.0.30.10/32", pinhole)
        self.assertIn('"88"', pinhole)
        self.assertRegex(pinhole, r"quick\s+= true")


if __name__ == "__main__":
    unittest.main()
