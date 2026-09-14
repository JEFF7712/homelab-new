# DeskPi RackMate T1 8U Upper Extension
## Product Requirements & Mechanical Design Specification

**Version:** 0.4  
**Status:** Structural architecture substantially locked; ready for independent audit before detailed CAD  
**Date:** 2026-09-13

---

## 1. Purpose

Design a mechanically credible, visually integrated, 3D-printable **8U extension** that mounts directly on top of a DeskPi RackMate T1.

The extension should:

- Reuse the T1's existing top / handle mounting interface where practical.
- Preserve standard 10-inch rack geometry.
- Match the T1's external dimensions closely enough to appear like a factory continuation.
- Be manufacturable on a **Bambu Lab A1**.
- Require no permanent modification to the original RackMate T1.
- Remain modular, serviceable, and easy to revise.

The intended final result is approximately equivalent to a **16U RackMate T1**, consisting of the original 8U T1 plus a custom 8U upper extension.

---

## 2. Executive Summary

The extension will mount **above** the existing T1 and function as a removable 8U chassis spacer inserted between the original T1 lower chassis and its original top plate / handles.

The refined architecture is:

1. Remove the factory handles and factory 281 × 200 × 4.4 mm acrylic top plate.
2. Bolt a custom printed lower interface frame directly to the exposed aluminum top structure of the T1.
3. Use eight existing M4 × 0.7 structural holes near the four corners as the primary chassis attachment points.
4. Build the extension from four reinforced hollow box columns, each split into two 4U printed modules.
5. Run one continuous M5 threaded rod through each vertical column to clamp the lower frame, both 4U modules, and upper frame into a single preloaded structure.
6. Use M4 brass heat-set inserts in the front rack rails for repeated equipment mounting.
7. Reproduce the factory handle-hole pattern at the top of the extension.
8. Reinstall the **original T1 acrylic top plate and original aluminum handles** on the custom extension.

This architecture preserves the stock T1 as the structural base, keeps heavy equipment low, avoids permanent chassis modification, and lets the completed rack retain the original RackMate top appearance.

---

## 3. Product Goals

### Primary goals

- Add **8U** of usable 10-inch rack space above the current T1.
- Make the extension appear to be a continuation of the stock RackMate T1.
- Match the T1's external width and depth as closely as practical.
- Preserve continuous rack-hole spacing across the T1-to-extension seam.
- Reuse existing mounting holes rather than drilling the chassis.
- Ensure every printed part fits on a Bambu Lab A1.
- Use common metric hardware.
- Make damaged or revised parts individually replaceable.
- Prioritize stiffness and structural geometry over minimizing filament use.

### Secondary goals

- Allow optional smoked acrylic side panels.
- Minimize visible fasteners and seams.
- Permit later addition of handles to the top of the extension.
- Allow hidden metal reinforcement if necessary.

---

## 4. Non-Goals

The design is **not** intended to:

- Replace a load-rated commercial floor-standing rack.
- Reproduce DeskPi's die-cast aluminum construction exactly.
- Support the full mass of the lower T1 from printed members.
- Use adhesive as a primary structural connection.
- Require drilling, cutting, or otherwise permanently modifying the T1.
- Require modification of the original acrylic side panels.

---

## 5. Reference Geometry

### Physically verified T1 dimensions

The following dimensions were measured directly from the user's RackMate T1.

| Parameter | Verified / working value | Status |
|---|---:|---|
| T1 top-frame external width | 281 mm | Physically measured |
| T1 top-frame external depth | 199-200 mm | Physically measured; design nominal = 200 mm |
| Original acrylic top plate | 281 × 200 × 4.4 mm | Physically measured |
| Left/right aluminum top-member width | 30.0 mm | Physically measured |
| Front/rear aluminum top-member width | 30.0 mm | Physically measured |
| Top-frame structural thickness | ~10 mm | Physically measured |
| Stock handle screw | ~3.6 mm measured major diameter × 15.5 mm long | Nominal M4 × 16 mm |
| Thread pitch | 0.7 mm | Verified over 10 thread intervals |
| Top-frame thread | **M4 × 0.7** | Confirmed |
| Extension capacity | 8U | Fixed |
| Rack unit pitch | 44.45 mm | Standard |
| Nominal extension rack height | 355.6 mm | 8 × 44.45 mm |
| Bambu A1 build volume | 256 × 256 × 256 mm | Fixed manufacturing constraint |

### Verified top-hole pattern

Coordinate system:

```text
Origin: front-left outside corner of T1 top frame
X: left → right
Y: front → rear
```

Left-side structural-hole column:

```text
X = 22.8 mm

Y = 25
    38
    69
    82
    113
    126
    157
    170 mm
```

Left-side handle-hole column:

```text
X = 13.0 mm

Y = 34.5
    165.5 mm
```

The right-side pattern is mirrored across the 281 mm chassis width:

```text
Structural-hole X = 258.2 mm
Handle-hole X     = 268.0 mm
```

All ten holes per side accept the same **M4 × 0.7** thread.

