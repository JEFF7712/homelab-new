"""Local unit tests for the Wyse 5070 Extended T1 mount.

Run from repo root:
  PYTHONPATH=3d-prints python -m unittest wyse5070_extended_t1.test_model -v
"""

from __future__ import annotations

import unittest

from wyse5070_extended_t1 import model, params


class TestEnvelopes(unittest.TestCase):
    def test_device_spec_uses_conservative_width(self) -> None:
        self.assertAlmostEqual(params.DEVICE_X_MM, 184.0)
        self.assertAlmostEqual(params.DEVICE_Y_MM, 66.0)
        self.assertAlmostEqual(params.DEVICE_Z_MM, 184.0)

    def test_tray_height_matches_u_target(self) -> None:
        env = params.tray_envelope()
        self.assertAlmostEqual(env.outer_y_mm, params.TARGET_HEIGHT_MM)
        pocket_y = params.TRAY_FLOOR_MM + params.DEVICE_Y_MM + params.FIT_CLEARANCE_MM
        self.assertLessEqual(pocket_y, params.TARGET_HEIGHT_MM)

    def test_fits_rack_and_bed(self) -> None:
        env = params.tray_envelope()
        self.assertTrue(params.fits_rack(env), f"envelope {env} exceeds T1")
        self.assertTrue(params.fits_bed(), "ear span exceeds A1 bed")

    def test_reference_ear_span_matches_existing_prints(self) -> None:
        # Existing STLs measure 250 to 254mm wide. New ears must stay compatible.
        self.assertGreaterEqual(params.EAR_SPAN_MM, 250.0)
        self.assertLessEqual(params.EAR_SPAN_MM, params.BED_X_MM)

    def test_hole_pattern_matches_deskpi_panel(self) -> None:
        # Measured from DeskPi's 1U blank panel 3MF: slots 10mm from each
        # outer edge, 30mm vertical spacing.
        self.assertAlmostEqual(params.HOLE_EDGE_OFFSET_MM, 10.0)
        self.assertAlmostEqual(params.HOLE_Y_SPACING_MM, 30.0)
        self.assertEqual(model.ear_hole_x_positions(), [10.0, 244.0])
        ymid = params.TARGET_HEIGHT_MM / 2.0
        self.assertEqual(model.ear_hole_y_positions(), [ymid - 15.0, ymid + 15.0])

    def test_tray_centered_with_outboard_ears(self) -> None:
        env = params.tray_envelope()
        ox = params.tray_offset_x_mm()
        self.assertGreater(ox, 0)
        self.assertAlmostEqual(ox + env.outer_x_mm + ox, params.EAR_SPAN_MM)

    def test_waffle_floor_needs_no_foot_data(self) -> None:
        cells = model.waffle_cells()
        self.assertGreater(len(cells), 20)
        pitch = params.WAFFLE_CELL_MM + params.WAFFLE_RIB_MM
        self.assertLess(params.WAFFLE_DEPTH_MM, params.TRAY_FLOOR_MM)
        xs = [c[0] for c in cells]
        self.assertGreaterEqual(min(xs) - params.WAFFLE_CELL_MM / 2.0, 0)
        self.assertLess(pitch, 25.0)

    def test_validate_passes_without_measurements(self) -> None:
        self.assertEqual(model.validate(), [])


if __name__ == "__main__":
    unittest.main()
