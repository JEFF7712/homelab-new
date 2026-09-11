"""Build123d parametric model for the Wyse 5070 Extended T1 mount.

Requires build123d only for build/export. Import it lazily so unit tests
and repo checks run without the CAD kernel installed.

Install for local iteration:
  uv run --with build123d python -m wyse5070_extended_t1.model

Export (needs PYTHONPATH=3d-prints):
  PYTHONPATH=3d-prints uv run --with build123d \\
      python -m wyse5070_extended_t1.model --export /tmp/wyse5070_t1.stl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import params


def ear_hole_y_positions() -> list[float]:
    """Hole heights per ear, symmetric about ear mid."""
    y_mid = params.TARGET_HEIGHT_MM / 2.0
    gap = params.HOLE_Y_SPACING_MM / 2.0
    return [y_mid - gap, y_mid + gap]


def ear_hole_x_positions() -> list[float]:
    """Hole columns in full-span coordinates (DeskPi slot centers)."""
    return [
        params.HOLE_EDGE_OFFSET_MM,
        params.EAR_SPAN_MM - params.HOLE_EDGE_OFFSET_MM,
    ]


def waffle_cells() -> list[tuple[float, float]]:
    """Centers of waffle cells in tray-local coordinates."""
    pitch = params.WAFFLE_CELL_MM + params.WAFFLE_RIB_MM
    env = params.tray_envelope()
    x0 = params.WAFFLE_MARGIN_MM + params.WAFFLE_CELL_MM / 2.0
    x1 = env.outer_x_mm - params.WAFFLE_MARGIN_MM - params.WAFFLE_CELL_MM / 2.0
    z0 = params.WAFFLE_MARGIN_MM + params.WAFFLE_CELL_MM / 2.0
    z1 = env.outer_z_mm - params.WAFFLE_MARGIN_MM - params.WAFFLE_CELL_MM / 2.0
    cells = []
    x = x0
    while x <= x1 + 1e-6:
        z = z0
        while z <= z1 + 1e-6:
            cells.append((x, z))
            z += pitch
        x += pitch
    return cells


def validate() -> list[str]:
    """Return a list of blocking errors. Empty means ready to build."""
    errors: list[str] = []
    env = params.tray_envelope()
    if not params.fits_rack(env):
        errors.append(
            f"tray {env.outer_x_mm:.1f}x{env.outer_y_mm:.1f}x{env.outer_z_mm:.1f}mm "
            "exceeds T1 envelope "
            f"{params.RACK_INTERNAL_WIDTH_MM:.0f}x{params.TARGET_HEIGHT_MM:.1f}x"
            f"{params.RACK_MAX_DEPTH_MM:.0f}mm"
        )
    if not params.fits_bed():
        errors.append("ear span exceeds A1 bed")
    ear_w = (params.EAR_SPAN_MM - env.outer_x_mm) / 2.0
    if ear_w < params.HOLE_EDGE_OFFSET_MM + params.HOLE_DIA_MM:
        errors.append("ears too narrow for hole offset")
    if params.WAFFLE_DEPTH_MM >= params.TRAY_FLOOR_MM:
        errors.append("waffle grooves deeper than floor")
    return errors


def build() -> object:
    """Build the solid with build123d. Raises RuntimeError if invalid."""
    errors = validate()
    if errors:
        raise RuntimeError("; ".join(errors))
    try:
        from build123d import Align, Box, Cylinder
    except ImportError as exc:
        raise RuntimeError("build123d is not installed") from exc

    def _box(w: float, h: float, d: float) -> object:
        # Corner-at-origin semantics; build123d defaults to centered.
        return Box(w, h, d, align=(Align.MIN, Align.MIN, Align.MIN))

    env = params.tray_envelope()
    tray_w = env.outer_x_mm
    tray_h = params.TARGET_HEIGHT_MM
    tray_d = env.outer_z_mm
    ox = params.tray_offset_x_mm()
    ear_w = (params.EAR_SPAN_MM - tray_w) / 2.0

    tray = _box(tray_w, tray_h, tray_d)

    # Hollow the device pocket from the top of the floor.
    pocket = _box(
        params.DEVICE_X_MM + 2 * params.FIT_CLEARANCE_MM,
        params.DEVICE_Y_MM + params.FIT_CLEARANCE_MM,
        params.DEVICE_Z_MM + params.FIT_CLEARANCE_MM,
    ).translate(
        (
            params.WALL_MM + params.VENT_GAP_MM,
            params.TRAY_FLOOR_MM,
            params.WALL_MM,
        )
    )
    tray -= pocket

    # Waffle vent/foot grid milled into the floor top.
    cell = params.WAFFLE_CELL_MM
    for cx, cz in waffle_cells():
        groove = _box(cell, params.WAFFLE_DEPTH_MM + 0.2, cell).translate(
            (
                cx - cell / 2.0,
                params.TRAY_FLOOR_MM - params.WAFFLE_DEPTH_MM,
                cz - cell / 2.0,
            )
        )
        tray -= groove

    # Side vent slots cut through both walls.
    vent_h, vent_d, vent_n = 30.0, 8.0, 4
    for i in range(vent_n):
        z = 30.0 + i * ((tray_d - 60.0) / max(vent_n - 1, 1))
        for x in (0.0, tray_w - params.WALL_MM):
            vent = _box(params.WALL_MM + 0.4, vent_h, vent_d).translate(
                (
                    x - 0.2,
                    params.TRAY_FLOOR_MM + 8.0,
                    z - vent_d / 2.0,
                )
            )
            tray -= vent

    body = tray.translate((ox, 0.0, 0.0))

    # Outboard ears with clearance holes (axis through Z, front to back).
    for ex in (0.0, params.EAR_SPAN_MM - ear_w):
        ear = _box(ear_w, tray_h, params.EAR_THICKNESS_MM).translate(
            (
                ex,
                0.0,
                -params.EAR_THICKNESS_MM,
            )
        )
        for hx in ear_hole_x_positions():
            if not (ex < hx < ex + ear_w):
                continue
            for hy in ear_hole_y_positions():
                hole = Cylinder(
                    radius=params.HOLE_DIA_MM / 2.0,
                    height=params.EAR_THICKNESS_MM + 0.4,
                ).translate(
                    (
                        hx,
                        hy,
                        -params.EAR_THICKNESS_MM / 2.0,
                    )
                )
                ear -= hole
        body += ear

    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", default=None, help="output .stl or .step path")
    args = parser.parse_args(argv)
    errors = validate()
    if errors:
        print("blocking:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    if args.export:
        solid = build()
        from build123d import export_stl

        out = Path(args.export)
        if out.suffix.lower() == ".stl":
            export_stl(solid, str(out))
        else:
            from build123d import export_step

            export_step(solid, str(out))
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