### Selected lower attachment holes

Revision 0.2 selects eight structural mounting holes:

```text
Y = 25, 38, 157, 170 mm
```

on both left and right sides.

This creates four paired attachment zones near the chassis corners while leaving the middle structural holes free.

---

## 6. Critical Manufacturing Constraint

The Bambu Lab A1 build volume is:

```text
256 × 256 × 256 mm
```

The extension is approximately:

```text
Width:   ~282.25 mm
Depth:   ~200 mm
Height:  355.6 mm
```

Therefore:

- A full-width ~282 mm top frame **cannot be printed as one flat piece**.
- A full-width ~282 mm bottom frame **cannot be printed as one flat piece**.
- A full-height 355.6 mm rail **cannot be printed vertically as one piece**.

The design **must be modular**.

---

## 7. High-Level Architecture

```text
            8U PRINTED EXTENSION
      ┌────────────────────────────┐
      │                            │
      │   lightweight equipment    │
      │                            │
      │   modular 10-inch rails    │
      │                            │
      ├────────────────────────────┤
      │   rigid interface frame    │
      └────────────┬───────────────┘
                   │
          factory top mounting
             / handle holes
                   │
      ┌────────────┴───────────────┐
      │                            │
      │      ORIGINAL T1 8U        │
      │                            │
      │    heavy equipment low     │
      │                            │
      └────────────────────────────┘
```

---

## 8. T1 Attachment Interface

### Bottom interface

The extension shall mount directly to the exposed aluminum top frame after removal of the factory top plate and handles.

The primary attachment scheme shall use **eight M4 × 0.7 bolts** located at:

```text
Y = 25, 38, 157, 170 mm
```

on both left and right structural-hole columns.

The lower interface frame shall:

- sit directly on the 30 mm-wide T1 aluminum side members,
- distribute vertical load through broad printed-to-aluminum bearing surfaces,
- use the eight M4 fasteners primarily for clamping, anti-separation, and lateral retention,
- include geometric registration features where useful,
- require no drilling, tapping, or permanent modification,
- remain fully removable.

### Top interface

The custom upper frame shall reproduce the stock handle-hole coordinates:

```text
Left handle-hole X:  13.0 mm
Right handle-hole X: 268.0 mm
Front Y: 34.5 mm
Rear Y:  165.5 mm
```

The original **281 × 200 × 4.4 mm acrylic top plate** and original aluminum handles shall be reinstalled on the custom extension.

The preferred top-thread implementation is captive M4 hardware or M4 brass heat-set inserts positioned so the stock M4 × 16 mm handle screws can be reused if practical.

---

## 9. Structural Load Path

The preferred vertical load path is:

```text
upper equipment
      ↓
rack rails / upper frame
      ↓
vertical extension members
      ↓
rigid lower interface frame
      ↓
broad contact with T1 aluminum frame
      ↓
original T1 structure
      ↓
T1 feet / supporting surface
```

The M3 fasteners should primarily provide:

- clamping,
- alignment retention,
- anti-separation,
- limited shear restraint.

They should **not** be the sole load-bearing mechanism.

---

## 10. Mechanical Registration

The extension should include geometry that physically registers against the T1 frame.

Possible approaches:

- shallow locating lips,
- corner pockets,
- mating ledges,
- keyed bosses,
- partial frame sockets.

Target engagement depth:

```text
~2-4 mm
```

The registration geometry should resist:

- lateral sliding,
- twisting,
- front-to-back movement.

It should also make assembly self-aligning.

Example concept:

```text
        printed upright
             │
             │
       ┌─────┴─────┐
       │ lower frame│
       └─┐       ┌─┘
         │       │
    ┌────┴───────┴────┐
    │   T1 aluminum   │
    └─────────────────┘
```

---

## 11. Lower Interface Frame

The extension shall have a rigid lower perimeter structure connecting all four vertical members before load enters the T1.

Requirements:

- Match the T1 footprint as closely as possible.
- Sit flush against the T1 top structure.
- Contain the factory-hole attachment geometry.
- Contain mechanical registration features.
- Tie all four uprights together.
- Avoid simple unsupported butt joints.

Because the T1 is wider than the A1 bed, the lower frame must be split into multiple printed sections.

Potential joint types:

- keyed lap joint,
- dovetail,
- tongue-and-groove,
- scarf joint,
- spline joint,
- bolted overlapping plates.

The preferred solution should combine **geometric interlock + mechanical fasteners**.

---

## 12. Vertical Rail / Upright Architecture

The extension shall use four reinforced hollow box columns.

All four columns shall be **rack-capable** and use the same M4 heat-set insert pattern so equipment can be supported from both front and rear.

### Overall height and segmentation

The extension shall add exactly:

```text
8U = 355.6 mm nominal vertical pitch
```

from the original T1 top-plane datum to the relocated factory top-plane datum.

The 12 mm top and bottom frames are **included within this 355.6 mm overall added height**. They shall overlap / capture the ends of the columns rather than adding 24 mm on top of the 8U height.

