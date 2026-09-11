"""Parametric constants for Wyse 5070 Extended 10in rack mount.

Source of truth for the DeskPi RackMate T1 + Bambu A1 + Dell Wyse 5070
Extended combination. Pure Python so unit tests run without a CAD kernel.

Coordinate convention (mm):
  X = across the rack (left to right)
  Y = vertical (rack U direction)
  Z = depth (front rails toward rear)
  Origin = front-left-bottom of the full ear-span envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

U_MM: float = 44.45
# 2U default: a 66mm wide device cannot sit in a 66.675mm (1.5U) tray
# with any floor underneath (4mm floor + 66mm device already exceeds it).
# Drop to 1.5U only after measuring body-minus-feet under 62mm.
TARGET_U: float = 2.0
TARGET_HEIGHT_MM: float = U_MM * TARGET_U  # 88.9

# Dell Wyse 5070 Extended. Manuals/datasheet say 184 x 66 x 184;
# Dell shop pages say width 56. 66 is kept as worst case.
# Mounted flat with front ports forward:
#   X (across rack) = 184, Y (vertical) = 66, Z (depth) = 184.
DEVICE_X_MM: float = 184.0
DEVICE_Y_MM: float = 66.0
DEVICE_Z_MM: float = 184.0
DEVICE_WEIGHT_KG: float = 1.47

# DeskPi RackMate T1 (8U, 10in class).
RACK_INTERNAL_WIDTH_MM: float = 212.0
RACK_MAX_DEPTH_MM: float = 200.0
EAR_SPAN_MM: float = 254.0  # measured from existing 3d-prints/*.stl
EAR_THICKNESS_MM: float = 5.0
TRAY_FLOOR_MM: float = 4.0
WALL_MM: float = 3.0

# Bambu Lab A1 build volume.
BED_X_MM: float = 256.0
BED_Y_MM: float = 256.0
BED_Z_MM: float = 256.0

# Fit tuning.
FIT_CLEARANCE_MM: float = 0.4
VENT_GAP_MM: float = 6.0  # side vent channel per side

# Ear hole pattern measured from DeskPi's own 1U blank panel 3MF
# (Model_7_1U_Blank_Panel, 254x43x3mm): mounting slots centered 10mm
# from each outer edge with 30mm vertical spacing (slot ~13x7mm).
# We use 5mm holes at slot centers for M4 screws + washers.
HOLE_DIA_MM: float = 5.0
HOLES_PER_EAR: int = 2
HOLE_EDGE_OFFSET_MM: float = 10.0
HOLE_Y_SPACING_MM: float = 30.0

# Floor vent waffle instead of fitted foot pockets. Dell publishes no
# foot positions, so the floor is a rib grid: feet catch on ribs
# anywhere, plus ventilation and less filament (per community feedback
# on similar mounts asking for non-solid bottoms).
WAFFLE_CELL_MM: float = 14.0
WAFFLE_RIB_MM: float = 3.5
WAFFLE_DEPTH_MM: float = 2.5
WAFFLE_MARGIN_MM: float = 20.0


@dataclass(frozen=True)
class TrayEnvelope:
    outer_x_mm: float
    outer_y_mm: float
    outer_z_mm: float


def tray_envelope() -> TrayEnvelope:
    """Outer envelope of the tray, before ears. Height is fixed to the
    U target, the pocket must fit inside it (checked by fits_rack)."""
    outer_x = DEVICE_X_MM + 2 * (WALL_MM + VENT_GAP_MM) + 2 * FIT_CLEARANCE_MM
    outer_y = TARGET_HEIGHT_MM
    outer_z = DEVICE_Z_MM + WALL_MM + FIT_CLEARANCE_MM
    return TrayEnvelope(outer_x_mm=outer_x, outer_y_mm=outer_y, outer_z_mm=outer_z)


def tray_offset_x_mm() -> float:
    """Left edge of the centered tray inside the ear span."""
    return (EAR_SPAN_MM - tray_envelope().outer_x_mm) / 2.0


def fits_rack(envelope: TrayEnvelope) -> bool:
    pocket_y = TRAY_FLOOR_MM + DEVICE_Y_MM + FIT_CLEARANCE_MM
    return (
        envelope.outer_x_mm <= RACK_INTERNAL_WIDTH_MM
        and envelope.outer_z_mm <= RACK_MAX_DEPTH_MM
        and envelope.outer_y_mm <= TARGET_HEIGHT_MM
        and pocket_y <= TARGET_HEIGHT_MM
    )


def fits_bed() -> bool:
    return EAR_SPAN_MM <= BED_X_MM and TARGET_HEIGHT_MM <= BED_Z_MM
