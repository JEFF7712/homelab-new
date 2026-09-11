"""Repo gate for the Wyse 5070 Extended T1 mount (offline, no CAD kernel)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "3d-prints" / "wyse5070_extended_t1" / "params.py"


def load_params():  # type: ignore[no-untyped-def]
    import sys

    name = "wyse5070_params"
    spec = importlib.util.spec_from_file_location(name, PARAMS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


params = load_params()


class Wyse5070MountTests(unittest.TestCase):
    def test_params_source_exists(self) -> None:
        self.assertTrue(PARAMS_PATH.is_file(), f"missing {PARAMS_PATH}")

    def test_device_spec_matches_dell(self) -> None:
        self.assertAlmostEqual(params.DEVICE_X_MM, 184.0)
        self.assertAlmostEqual(params.DEVICE_Y_MM, 66.0)
        self.assertAlmostEqual(params.DEVICE_Z_MM, 184.0)

    def test_tray_fits_t1_and_a1(self) -> None:
        env = params.tray_envelope()
        self.assertTrue(params.fits_rack(env), f"envelope {env} exceeds T1")
        self.assertTrue(params.fits_bed(), "ear span exceeds A1 bed")

    def test_ear_span_matches_existing_prints(self) -> None:
        self.assertGreaterEqual(params.EAR_SPAN_MM, 250.0)
        self.assertLessEqual(params.EAR_SPAN_MM, params.BED_X_MM)

    def test_hole_pattern_matches_deskpi_panel(self) -> None:
        self.assertAlmostEqual(params.HOLE_EDGE_OFFSET_MM, 10.0)
        self.assertAlmostEqual(params.HOLE_Y_SPACING_MM, 30.0)
        self.assertAlmostEqual(params.HOLE_DIA_MM, 5.0)

    def test_waffle_floor_is_sane(self) -> None:
        self.assertLess(params.WAFFLE_DEPTH_MM, params.TRAY_FLOOR_MM)
        self.assertGreater(params.WAFFLE_CELL_MM, 0)
        self.assertGreater(params.WAFFLE_RIB_MM, 0)


if __name__ == "__main__":
    unittest.main()