Each column is split at approximately the 4U midpoint:

```text
Lower module nominal span: 177.8 mm
Upper module nominal span: 177.8 mm
Overall extension height: 355.6 mm
```

The exact printed geometry may include interlocking overlap at the splice while preserving the external 355.6 mm datum-to-datum height.

### Column cross-section

Locked baseline:

```text
External section: ~30 × 30 mm
Structure: hollow ribbed box
Nominal outer walls: ~4 mm
Local front/rear insert region: ~5-8 mm
M5 tie-rod clearance bore: ~6.0-6.5 mm
```

The visible rack face shall be treated as the primary datum. The column body shall grow rearward/inward from that datum rather than being arbitrarily centered.

### Exact rail flushness

The extension rack faces shall be **coplanar with the corresponding stock T1 rack faces**.

Requirement:

```text
Nominal face offset: 0.00 mm
Target practical tolerance: ±0.25 mm
```

A straightedge spanning the original T1 rail and extension rail should contact both continuously.

The lower frame shall include registration geometry that establishes this alignment before fasteners are tightened.

### Continuous M5 reinforcement

Each of the four columns shall contain one continuous **M5 × 0.8 threaded rod** from the lower frame to the upper frame.

The rod will preload:

```text
upper frame
    ↓
upper 4U printed module
    ↓
4U splice
    ↓
lower 4U printed module
    ↓
lower frame
```

into one clamped structural stack.

Each rod shall use:

- M5 nyloc nuts,
- 20 mm OD × 5.3 mm ID × 1.2 mm stainless fender washers.

### 4U-to-4U splice

Locked baseline: **internal male/female spigot joint**.

Configuration:

```text
Lower 4U module: male spigot
Upper 4U module: female socket
Spigot engagement: 20-25 mm
Clearance target: ~0.2-0.3 mm per side
Lead-in chamfer: ~0.5-1.0 mm
```

The square / keyed spigot provides:

- lateral alignment,
- anti-rotation,
- shear transfer,
- front-face coplanarity.

The continuous M5 rod provides axial clamping and anti-separation.

The external front/rear rack faces shall remain uninterrupted except for a narrow cosmetic seam.

The splice should be positioned so it does not intersect a heat-set insert boss. The nominal 4U datum remains 177.8 mm even if the internal engagement geometry extends above/below that plane.

The CAD shall include an optional transverse M4 through-bolt provision across the splice, but this bolt is not required in the baseline assembly unless testing shows joint play.

### Print orientation

Each 4U module should be designed to print **horizontally on its side** on the Bambu A1.

The design should avoid unsupported circular horizontal tunnels where possible. The M5 passage may use printable chamfered, diamond, or teardrop geometry if helpful.

---

## 13. Rack Hole Geometry and Rack Threads

The extension must function as a true continuation of the T1 rack.

### Geometry

- Rack unit pitch: `1U = 44.45 mm`
- Hole layout shall be referenced to a single rack datum.
- The extension's first mounting position shall be derived from the topmost existing T1 rack position.
- Left and right front rails must remain parallel and coplanar.
- Hole geometry shall be parameterized.

### Rack-thread implementation

All four custom rack columns, front and rear, shall use **M4 × 0.7 brass heat-set inserts** rather than printed PETG threads.

Purchased insert specification:

```text
Thread: M4 × 0.7
Nominal outside diameter: 6.0 mm
Length: 6.0 mm
Material: brass
Quantity purchased: 100
```

The final printed pilot-bore diameter shall be established with a PETG test coupon rather than simply matching the nominal 6 mm insert OD.

Recommended coupon bore series:

```text
5.2 mm
5.4 mm
5.6 mm
5.8 mm
```

Initial insert-boss target: approximately 11-12 mm outside diameter or equivalent surrounding material.

---

## 14. Top and Bottom Frames

The extension shall use rigid upper and lower perimeter frames.

### Common geometry

```text
Outer envelope: 281 × 200 mm
Nominal frame vertical thickness: 12 mm
```

The top and bottom frame thicknesses are **inside**, not additional to, the 355.6 mm overall extension height.

The frames shall overlap/capture the column ends so the extension remains exactly 8U taller than the original chassis.

### Bottom frame

The bottom frame shall:

- sit directly on the exposed T1 aluminum top structure,
- use the eight selected M4 × 0.7 mounting holes,
- align to the 30 mm left/right aluminum members,
- establish front/rear rail coplanarity through mechanical registration,
- connect all four columns,
- contain the lower M5 tie-rod clamp pockets.

Working beam widths:

```text
Left/right beams: ~30 mm
Front/rear beams: ~15-20 mm
```

### Top frame

The top frame shall:

- preserve the same 281 × 200 mm envelope,
- connect all four columns,
- reproduce the original factory handle-hole pattern,
- support the original 281 × 200 × 4.4 mm acrylic top plate,
- accept the original RackMate handles,
- contain the upper M5 tie-rod clamp pockets,
- hide tie-rod hardware beneath the factory top plate.

### M5 tie-rod pockets

