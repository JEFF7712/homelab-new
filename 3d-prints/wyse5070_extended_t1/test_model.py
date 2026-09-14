from __future__ import annotations

import unittest

from wyse5070_extended_t1 import model, params


class TestCradleGeometry(unittest.TestCase):
    def test_extended_device_envelope(self) -> None:
        self.assertEqual(
            (
                params.DEVICE_X_MM,
                params.DEVICE_BODY_Y_MM,
                params.DEVICE_Y_MM,
                params.DEVICE_Z_MM,
            ),
            (184.0, 55.9, 59.5, 184.0),
        )
        self.assertAlmostEqual(params.FOOT_HEIGHT_MM, 3.6)

    def test_fits_rack_and_a1_bed(self) -> None:
        self.assertTrue(params.fits_rack())
        self.assertTrue(params.fits_bed())
        self.assertLessEqual(params.body_width_mm(), params.RACK_INTERNAL_WIDTH_MM)

    def test_device_has_air_space_below_and_above(self) -> None:
        self.assertGreaterEqual(params.LOWER_AIR_GAP_MM, 6.0)
        self.assertGreater(params.TOP_CLEARANCE_MM, 0)
        self.assertLessEqual(
            params.top_lip_y_mm() + params.TOP_LIP_THICKNESS_MM,
            params.PANEL_HEIGHT_MM,
        )
        self.assertAlmostEqual(
            params.top_lip_y_mm()
            - (
                params.device_floor_y_mm()
                + params.DEVICE_Y_MM
                - params.FOOT_POCKET_DEPTH_MM
            ),
            params.TOP_CLEARANCE_MM,
        )
        self.assertGreaterEqual(params.TOP_LIP_MM, 6.0)
        self.assertGreaterEqual(params.TOP_LIP_THICKNESS_MM, 4.0)
        self.assertGreaterEqual(params.SIDE_VENT_TOP_RIB_MM, 10.0)

    def test_four_slots_repeat_the_reference_one_u_pattern(self) -> None:
        self.assertEqual(model.ear_slot_x_positions(), [10.0, 244.0])
        self.assertEqual(model.ear_slot_y_positions(), [7.0, 37.0, 51.0, 81.0])
        self.assertEqual(params.SLOT_WIDTH_MM, 7.0)
        self.assertEqual(params.SLOT_HEIGHT_MM, 13.0)
        for y in model.ear_slot_y_positions():
            self.assertGreaterEqual(y - params.SLOT_HEIGHT_MM / 2, 0)
            self.assertLessEqual(y + params.SLOT_HEIGHT_MM / 2, params.PANEL_HEIGHT_MM)

    def test_support_rails_hold_both_device_edges(self) -> None:
        ranges = model.support_rail_x_ranges()
        self.assertEqual(len(ranges), 2)
        self.assertAlmostEqual(ranges[0][1] - ranges[0][0], params.SUPPORT_RAIL_MM)
        self.assertAlmostEqual(ranges[1][1] - ranges[1][0], params.SUPPORT_RAIL_MM)
        self.assertGreater(ranges[1][0] - ranges[0][1], 140.0)

    def test_two_tie_locations_clear_front_and_rear(self) -> None:
        self.assertEqual(len(params.TIE_SLOT_Z_POSITIONS_MM), 2)
        for z in params.TIE_SLOT_Z_POSITIONS_MM:
            self.assertGreater(z - params.TIE_SLOT_Z_MM / 2, params.PANEL_THICKNESS_MM)
            self.assertLess(z + params.TIE_SLOT_Z_MM / 2, params.RAIL_DEPTH_MM)

    def test_side_vents_preserve_structural_ribs(self) -> None:
        vents = model.side_vent_z_ranges()
        self.assertEqual(len(vents), params.SIDE_VENT_COUNT)
        self.assertGreaterEqual(
            vents[0][0],
            params.PANEL_THICKNESS_MM + params.SIDE_VENT_FRONT_MARGIN_MM,
        )
        self.assertLessEqual(
            vents[-1][1],
            params.RAIL_DEPTH_MM
            - params.RETAINER_DEPTH_MM
            - params.SIDE_VENT_REAR_MARGIN_MM,
        )
        for (_, previous_end), (next_start, _) in zip(vents, vents[1:]):
            self.assertGreater(next_start - previous_end, 8.0)
        self.assertLessEqual(params.SIDE_VENT_DEPTH_MM, 12.0)

    def test_capture_tabs_are_segmented_and_clear_the_rear(self) -> None:
        tabs = model.capture_tab_z_ranges()
        self.assertEqual(len(tabs), 3)
        self.assertGreater(tabs[0][0], params.PANEL_THICKNESS_MM)
        self.assertLess(tabs[-1][1], params.RAIL_DEPTH_MM)
        for (_, previous_end), (next_start, _) in zip(tabs, tabs[1:]):
            self.assertGreater(next_start - previous_end, 20.0)

    def test_retainer_uses_m3_screws_and_insert_depth(self) -> None:
        self.assertGreater(params.RETAINER_SCREW_DIA_MM, 3.0)
        self.assertLess(params.RETAINER_SCREW_DIA_MM, params.RETAINER_INSERT_DIA_MM)
        self.assertLess(params.RETAINER_INSERT_DEPTH_MM, params.SUPPORT_RAIL_MM)
        self.assertLess(params.RETAINER_RAIL_HEIGHT_MM, params.RETAINER_HEIGHT_MM)
        self.assertGreaterEqual(params.RETAINER_END_PAD_MM, 20.0)

    def test_measured_foot_offsets_are_recorded(self) -> None:
        self.assertEqual((params.FOOT_X_MM, params.FOOT_Z_MM), (5.8, 20.0))
        self.assertEqual(params.FOOT_INSET_X_MM, 10.0)
        self.assertEqual(params.FOOT_INSET_FRONT_MM, 24.8)
        self.assertEqual(params.FOOT_INSET_REAR_MM, 9.5)
        self.assertEqual(params.FOOT_ROW_SPACING_Z_MM, 128.7)
        inferred_rear = (
            params.DEVICE_Z_MM
            - params.FOOT_INSET_FRONT_MM
            - params.FOOT_ROW_SPACING_Z_MM
            - params.FOOT_Z_MM
        )
        self.assertAlmostEqual(inferred_rear, 10.5)

    def test_four_foot_pockets_fit_inside_support_rails(self) -> None:
        pockets = model.foot_pocket_origins()
        self.assertEqual(len(pockets), 4)
        rails = model.support_rail_x_ranges()
        pocket_width = params.FOOT_X_MM + 2 * params.FOOT_POCKET_CLEARANCE_MM
        for x, z in pockets:
            self.assertTrue(any(x >= x0 and x + pocket_width <= x1 for x0, x1 in rails))
            self.assertGreater(z, params.PANEL_THICKNESS_MM)
            self.assertLess(
                z + params.FOOT_Z_MM + 2 * params.FOOT_POCKET_CLEARANCE_MM,
                params.DEVICE_FRONT_Z_MM + params.DEVICE_Z_MM,
            )

    def test_intermediate_wall_is_thinner_than_load_rails(self) -> None:
        self.assertLess(params.WEB_WALL_MM, params.WALL_MM)
        self.assertGreaterEqual(params.GUSSET_DEPTH_MM, 30.0)

    def test_front_stops_define_a_shallow_recess(self) -> None:
        self.assertEqual(params.DEVICE_FRONT_Z_MM, params.FRONT_STOP_DEPTH_MM)
        self.assertGreater(params.FRONT_STOP_INSET_MM, params.SIDE_CLEARANCE_MM)
        self.assertLessEqual(params.DEVICE_FRONT_Z_MM, 1.5)
        self.assertLessEqual(params.FRONT_STOP_HEIGHT_MM, 10.0)
        self.assertGreaterEqual(params.FRONT_TOP_BRACE_HEIGHT_MM, 4.0)

    def test_compliant_tabs_preload_at_widely_spaced_ribs(self) -> None:
        positions = model.anti_rattle_tab_z_positions()
        self.assertEqual(len(positions), 2)
        self.assertGreater(positions[1] - positions[0], 70.0)
        interference = params.ANTI_RATTLE_TAB_PROTRUSION_MM - params.SIDE_CLEARANCE_MM
        self.assertAlmostEqual(interference, 0.2)
        self.assertLess(
            params.ANTI_RATTLE_TAB_THICKNESS_MM,
            params.WEB_WALL_MM,
        )
        self.assertLess(
            params.ANTI_RATTLE_TAB_WIDTH_MM,
            params.ANTI_RATTLE_RELIEF_WIDTH_MM,
        )

    def test_fit_coupon_contains_front_fit_features(self) -> None:
        front_foot_start = (
            params.DEVICE_FRONT_Z_MM
            + params.FOOT_INSET_FRONT_MM
            - params.FOOT_POCKET_CLEARANCE_MM
        )
        self.assertGreater(params.FIT_TEST_DEPTH_MM, front_foot_start + 5.0)
        self.assertGreater(
            params.FIT_TEST_DEPTH_MM,
            model.capture_tab_z_ranges()[0][0] + 5.0,
        )
        self.assertLess(params.FIT_TEST_DEPTH_MM, 35.0)
        self.assertGreaterEqual(params.FIT_TEST_CONNECTOR_HEIGHT_MM, 3.0)

    def test_validation_passes(self) -> None:
        self.assertEqual(model.validate(), [])


if __name__ == "__main__":
    unittest.main()
