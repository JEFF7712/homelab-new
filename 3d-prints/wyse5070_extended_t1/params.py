"""Dimensions for the Wyse 5070 Extended DeskPi RackMate T1 cradle.

Coordinate convention (mm): X is rack width, Y is height, and Z runs from
the front rail toward the rear of the rack.
"""

from __future__ import annotations

from dataclasses import dataclass

U_MM = 44.45
TARGET_U = 2
PANEL_HEIGHT_MM = 88.0

# Measured 2022 N12D Extended chassis, mounted flat with its ports forward.
DEVICE_X_MM = 184.0
DEVICE_BODY_Y_MM = 55.9
DEVICE_Y_MM = 59.5
DEVICE_Z_MM = 184.0
DEVICE_WEIGHT_KG = 1.47
FOOT_HEIGHT_MM = DEVICE_Y_MM - DEVICE_BODY_Y_MM
FOOT_X_MM = 5.8
FOOT_Z_MM = 20.0
FOOT_INSET_X_MM = 10.0
FOOT_INSET_FRONT_MM = 24.8
FOOT_INSET_REAR_MM = 9.5
FOOT_ROW_SPACING_Z_MM = 128.7
FOOT_POCKET_CLEARANCE_MM = 0.4
FOOT_POCKET_DEPTH_MM = 1.6

# DeskPi RackMate T1 and Bambu Lab A1 constraints.
RACK_INTERNAL_WIDTH_MM = 212.0
RACK_MAX_DEPTH_MM = 200.0
EAR_SPAN_MM = 254.0
BED_X_MM = 256.0
BED_Y_MM = 256.0

# Fit and structure. The device slides in from the rear.
SIDE_CLEARANCE_MM = 0.6
TOP_CLEARANCE_MM = 0.8
PANEL_THICKNESS_MM = 4.0
WALL_MM = 3.2
WEB_WALL_MM = 2.6
RAIL_DEPTH_MM = 190.5
SUPPORT_RAIL_MM = 18.0
SUPPORT_THICKNESS_MM = 4.0
LOWER_AIR_GAP_MM = 10.35
TOP_LIP_MM = 6.0
TOP_LIP_THICKNESS_MM = 4.0
CAPTURE_TAB_COUNT = 3
CAPTURE_TAB_DEPTH_MM = 32.0
CAPTURE_TAB_FRONT_MARGIN_MM = 18.0
CAPTURE_TAB_REAR_MARGIN_MM = 14.0
SIDE_VENT_COUNT = 8
SIDE_VENT_DEPTH_MM = 12.0
SIDE_VENT_FRONT_MARGIN_MM = 16.0
SIDE_VENT_REAR_MARGIN_MM = 12.0
SIDE_VENT_BOTTOM_RIB_MM = 10.0
SIDE_VENT_TOP_RIB_MM = 10.0
RETAINER_DEPTH_MM = 4.0
RETAINER_HEIGHT_MM = 12.0
RETAINER_SCREW_DIA_MM = 3.4
RETAINER_INSERT_DIA_MM = 4.2
RETAINER_INSERT_DEPTH_MM = 6.0
RETAINER_END_PAD_MM = 20.0
RETAINER_RAIL_HEIGHT_MM = 4.0
FRONT_STOP_DEPTH_MM = 1.2
FRONT_STOP_INSET_MM = 2.0
FRONT_STOP_HEIGHT_MM = 8.0
FRONT_TOP_BRACE_HEIGHT_MM = 4.0
DEVICE_FRONT_Z_MM = FRONT_STOP_DEPTH_MM
ANTI_RATTLE_TAB_COUNT = 2
ANTI_RATTLE_TAB_HEIGHT_MM = 28.0
ANTI_RATTLE_TAB_WIDTH_MM = 4.0
ANTI_RATTLE_TAB_THICKNESS_MM = 1.2
ANTI_RATTLE_TAB_PROTRUSION_MM = 0.8
ANTI_RATTLE_TAB_ANCHOR_MM = 4.0
ANTI_RATTLE_RELIEF_WIDTH_MM = 6.0
FIT_TEST_DEPTH_MM = 32.0
FIT_TEST_CONNECTOR_HEIGHT_MM = 3.0
FIT_TEST_CONNECTOR_DEPTH_MM = 4.0
FRONT_BRACE_HEIGHT_MM = 6.0
GUSSET_WIDTH_MM = 18.0
GUSSET_DEPTH_MM = 32.0

# DeskPi's 1U panel repeats a pair of vertical slots in every rack unit.
SLOT_WIDTH_MM = 7.0
SLOT_HEIGHT_MM = 13.0
SLOT_EDGE_OFFSET_MM = 10.0
SLOT_Y_INSET_MM = 7.0

# Slots through each support rail accept a 5 mm zip tie or hook-and-loop tie.
TIE_SLOT_X_MM = 7.0
TIE_SLOT_Z_MM = 16.0
TIE_SLOT_Z_POSITIONS_MM = (58.0, 132.0)


@dataclass(frozen=True)
class CradleEnvelope:
    body_x_mm: float
    panel_y_mm: float
    body_z_mm: float


def device_pocket_width_mm() -> float:
    return DEVICE_X_MM + 2 * SIDE_CLEARANCE_MM


def body_width_mm() -> float:
    return device_pocket_width_mm() + 2 * WALL_MM


def body_offset_x_mm() -> float:
    return (EAR_SPAN_MM - body_width_mm()) / 2


def device_floor_y_mm() -> float:
    return LOWER_AIR_GAP_MM + SUPPORT_THICKNESS_MM


def top_lip_y_mm() -> float:
    return device_floor_y_mm() + DEVICE_Y_MM - FOOT_POCKET_DEPTH_MM + TOP_CLEARANCE_MM


def cradle_envelope() -> CradleEnvelope:
    return CradleEnvelope(body_width_mm(), PANEL_HEIGHT_MM, RAIL_DEPTH_MM)


def fits_rack() -> bool:
    return (
        body_width_mm() <= RACK_INTERNAL_WIDTH_MM
        and RAIL_DEPTH_MM <= RACK_MAX_DEPTH_MM
        and top_lip_y_mm() + TOP_LIP_THICKNESS_MM <= PANEL_HEIGHT_MM
    )


def fits_bed() -> bool:
    return EAR_SPAN_MM <= BED_X_MM and RAIL_DEPTH_MM <= BED_Y_MM