Purchased fender washer:

```text
ID: 5.3 mm
OD: 20.0 mm
Thickness: 1.2 mm
```

Nominal washer pocket:

```text
Diameter: ~20.4-20.6 mm
```

Tie-rod clamp pockets shall be recessed deeply enough to contain:

```text
1.2 mm washer
+ M5 nyloc nut
+ at least ~1.5-1.6 mm thread protrusion past the locking element
```

while keeping all hardware at or below the exterior frame plane.

For a 5.0 mm-high DIN 985-style M5 nyloc, an **8.0 mm deep hardware recess** is an appropriate baseline:

```text
1.2 mm washer
+ 5.0 mm nut
+ 1.6 mm thread protrusion
= 7.8 mm
```

leaving approximately 4 mm of structural web in a 12 mm frame.

Final pocket depth shall be parameterized around the actual purchased nut height.

---

## 15. Rear Structure and Bracing

The extension shall include:

1. one upper rear horizontal crossbar,
2. one lower rear horizontal crossbar,
3. one removable rear diagonal brace.

Concept:

```text
REAR VIEW

┌──────────────────────────┐
│══════════════════════════│  upper crossbar
│\                         │
│  \                       │
│    \                     │
│      \                   │
│        \                 │
│          \               │
│══════════════════════════│  lower crossbar
└──────────────────────────┘
```

The crossbars maintain rear-column spacing.

The diagonal brace provides anti-racking stiffness and shall be removable for service access.

Initial printed diagonal target:

```text
Width: ~15-20 mm
Thickness: ~5-8 mm
```

The design should permit later substitution of aluminum flat bar or another metal brace if prototype testing shows printed bracing is insufficient.

A second diagonal / full X-brace is not required in Revision 1 but may be added if testing shows directional flexibility.

---

## 16. Material Strategy

### Baseline material

**Black PETG**

Reasons:

- easy to print on a Bambu A1,
- more temperature tolerant than PLA,
- tougher than PLA,
- suitable for structural brackets,
- visually compatible with the black RackMate.

### Initial print profile target

| Setting | Target |
|---|---|
| Material | PETG |
| Layer height | ~0.20 mm |
| Walls | 5-6 |
| Top / bottom layers | 5+ |
| Infill | ~30-40% |
| Infill type | Gyroid or cubic |
| Fastener regions | locally reinforced |
| Critical joints | mechanical fasteners preferred |

Very high infill should **not** substitute for good structural geometry.

---

## 17. Hardware Strategy

Preferred hardware:

- metric machine screws,
- washers,
- locknuts,
- captive nuts,
- heat-set inserts,
- optional threaded rods,
- optional metal reinforcement.

### Guidelines

Heat-set inserts are appropriate for:

- removable panels,
- repeated service joints,
- non-critical fastening.

For major structural joints, prefer:

- through-bolts,
- captured nuts,
- metal reinforcement,
- load-spreading washers.

---

## 18. Aesthetic Requirements

The extension should look like an intentional continuation of the RackMate T1.

### Requirements

- Match T1 exterior width.
- Match T1 exterior depth.
- Align major vertical structural lines.
- Keep the T1-to-extension seam narrow and consistent.
- Use black structural parts.
- Avoid exposed oversized brackets where possible.
- Minimize visible hardware on front and side views.
- Provide a visually finished top edge.
- Avoid a visibly improvised "stack of brackets" appearance.

Desired visual concept:

```text
┌──────────────────────────┐
│                          │
│    CUSTOM UPPER 8U       │
│                          │
│                          │
├──────────────────────────┤
│                          │
│    ORIGINAL T1 8U        │
│                          │
│                          │
└──────────────────────────┘
```

The seam should be visually subtle enough that the rack reads as one approximately 16U enclosure.

---

## 19. Optional Side Panels

A later revision may support smoked acrylic side panels similar to the stock RackMate T1.

Possible design:

- removable 2-3 mm smoked acrylic,
- captive edge channels,
- small screws,
- magnetic attachment,
- printed panel clips.

Side panels are **not required for Revision 1**.

The structural frame must not depend on acrylic panels for primary stiffness unless explicitly redesigned around them.

---

## 20. Equipment Placement Strategy

Heavy equipment should remain in the original lower T1 wherever possible.

Example:

```text
TOP

┌──────────────────────────┐
│ patch panel / networking │
├──────────────────────────┤
│ switch                   │
├──────────────────────────┤
│ mini PCs / lightweight   │
├──────────────────────────┤
│ misc. gear               │
├──────────────────────────┤
│                          │
│      original T1         │
│                          │
│      Jonsbo N2 NAS       │
│                          │
│      heavy hardware      │
│                          │
└──────────────────────────┘

BOTTOM
```

This minimizes overturning moment and stress on the printed upper structure.

---

## 21. Anti-Tip Requirement

A 16U-equivalent mini rack is tall relative to its footprint.

A defined anti-tip strategy is required before the design is considered complete.

Possible solutions:

