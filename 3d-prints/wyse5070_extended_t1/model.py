"""Parametric Build123d model for the Wyse 5070 Extended T1 cradle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import params


def ear_slot_x_positions() -> list[float]:
    return [params.SLOT_EDGE_OFFSET_MM, params.EAR_SPAN_MM - params.SLOT_EDGE_OFFSET_MM]


def ear_slot_y_positions() -> list[float]:
    positions: list[float] = []
    panel_unit = params.PANEL_HEIGHT_MM / params.TARGET_U
    for rack_unit in range(params.TARGET_U):
        base = rack_unit * panel_unit
        positions.extend(
            [
                base + params.SLOT_Y_INSET_MM,
                base + panel_unit - params.SLOT_Y_INSET_MM,
            ]
        )
    return positions


def support_rail_x_ranges() -> list[tuple[float, float]]:
    pocket_left = params.body_offset_x_mm() + params.WALL_MM
    pocket_right = pocket_left + params.device_pocket_width_mm()
    return [
        (pocket_left, pocket_left + params.SUPPORT_RAIL_MM),
        (pocket_right - params.SUPPORT_RAIL_MM, pocket_right),
    ]


def foot_pocket_origins() -> list[tuple[float, float]]:
    pocket_left = params.body_offset_x_mm() + params.WALL_MM
    x_positions = [
        pocket_left + params.FOOT_INSET_X_MM - params.FOOT_POCKET_CLEARANCE_MM,
        pocket_left
        + params.DEVICE_X_MM
        - params.FOOT_INSET_X_MM
        - params.FOOT_X_MM
        - params.FOOT_POCKET_CLEARANCE_MM,
    ]
    z_positions = [
        params.DEVICE_FRONT_Z_MM
        + params.FOOT_INSET_FRONT_MM
        - params.FOOT_POCKET_CLEARANCE_MM,
        params.DEVICE_FRONT_Z_MM
        + params.FOOT_INSET_FRONT_MM
        + params.FOOT_ROW_SPACING_Z_MM
        - params.FOOT_POCKET_CLEARANCE_MM,
    ]
    return [(x, z) for x in x_positions for z in z_positions]


def side_vent_z_ranges() -> list[tuple[float, float]]:
    first = params.PANEL_THICKNESS_MM + params.SIDE_VENT_FRONT_MARGIN_MM
    last = (
        params.RAIL_DEPTH_MM
        - params.RETAINER_DEPTH_MM
        - params.SIDE_VENT_REAR_MARGIN_MM
    )
    openings = params.SIDE_VENT_COUNT * params.SIDE_VENT_DEPTH_MM
    gap = (last - first - openings) / (params.SIDE_VENT_COUNT - 1)
    return [
        (
            first + index * (params.SIDE_VENT_DEPTH_MM + gap),
            first
            + index * (params.SIDE_VENT_DEPTH_MM + gap)
            + params.SIDE_VENT_DEPTH_MM,
        )
        for index in range(params.SIDE_VENT_COUNT)
    ]


def anti_rattle_tab_z_positions() -> list[float]:
    vents = side_vent_z_ranges()
    gaps = [(left[1], right[0]) for left, right in zip(vents, vents[1:])]
    selected = (1, len(gaps) - 2)
    return [(gaps[index][0] + gaps[index][1]) / 2 for index in selected]


def capture_tab_z_ranges() -> list[tuple[float, float]]:
    first = params.PANEL_THICKNESS_MM + params.CAPTURE_TAB_FRONT_MARGIN_MM
    last = params.RAIL_DEPTH_MM - params.CAPTURE_TAB_REAR_MARGIN_MM
    tabs = params.CAPTURE_TAB_COUNT * params.CAPTURE_TAB_DEPTH_MM
    gap = (last - first - tabs) / (params.CAPTURE_TAB_COUNT - 1)
    return [
        (
            first + index * (params.CAPTURE_TAB_DEPTH_MM + gap),
            first
            + index * (params.CAPTURE_TAB_DEPTH_MM + gap)
            + params.CAPTURE_TAB_DEPTH_MM,
        )
        for index in range(params.CAPTURE_TAB_COUNT)
    ]


def validate() -> list[str]:
    errors: list[str] = []
    if not params.fits_rack():
        env = params.cradle_envelope()
        errors.append(
            f"cradle {env.body_x_mm:.1f}x{env.panel_y_mm:.1f}x{env.body_z_mm:.1f}mm "
            "does not fit the T1 envelope"
        )
    if not params.fits_bed():
        errors.append("cradle exceeds the A1 bed")
    ear_width = params.body_offset_x_mm()
    if ear_width < params.SLOT_EDGE_OFFSET_MM + params.SLOT_WIDTH_MM / 2:
        errors.append("ears are too narrow for the rack slots")
    if params.SUPPORT_RAIL_MM <= params.TIE_SLOT_X_MM + 2 * params.WALL_MM:
        errors.append("support rails are too narrow around tie slots")
    if (
        params.RETAINER_DEPTH_MM + params.DEVICE_Z_MM + params.PANEL_THICKNESS_MM
        > params.RAIL_DEPTH_MM + 2
    ):
        errors.append("device and stops exceed rail depth")
    vent_height = (
        params.top_lip_y_mm()
        + params.TOP_LIP_THICKNESS_MM
        - (params.device_floor_y_mm() - params.SUPPORT_THICKNESS_MM)
        - params.SIDE_VENT_BOTTOM_RIB_MM
        - params.SIDE_VENT_TOP_RIB_MM
    )
    if vent_height <= 0 or any(z1 <= z0 for z0, z1 in side_vent_z_ranges()):
        errors.append("side vent dimensions leave no structural ribs")
    if any(z1 <= z0 for z0, z1 in capture_tab_z_ranges()):
        errors.append("capture tab dimensions overlap")
    if not 0 < params.WEB_WALL_MM < params.WALL_MM:
        errors.append("web wall must be thinner than the structural rails")
    inferred_rear_inset = (
        params.DEVICE_Z_MM
        - params.FOOT_INSET_FRONT_MM
        - params.FOOT_ROW_SPACING_Z_MM
        - params.FOOT_Z_MM
    )
    if abs(inferred_rear_inset - params.FOOT_INSET_REAR_MM) > 2.0:
        errors.append("foot row spacing conflicts with front and rear insets")
    if params.FOOT_POCKET_DEPTH_MM >= params.SUPPORT_THICKNESS_MM:
        errors.append("foot pockets cut through the support rails")
    if params.ANTI_RATTLE_TAB_PROTRUSION_MM <= params.SIDE_CLEARANCE_MM:
        errors.append("anti-rattle tabs do not preload the chassis")
    if len(anti_rattle_tab_z_positions()) != params.ANTI_RATTLE_TAB_COUNT:
        errors.append("anti-rattle tab count does not match selected vent ribs")
    return errors


def build() -> object:
    errors = validate()
    if errors:
        raise RuntimeError("; ".join(errors))
    try:
        from build123d import Align, Box, Cylinder, Face, Solid, Wire
    except ImportError as exc:
        raise RuntimeError("build123d is not installed") from exc

    def box(x: float, y: float, z: float) -> object:
        return Box(x, y, z, align=(Align.MIN, Align.MIN, Align.MIN))

    def vertical_slot(x: float, y: float, depth: float) -> object:
        radius = params.SLOT_WIDTH_MM / 2
        straight = params.SLOT_HEIGHT_MM - params.SLOT_WIDTH_MM
        cutter = box(params.SLOT_WIDTH_MM, straight, depth).translate(
            (x - radius, y - straight / 2, -0.1)
        )
        for cy in (y - straight / 2, y + straight / 2):
            cutter += Cylinder(
                radius,
                depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ).translate((x, cy, -0.1))
        return cutter

    def side_capsule(x: float, y: float, z: float, height: float) -> object:
        radius = params.SIDE_VENT_DEPTH_MM / 2
        straight = height - 2 * radius
        cutter = box(params.WALL_MM + 0.6, straight, 2 * radius).translate(
            (x - 0.3, y + radius, z)
        )
        for cy in (y + radius, y + height - radius):
            cutter += Cylinder(
                radius,
                params.WALL_MM + 0.6,
                rotation=(0, 90, 0),
            ).translate((x + params.WALL_MM / 2, cy, z + radius))
        return cutter

    def triangular_gusset(x: float) -> object:
        rail_underside = params.device_floor_y_mm() - params.SUPPORT_THICKNESS_MM + 0.6
        profile = Face(
            Wire.make_polygon(
                [
                    (x, 0, params.PANEL_THICKNESS_MM),
                    (x, rail_underside, params.PANEL_THICKNESS_MM),
                    (
                        x,
                        rail_underside,
                        params.PANEL_THICKNESS_MM + params.GUSSET_DEPTH_MM,
                    ),
                ],
                close=True,
            )
        )
        return Solid.extrude(profile, (params.GUSSET_WIDTH_MM, 0, 0))

    body_x = params.body_offset_x_mm()
    body_w = params.body_width_mm()
    pocket_x = body_x + params.WALL_MM
    pocket_w = params.device_pocket_width_mm()
    floor_y = params.device_floor_y_mm()
    lip_y = params.top_lip_y_mm()
    rail_d = params.RAIL_DEPTH_MM

    body = box(params.EAR_SPAN_MM, params.PANEL_HEIGHT_MM, params.PANEL_THICKNESS_MM)
    opening = box(
        pocket_w,
        params.DEVICE_Y_MM + params.TOP_CLEARANCE_MM,
        params.PANEL_THICKNESS_MM + 0.2,
    ).translate((pocket_x, floor_y, -0.1))
    body -= opening

    body += box(
        body_w,
        params.FRONT_TOP_BRACE_HEIGHT_MM,
        params.PANEL_THICKNESS_MM,
    ).translate((body_x, lip_y, 0))

    bottom_stop_y = floor_y + params.FOOT_HEIGHT_MM
    top_stop_y = floor_y + params.DEVICE_Y_MM - params.FRONT_STOP_HEIGHT_MM
    for stop_x in (
        pocket_x,
        pocket_x + pocket_w - params.FRONT_STOP_INSET_MM,
    ):
        for stop_y in (bottom_stop_y, top_stop_y):
            body += box(
                params.FRONT_STOP_INSET_MM,
                params.FRONT_STOP_HEIGHT_MM,
                params.FRONT_STOP_DEPTH_MM,
            ).translate((stop_x, stop_y, 0))

    for x in ear_slot_x_positions():
        for y in ear_slot_y_positions():
            body -= vertical_slot(x, y, params.PANEL_THICKNESS_MM + 0.2)

    for rail_x0, rail_x1 in support_rail_x_ranges():
        rail = box(
            rail_x1 - rail_x0,
            params.SUPPORT_THICKNESS_MM,
            rail_d - params.PANEL_THICKNESS_MM,
        ).translate(
            (
                rail_x0,
                floor_y - params.SUPPORT_THICKNESS_MM,
                params.PANEL_THICKNESS_MM,
            )
        )
        for slot_z in params.TIE_SLOT_Z_POSITIONS_MM:
            tie_slot = box(
                params.TIE_SLOT_X_MM,
                params.SUPPORT_THICKNESS_MM + 0.2,
                params.TIE_SLOT_Z_MM,
            ).translate(
                (
                    (rail_x0 + rail_x1 - params.TIE_SLOT_X_MM) / 2,
                    floor_y - params.SUPPORT_THICKNESS_MM - 0.1,
                    slot_z - params.TIE_SLOT_Z_MM / 2,
                )
            )
            rail -= tie_slot
        for foot_x, foot_z in foot_pocket_origins():
            if rail_x0 <= foot_x <= rail_x1:
                foot_pocket = box(
                    params.FOOT_X_MM + 2 * params.FOOT_POCKET_CLEARANCE_MM,
                    params.FOOT_POCKET_DEPTH_MM + 0.2,
                    params.FOOT_Z_MM + 2 * params.FOOT_POCKET_CLEARANCE_MM,
                ).translate(
                    (
                        foot_x,
                        floor_y - params.FOOT_POCKET_DEPTH_MM,
                        foot_z,
                    )
                )
                rail -= foot_pocket
        body += rail

    for side_x, lip_x, inward in (
        (body_x, pocket_x, 1.0),
        (
            body_x + body_w - params.WALL_MM,
            pocket_x + pocket_w - params.TOP_LIP_MM,
            -1.0,
        ),
    ):
        wall_bottom = floor_y - params.SUPPORT_THICKNESS_MM
        wall_top = lip_y + params.TOP_LIP_THICKNESS_MM
        web_offset = (params.WALL_MM - params.WEB_WALL_MM) / 2
        wall = box(
            params.WEB_WALL_MM,
            wall_top - wall_bottom,
            rail_d - params.PANEL_THICKNESS_MM,
        ).translate((side_x + web_offset, wall_bottom, params.PANEL_THICKNESS_MM))
        wall += box(
            params.WALL_MM,
            params.SIDE_VENT_BOTTOM_RIB_MM,
            rail_d - params.PANEL_THICKNESS_MM,
        ).translate((side_x, wall_bottom, params.PANEL_THICKNESS_MM))
        wall += box(
            params.WALL_MM,
            params.SIDE_VENT_TOP_RIB_MM,
            rail_d - params.PANEL_THICKNESS_MM,
        ).translate(
            (
                side_x,
                wall_top - params.SIDE_VENT_TOP_RIB_MM,
                params.PANEL_THICKNESS_MM,
            )
        )
        for z0, depth in (
            (params.PANEL_THICKNESS_MM, params.SIDE_VENT_FRONT_MARGIN_MM),
            (
                rail_d - params.SIDE_VENT_REAR_MARGIN_MM,
                params.SIDE_VENT_REAR_MARGIN_MM,
            ),
        ):
            wall += box(params.WALL_MM, wall_top - wall_bottom, depth).translate(
                (side_x, wall_bottom, z0)
            )
        vent_y = wall_bottom + params.SIDE_VENT_BOTTOM_RIB_MM
        vent_height = wall_top - params.SIDE_VENT_TOP_RIB_MM - vent_y
        for vent_z0, _ in side_vent_z_ranges():
            wall -= side_capsule(side_x, vent_y, vent_z0, vent_height)
        spring_y = floor_y + 8.0
        for spring_z in anti_rattle_tab_z_positions():
            relief = box(
                params.WALL_MM + 0.6,
                params.ANTI_RATTLE_TAB_HEIGHT_MM - params.ANTI_RATTLE_TAB_ANCHOR_MM,
                params.ANTI_RATTLE_RELIEF_WIDTH_MM,
            ).translate(
                (
                    side_x - 0.3,
                    spring_y + params.ANTI_RATTLE_TAB_ANCHOR_MM,
                    spring_z - params.ANTI_RATTLE_RELIEF_WIDTH_MM / 2,
                )
            )
            wall -= relief
            pocket_edge = pocket_x if inward > 0 else pocket_x + pocket_w
            spring_x = (
                pocket_edge
                + params.ANTI_RATTLE_TAB_PROTRUSION_MM
                - params.ANTI_RATTLE_TAB_THICKNESS_MM
                if inward > 0
                else pocket_edge - params.ANTI_RATTLE_TAB_PROTRUSION_MM
            )
            wall += box(
                params.ANTI_RATTLE_TAB_THICKNESS_MM,
                params.ANTI_RATTLE_TAB_HEIGHT_MM,
                params.ANTI_RATTLE_TAB_WIDTH_MM,
            ).translate(
                (
                    spring_x,
                    spring_y,
                    spring_z - params.ANTI_RATTLE_TAB_WIDTH_MM / 2,
                )
            )
        body += wall
        for tab_z0, tab_z1 in capture_tab_z_ranges():
            body += box(
                params.TOP_LIP_MM,
                params.TOP_LIP_THICKNESS_MM,
                tab_z1 - tab_z0,
            ).translate((lip_x, lip_y, tab_z0))

        screw = Cylinder(
            params.RETAINER_SCREW_DIA_MM / 2,
            params.WALL_MM + 0.6,
            rotation=(0, 90, 0),
        ).translate(
            (
                side_x + params.WALL_MM / 2,
                floor_y + params.RETAINER_HEIGHT_MM / 2,
                params.DEVICE_FRONT_Z_MM
                + params.DEVICE_Z_MM
                + params.RETAINER_DEPTH_MM / 2,
            )
        )
        body -= screw

    body += box(
        body_w, params.FRONT_BRACE_HEIGHT_MM, params.PANEL_THICKNESS_MM
    ).translate(
        (body_x, floor_y - params.SUPPORT_THICKNESS_MM, params.PANEL_THICKNESS_MM)
    )
    for gx in (body_x, body_x + body_w - params.GUSSET_WIDTH_MM):
        body += triangular_gusset(gx)

    return body


def build_retainer() -> object:
    try:
        from build123d import Align, Box, Cylinder
    except ImportError as exc:
        raise RuntimeError("build123d is not installed") from exc

    retainer = Box(
        params.device_pocket_width_mm(),
        params.RETAINER_RAIL_HEIGHT_MM,
        params.RETAINER_DEPTH_MM,
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    for x in (0.0, params.device_pocket_width_mm() - params.RETAINER_END_PAD_MM):
        retainer += Box(
            params.RETAINER_END_PAD_MM,
            params.RETAINER_HEIGHT_MM,
            params.RETAINER_DEPTH_MM,
            align=(Align.MIN, Align.MIN, Align.MIN),
        ).translate((x, 0, 0))
    for x, direction in (
        (0.0, 1.0),
        (params.device_pocket_width_mm(), -1.0),
    ):
        bore = Cylinder(
            params.RETAINER_INSERT_DIA_MM / 2,
            params.RETAINER_INSERT_DEPTH_MM,
            rotation=(0, 90, 0),
        )
        retainer -= bore.translate(
            (
                x + direction * params.RETAINER_INSERT_DEPTH_MM / 2,
                params.RETAINER_HEIGHT_MM / 2,
                params.RETAINER_DEPTH_MM / 2,
            )
        )
    return retainer


def build_fit_test() -> object:
    try:
        from build123d import Align, Box
    except ImportError as exc:
        raise RuntimeError("build123d is not installed") from exc

    wall_bottom = params.device_floor_y_mm() - params.SUPPORT_THICKNESS_MM
    wall_top = params.top_lip_y_mm() + params.TOP_LIP_THICKNESS_MM
    body_x = params.body_offset_x_mm()
    side_width = params.WALL_MM + params.SUPPORT_RAIL_MM
    source = build()
    fit_test = None
    for x in (body_x, body_x + params.body_width_mm() - side_width):
        clip = Box(
            side_width,
            wall_top - wall_bottom,
            params.FIT_TEST_DEPTH_MM,
            align=(Align.MIN, Align.MIN, Align.MIN),
        ).translate((x, wall_bottom, 0))
        rail_section = source & clip
        fit_test = rail_section if fit_test is None else fit_test + rail_section
    top_bar_clip = Box(
        params.body_width_mm(),
        params.FRONT_TOP_BRACE_HEIGHT_MM,
        params.PANEL_THICKNESS_MM,
        align=(Align.MIN, Align.MIN, Align.MIN),
    ).translate((body_x, params.top_lip_y_mm(), 0))
    fit_test += source & top_bar_clip
    connector = Box(
        params.body_width_mm(),
        params.FIT_TEST_CONNECTOR_HEIGHT_MM,
        params.FIT_TEST_CONNECTOR_DEPTH_MM,
        align=(Align.MIN, Align.MIN, Align.MIN),
    ).translate((body_x, wall_bottom, 0))
    return (fit_test + connector).translate((-body_x, -wall_bottom, 0))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", help="output .stl or .step path")
    parser.add_argument(
        "--export-retainer", help="output rear retainer .stl or .step path"
    )
    parser.add_argument(
        "--export-fit-test", help="output short fit-test .stl or .step path"
    )
    args = parser.parse_args(argv)
    errors = validate()
    if errors:
        for error in errors:
            print(f"blocking: {error}", file=sys.stderr)
        return 1
    for output, solid in (
        (args.export, build() if args.export else None),
        (args.export_retainer, build_retainer() if args.export_retainer else None),
        (args.export_fit_test, build_fit_test() if args.export_fit_test else None),
    ):
        if not output or solid is None:
            continue
        out = Path(output)
        if out.suffix.lower() == ".stl":
            from build123d import export_stl

            export_stl(solid, str(out))
        elif out.suffix.lower() in {".step", ".stp"}:
            from build123d import export_step

            export_step(solid, str(out))
        else:
            print(
                "blocking: export path must end in .stl, .step, or .stp",
                file=sys.stderr,
            )
            return 1
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