- attach rack to wall,
- attach rack to desk,
- use a rear restraint strap,
- add a wider base,
- mechanically connect rack to shelving,
- use a weighted lower base.

The CAD should include optional mounting points for a restraint if feasible.

---

## 22. Physical Measurements Required Before Final CAD

The implementation agent should **not finalize mating geometry** until the following are measured.

| ID | Measurement | Target Precision |
|---|---|---:|
| M-01 | Center-to-center distance between the two screws on one handle | ±0.1 mm |
| M-02 | X/Y location of all four handle holes relative to a repeatable rack datum | ±0.2 mm |
| M-03 | Handle-hole thread size and pitch | Confirm physically |
| M-04 | Usable thread depth | ±0.5 mm |
| M-05 | Top aluminum member width | ±0.2 mm |
| M-06 | Top aluminum member thickness / profile | ±0.2 mm |
| M-07 | External body width at top | ±0.2 mm |
| M-08 | External body depth | ±0.2 mm |
| M-09 | Front rail hole center spacing | ±0.2 mm |
| M-10 | Vertical distance from topmost rack hole to top T1 surface | ±0.2 mm |
| M-11 | Geometry around handle mounting holes | photo + dimensions |
| M-12 | Any protruding screws, lips, acrylic edges, or obstacles on the top surface | photo + dimensions |

Internet dimensions are adequate for rough architecture only.

Final interface CAD should use measurements from the actual T1.

---

## 23. Recommended Measurement Datum

For repeatable measurements, define a reference coordinate system.

Suggested origin:

```text
front-left outer corner of the T1 top frame
```

Axes:

```text
X = left-to-right
Y = front-to-back
Z = upward
```

Measure all attachment-hole locations from this datum.

Example:

```text
Handle hole 1 = (X1, Y1)
Handle hole 2 = (X2, Y2)
Handle hole 3 = (X3, Y3)
Handle hole 4 = (X4, Y4)
```

This is more reliable than separately measuring spacing between neighboring holes.

---

## 24. Parametric CAD Requirements

The CAD should be parameter-driven.

Suggested parameters:

### T1 envelope

```text
body_width
body_depth
top_member_width
top_member_height
top_profile_geometry
```

### Attachment

```text
handle_hole_x[]
handle_hole_y[]
handle_thread_diameter
handle_thread_pitch
usable_thread_depth
```

### Rack geometry

```text
u_pitch = 44.45
extension_u = 8
rail_center_spacing
rail_hole_pattern
rail_hole_offset
```

### Print tolerances

```text
registration_clearance
bolt_clearance
insert_clearance
joint_clearance
panel_clearance
```

### Structure

```text
wall_thickness
rib_thickness
fillet_radius
joint_overlap
upright_depth
upright_width
```

### Segmentation

```text
segment_u = 4
bottom_frame_segments
top_frame_segments
joint_type
```

---

## 25. Purchased Hardware / Current BOM

The following parts have already been purchased and shall be treated as preferred design inputs unless prototype testing shows a clear reason to change them.

### M4 brass heat-set inserts

**Listing:** HANGLIFE M4 heat-set threaded inserts  
**Amazon:** https://www.amazon.com/dp/B0CS6XGMFD

```text
Internal thread: M4 × 0.7
Nominal OD: 6.0 mm
Length: 6.0 mm
Material: brass
Quantity: 100
```

Intended use:

- front and rear rack mounting threads,
- optionally top-handle attachment,
- optional serviceable accessory joints.

### M5 nylon-insert lock nuts

**Listing:** Fullerkreg stainless nylon-insert lock nuts  
**Amazon:** https://www.amazon.com/Fullerkreg-Self-Locking-Stainless-18-8%EF%BC%8CPlain-Quantity/dp/B078NNFT93

Required / selected variant:

```text
Thread: M5 × 0.8
Type: nylon-insert lock nut
Material: stainless steel
```

Intended use:

- clamping the four continuous M5 vertical tie rods.

### M5 fender washers

**Listing:** Bykonh stainless steel fender washers  
**Amazon:** https://www.amazon.com/Bykonh-Stainless-Steel-Fender-Washers/dp/B0H4Q6ZB36

```text
Inside diameter: 5.3 mm
Outside diameter: 20.0 mm
Thickness: 1.2 mm
Material: stainless steel
Fit: M5 hardware
```

Intended use:

- spread M5 tie-rod preload across PETG,
- reduce local compressive stress and long-term indentation.

CAD washer-pocket target:

```text
Pocket diameter: ~20.4-20.6 mm
Pocket depth: ~1.3-1.5 mm
```

### M5 threaded rods

**Listing:** HIPICCO M5 × 400 mm fully threaded rods, 304 stainless steel, 4-pack  
**Amazon ASIN:** B0C94Y8JS1  
**Purchase price:** approximately $14 total

```text
Thread: M5 × 0.8
Length as purchased: 400 mm
Material: 304 stainless steel
Quantity purchased: 4
Target final cut length: 355 mm each
```

Intended use:

- one continuous tie rod per vertical column,
- axial preload of the upper frame, upper 4U module, splice, lower 4U module, and lower frame.

### Hardware still to purchase

- M4 × 0.7 machine screws for the eight lower T1 attachment points, final length TBD.
- Additional M4 rack screws as needed.
- Black PETG filament.
- Optional transverse M4 splice bolts if retained after testing.
- Optional anti-tip restraint hardware.

---

## 26. CAD Deliverables

The implementation agent should produce:

- parametric source CAD,
- STEP files,
- 3MF files,
- assembly model,
- exploded view,
- hardware BOM,
- parameter table,
- dimensioned interface drawing,
- print orientation recommendations,
- assembly instructions,
- prototype validation plan.

Preferred source formats include:

- CadQuery,
- FreeCAD,
- OpenSCAD,
- another reproducible parametric CAD format.

STEP export is strongly preferred for interoperability.

---

## 27. Functional Requirements

| ID | Priority | Requirement |
|---|---|---|
| FR-01 | MUST | Provide 8U additional usable rack space |
| FR-02 | MUST | Maintain continuous rack-hole pitch |
| FR-03 | MUST | Require no drilling or cutting of the T1 |
| FR-04 | MUST | Allow removal and restoration of factory handles |
| FR-05 | MUST | Fit ordinary 10-inch rack accessories |
| MR-01 | MUST | Match T1 exterior width and depth closely |
| MR-02 | MUST | Transfer vertical load through broad structural contact |
| MR-03 | MUST | Reuse factory top / handle holes if verified |
| MR-04 | MUST | Include lateral mechanical registration |
| MR-05 | MUST | Include lower frame, four uprights, and upper frame |
| MR-06 | SHOULD | Include anti-racking bracing |
| PF-01 | MUST | Every printed part fits 256 × 256 × 256 mm |
| PF-02 | SHOULD | Structural joints avoid weak layer orientations |
| PF-03 | SHOULD | Minimize support-heavy geometry |
| PF-04 | SHOULD | Use individually replaceable modules |
| AS-01 | MUST | Align visually with T1 |
| AS-02 | SHOULD | Minimize visible fasteners |
| AS-03 | SHOULD | Approximate T1 matte-black appearance |
| SF-01 | MUST | Heavy hardware should remain low |
| SF-02 | MUST | Define an anti-tip strategy |

---

## 28. Prototype Strategy

Do **not** begin by printing the entire rack.

Recommended sequence:

### Phase 1: Interface coupon

Print only:

- one or two handle-hole mounting points,
- T1 locating lip,
- a small section of the lower frame.

Validate:

- screw spacing,
- thread compatibility,
- fit,
- tolerance,
- seating.

### Phase 2: Corner prototype

Print:

- one lower frame corner,
- one lower 4U upright,
- one upper 4U upright,
- upright seam.

Validate:

- stiffness,
- joint geometry,
- hardware accessibility,
- print orientation.

### Phase 3: Single rail stack

Assemble one complete 8U vertical member.

Validate:

- straightness,
- rack-hole pitch,
- bending stiffness,
- seam strength.

### Phase 4: Empty full frame

Build:

- four uprights,
- lower frame,
- upper frame,
- bracing.

Check:

- squareness,
- twist,
- wobble,
- alignment,
- visual fit.

### Phase 5: Rack equipment fit

Test mounting:

- one standard 1U shelf or switch,
- equipment at lowest extension position,
- equipment near the 4U seam,
- equipment at highest extension position.

### Phase 6: Load testing

Use inert ballast before installing valuable electronics.

Increase load gradually.

Inspect:

- joint movement,
- screw loosening,
- rail deformation,
- plastic whitening,
- cracks,
- permanent deflection.

---

## 29. Acceptance Criteria

| ID | Category | Acceptance Criterion |
|---|---|---|
| AC-01 | Fit | Extension seats fully on the T1 without rocking |
| AC-02 | Alignment | Exterior is visually flush from front and side |
| AC-03 | Attachment | Top mounting screws install without cross-threading or bottoming out |
| AC-04 | Rack geometry | Standard 1U equipment mounts at all tested positions |
| AC-05 | Printability | Every part fits the Bambu A1 |
| AC-06 | Modularity | Individual components can be replaced independently |
| AC-07 | Stiffness | Empty frame shows no obvious joint slip under moderate hand-applied lateral force |
| AC-08 | Load test | Frame passes staged ballast testing |
| AC-09 | Reversibility | Original handles can be reinstalled |
| AC-10 | Safety | Anti-tip method is defined and implemented |

---

## 30. Open Design Decisions

These should be refined before implementation is considered final.

### OD-01: Lower-frame segmentation

Determine:

- number of printed pieces,
- seam positions,
- fastener strategy.

### OD-02: Upright reinforcement

Choose between:

- printed-only,
- steel threaded rod,
- aluminum flat bar,
- aluminum extrusion,
- internal metal spline.

### OD-03: Rack mounting hole implementation

Choose between:

- threaded printed holes,
- heat-set inserts,
- captive nuts,
- cage-nut-like geometry,
- through-bolts.

### OD-04: Rear rails

Determine whether the extension needs:

- front rails only,
- front + rear rails,
- optional rear support.

### OD-05: Side panels

Determine whether Revision 1 includes:

- no side panels,
- smoked acrylic,
- removable printed panels.

### OD-06: Top handles

Determine whether to:

- omit handles,
- reuse original T1 handles on the new top,
- design custom handles.

### OD-07: Anti-tip mechanism

Select the final restraint strategy based on rack location.

### OD-08: Rated upper load

Do not assign a final payload rating until prototype load testing.

### OD-09: Maximum visual seam

Define an acceptable T1-to-extension gap.

Suggested initial target:

```text
≤ 0.5-1.0 mm visually
```

---

## 31. Preliminary Implementation Recommendation

A strong first architecture is:

```text
T1
│
├── segmented rigid lower interface frame
│   ├── factory handle-hole fasteners
│   └── shallow locating lips
│
├── four lower 4U upright modules
│
├── reinforced 4U splice joints
│
├── four upper 4U upright modules
│
├── segmented rigid top frame
│
└── rear diagonal / rigid bracing
```

Optional hidden reinforcement can be added later if printed-only stiffness is insufficient.

---

## 32. Remaining Design Decisions

The core mechanical architecture is substantially locked.

### RD-01: Verify purchased M5 nyloc nut height

The tie-rod recess is currently designed around a low-profile DIN 985-style M5 nyloc approximately 5 mm tall.

Measure the actual purchased nut height when received. The CAD parameter shall adjust pocket depth if necessary.

### RD-02: Finalize M5 threaded-rod cut length

Current design target:

```text
Overall extension height: 355.6 mm
Top/bottom hardware fully recessed inside that envelope
Target rod cut length: 355 mm
Recommended purchased stock: ≥400 mm
```

See the dedicated tie-rod section below.

### RD-03: Validate heat-set insert pilot diameter

Print a PETG test coupon before final rail production.

### RD-04: Decide final anti-tip hardware

The completed ~16U system shall have an external restraint strategy appropriate to its installed location.

---

## 33. M5 Tie-Rod Length

### Design logic

The extension's relocated top plane must be exactly one additional 8U span above the original T1 top plane:

```text
8 × 44.45 mm = 355.6 mm
```

The 12 mm upper and lower frames are included within that 355.6 mm envelope.

The M5 rods therefore run almost the full extension height.

Using an 8.0 mm recessed hardware pocket at each end with:

```text
washer = 1.2 mm
DIN 985 M5 nyloc ≈ 5.0 mm
desired thread beyond nut ≈ 1.6 mm (2 × 0.8 mm pitches)
```

requires:

```text
1.2 + 5.0 + 1.6 = 7.8 mm
```

of axial hardware depth.

An 8.0 mm pocket leaves ~0.2 mm clearance to the exterior surface at each end.

Therefore a centered rod may be cut to approximately:

```text
355.6 mm - 0.4 mm = 355.2 mm
```

### Production target

For practical cutting and deburring:

```text
TARGET CUT LENGTH: 355 mm
```

Tolerance target:

```text
355.0 mm ± 0.5 mm
```

This keeps both rod ends slightly recessed while still providing approximately two thread pitches beyond a 5 mm-high nyloc nut.

### Purchase recommendation

Buy:

```text
4 × M5 × 0.8 threaded rods
minimum stock length: 400 mm each
```

Then cut each to 355 mm after the printed frame-pocket geometry and actual nyloc-nut height are confirmed.

Do not buy 350 mm rods: they are too short for the current architecture.

400 mm rods are preferred over longer stock because they require minimal trimming while providing enough tolerance for design adjustment.

---

## 34. M5 Threaded-Rod Cutting Procedure

The purchased rods are 400 mm long and are intended to be cut to approximately 355 mm after the final nut height and frame-pocket geometry are confirmed.

### Recommended tools

Preferred:

- rotary tool / Dremel,
- reinforced metal cutoff wheel,
- vise,
- small metal file,
- eye protection.

Acceptable alternative:

- fine-tooth hacksaw, approximately 24-32 TPI,
- vise,
- metal file.

### Procedure

1. Confirm the final CAD cut length before cutting.
2. Thread two ordinary M5 × 0.8 nuts onto the rod past the intended cut location.
3. Lock the two nuts against each other.
4. Measure from the finished reference end and mark the cut position.
5. Clamp the rod securely using soft jaws, wood, cardboard, or another thread-protecting interface.
6. Cut the rod slightly long if necessary.
7. File the cut end to final length.
8. Add a small approximately 45° lead-in chamfer to the cut edge.
9. Back the two M5 nuts off across the cut end to help reform / clean any damaged first thread.
10. Verify that an M5 nyloc nut threads smoothly by hand.

### Dimensional target

```text
Nominal cut length: 355.0 mm
Target tolerance: ±0.5 mm
```

Do not cut the rods until:

- actual purchased M5 nyloc nut height has been measured,
- top and bottom tie-rod pocket geometry is finalized,
- the CAD audit confirms the 355 mm target remains correct.

---

## 35. Audit Checklist

Before detailed CAD implementation, an independent reviewer should explicitly verify the following.

### Geometry

- 281 × 200 mm external T1 / top-plate envelope is used consistently.
- 355.6 mm added height represents exactly 8U.
- The 12 mm top and bottom frames are contained **within**, not added to, the 355.6 mm height.
- Front and rear rack faces remain coplanar with the corresponding stock T1 rack faces.
- The 4U splice does not shift the external rack-hole datum.

### T1 interface

- All modeled T1 top-frame threads are M4 × 0.7.
- Eight lower attachment screws use the selected structural-hole coordinates.
- Bottom-frame geometry bears directly on the T1 aluminum frame rather than suspending the extension from screws.
- The design remains fully reversible.

### Rack interface

- All four columns are rack-capable.
- Rack threads use the purchased M4 × 0.7, 6 mm OD × 6 mm brass heat-set inserts.
- Heat-set insert bosses do not interfere with the M5 tie-rod channel.
- Rack-hole pitch remains 44.45 mm per U across the T1-extension seam.

### Column structure

- External baseline is approximately 30 × 30 mm.
- Columns are hollow / ribbed rather than unnecessarily solid.
- Each 8U column is split into 4U + 4U modules.
- Splice uses 20-25 mm male/female spigot engagement.
- M5 tie rod passes continuously through the splice.
- Print orientation is structurally sensible for PETG and avoids trapped support material.

### Tie-rod system

- M5 × 0.8 hardware is used consistently.
- Purchased rods are 400 mm 304 stainless steel.
- Purchased fender washers are 5.3 mm ID × 20 mm OD × 1.2 mm.
- Purchased nyloc nuts are the selected M5 × 0.8 type.
- Nut height is physically measured before locking pocket depth.
- Rod cut length is recalculated from the final pocket geometry rather than copied blindly.

### Top assembly

- Original 281 × 200 × 4.4 mm acrylic top plate is reused.
- Original aluminum handles are reused.
- Factory handle-hole coordinates are reproduced accurately.
- M5 tie-rod hardware remains hidden below the factory top plate.

### Bracing and safety

- Upper and lower rear crossbars are present.
- Rear diagonal brace is removable.
- Prototype load testing is defined before valuable equipment is installed.
- Anti-tip restraint remains a required part of final installation.

---

## 36. Sources / Evidence

### DeskPi RackMate T1

Official product / technical information:

https://wiki.deskpi.com/rackmate/rackmate-t1/

Relevant information:

- 10-inch rack format
- 8U usable capacity
- approximately 355 mm usable rack height
- aluminum structural frame

### DeskPi RackMate stacking hardware

Official DeskPi RackMate accessories:

https://deskpi.com/products/deskpi-rackmate-accessories

Relevant information:

- stacking hardware intended for T0/T1/T2
- confirms that vertical RackMate stacking is an intended use case
- its M3 accessory hardware is not used to define this custom interface; the actual T1 top-frame holes were physically verified as M4 × 0.7

### Bambu Lab A1 specifications

https://bambulab.com/en-us/a1/tech-specs

Relevant information:

- 256 × 256 × 256 mm build volume
- PETG supported / suitable

### Community stacked RackMate build

https://www.reddit.com/r/homelab/comments/1k73b8t/stacked_deskpi_rackmate_t1_on_t2/

Relevant information:

- user reports stacking RackMate chassis using handle screws
- supports reuse of the handle mounting interface

### Secondary RackMate mechanical reference

https://github.com/Novotarskyi/ivan-bohun/blob/main/docs/1_hardware/16_rack.md

Relevant provisional dimensions:

- approximately 282.25 mm external width
- approximately 200 mm depth
- approximately 236.53 mm rail-hole center spacing
- approximately 222.25 mm clear rail opening

These values should be verified against the physical rack before final CAD.

---

## 37. Revision History

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-09-13 | Initial PRD. Defines upper-mounted 8U architecture, T1 handle-hole interface concept, A1-compatible modular structure, measurement requirements, and prototype strategy. |
| 0.2 | 2026-09-13 | Adds verified physical T1 geometry, confirms M4×0.7 top-frame threads, adopts factory lid/handle relocation, eight-bolt lower interface, reinforced 4U+4U columns with M5 tie rods, M4 heat-set rack threads, and purchased hardware BOM. |
| 0.3 | 2026-09-13 | Locks 30×30 mm rack-capable front/rear columns, exact rail coplanarity, 20-25 mm spigot splice, 12 mm frames within the 8U envelope, rear crossbars plus removable diagonal brace, and 355 mm target M5 tie-rod cut length. |
| 0.4 | 2026-09-13 | Records purchased HIPICCO M5×0.8×400 mm stainless tie rods, adds rod cutting/deburring procedure, and adds an independent-audit checklist covering geometry, interfaces, inserts, tie rods, bracing, and safety assumptions. |
