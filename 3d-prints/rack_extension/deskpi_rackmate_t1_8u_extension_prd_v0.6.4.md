# DeskPi RackMate T1 8U Upper Extension
## Product Requirements & Mechanical Design Specification

**Version:** 0.6.4  
**Status:** Preliminary CAD allowed; rack-hole phase is physically confirmed; seam geometry and tie-rod end-block packaging remain explicit pre-production gates  
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
| Stock T1 clear rack opening | **222.5 mm** | Physically measured |
| Top lid-support plane → top rack-hole center | **28.8 mm** | Physically measured |
| Top rack hole 1 → hole 2 | **15.9 mm** | Physically measured |
| Top rack hole 2 → hole 3 | **15.9 mm** | Physically measured |
| Purchased M5 nyloc nut height | **7.8 mm** | Physically measured |

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

## 6. Critical Manufacturing and 8U Geometry Constraint

The Bambu Lab A1 build volume is:

```text
256 × 256 × 256 mm
```

The extension target envelope is:

```text
Width:   281 mm
Depth:   200 mm
Added lid-support-plane height: 355.6 mm
```

### Critical datum definition

The **355.6 mm** dimension is defined between:

1. the original T1 aluminum **lid-support plane**, and
2. the relocated extension **lid-support plane**.

Because the original 4.4 mm acrylic top plate is reused at the new top, its thickness cancels from the added-height calculation.

### 8U does not automatically mean 8U usable

A correct 355.6 mm outer datum-to-datum height is necessary but not sufficient.

The CAD must separately prove that:

- all 8U rack-hole positions remain usable,
- top and bottom frame members do not obstruct equipment ears or chassis bodies,
- screws and heat-set inserts at the extreme U positions remain accessible,
- the first and last rack holes do not collide with the 12 mm frame zones,
- the actual T1 rack-hole **phase** is continued exactly across the seam.

Do not assume that simply repeating a 44.45 mm pitch produces a valid continuation.

### Measured rail phase and seam consequence

Physical T1 rail-phase measurements:

```text
lid-support plane → highest existing rack-hole center = 28.8 mm downward
top hole 1 → hole 2 = 15.9 mm
hole 2 → hole 3 = 15.9 mm
```

Using `z = 0` at the original aluminum lid-support plane and positive `z` upward, the highest existing hole is approximately:

```text
z = -28.8 mm
```

If the conventional repeating pattern is assumed provisionally, the next theoretical centers are approximately:

```text
highest existing hole                  -28.800 mm
next theoretical hole                  -16.100 mm
following theoretical hole              -0.225 mm
first theoretical hole above the seam  +15.650 mm
```

This exposes an important seam issue:

- a printed extension that begins entirely above `z = 0` cannot physically provide rack holes whose centers would fall below that plane;
- therefore, continuous pitch alone does **not** prove eight additional fully usable U;
- some theoretical positions may already exist in the stock metal, may be obstructed by the top structure, or may simply be absent.

### Required seam proof

Before production rail geometry is approved, the CAD package shall include a dimensioned **stock-to-extension seam drawing** showing:

- original aluminum lid-support plane,
- stock top-frame metal thickness/profile,
- highest existing stock rack holes,
- next theoretical hole centers,
- first extension rack holes,
- top/bottom frame geometry,
- equipment panel/ear envelope at the seam,
- screw-head and tool clearance,
- whether each theoretical hole position is:
  - present in stock metal,
  - provided by the extension,
  - obstructed,
  - intentionally omitted.

The design shall not claim "8 additional usable U" until this seam drawing proves the actual mounting pattern and equipment clearance.

### Pattern confirmation

R-04 has now been physically measured:

```text
R-04: hole 3 center → hole 4 center ≈ 12.7 mm
```

Together with the previous measurements:

```text
hole 1 → hole 2 ≈ 15.9 mm
hole 2 → hole 3 ≈ 15.9 mm
hole 3 → hole 4 ≈ 12.7 mm
```

this confirms the conventional repeating three-hole rack pattern closely enough for preliminary CAD.

Use the measured stock phase as the governing datum at the seam. The stock-to-extension seam drawing is still required because two theoretical continuation positions fall at or below the original lid-support plane.

### Print segmentation

- Full-height 355.6 mm rails cannot be printed vertically as one piece.
- The columns remain split into two printable modules.
- Any frame member longer than 256 mm must either fit diagonally on the bed or be segmented.
- Spigot engagement and frame overlap must add **zero assembled height** beyond the defined 355.6 mm lid-support-plane spacing.

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

The M4 fasteners should primarily provide:

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

The extension shall use four reinforced hollow box columns. All four columns remain rack-capable.

### Overall height and physical stack

The extension adds exactly:

```text
8U = 355.6 mm
```

between the original and relocated lid-support planes.

The previous shorthand of two 177.8 mm free-standing column bodies plus two separate 12 mm frames is **not permitted**, because that would exceed the 355.6 mm envelope.

Two implementation paths are allowed:

#### Path A: conventional end bearing

```text
bottom frame: 12.0 mm
lower clear column body: 165.8 mm
upper clear column body: 165.8 mm
top frame: 12.0 mm
total: 355.6 mm
```

#### Path B: full 177.8 mm module envelopes

Full nominal 4U module envelopes may be retained only if the frame geometry overlaps / captures them by a precisely dimensioned amount so assembled height remains exactly 355.6 mm.

Spigot engagement must likewise add **zero assembled height**.

### Column cross-section

Baseline remains:

```text
External envelope: ~30 × 30 mm nominal
Structure: hollow ribbed box
Nominal outer walls: ~4 mm
M5 tie-rod clearance bore: ~6.0-6.5 mm
```

The rack face is the primary datum. Column material grows away from that face.

### Exact rail flushness

Each extension rail face shall remain coplanar with its corresponding stock T1 rail face:

```text
front extension rail ↔ front stock T1 rail
rear extension rail  ↔ rear stock T1 rail

Nominal face offset: 0.00 mm
Target practical tolerance: ±0.25 mm
```

### Transverse rack-opening clearance

Depth coplanarity alone does not guarantee that equipment fits between the left and right columns.

The CAD shall include a dimensioned front section showing:

```text
overall external width
left/right structural-member intrusion
rack-hole center spacing
clear opening between opposing rail/column faces
heat-set boss intrusion into the opening
```

The extension clear opening shall be **no smaller than the physically measured clear opening of the stock T1**.

The physically measured stock clear opening is:

```text
222.5 mm
```

With a 281 mm overall width, the symmetric maximum inward projection per side is:

```text
(281 - 222.5) / 2 = 29.25 mm
```

Therefore, two fully inward-projecting 30 mm columns would leave only:

```text
281 - 2 × 30 = 221 mm
```

which would narrow the stock opening by 1.5 mm total and is not acceptable.

Therefore, `30 × 30 mm` remains only a nominal gross envelope. The **maximum stock-matching inward projection is 29.25 mm per side**, and a small manufacturing clearance may justify targeting slightly less.

The transverse section may use:

- an asymmetric approximately 30 mm external-depth × ≤29.25 mm inward-width section,
- outward-biased structure,
- local reliefs,
- or merged reinforced insert strips,

while preserving the stock external silhouette and rack-hole alignment.

### Continuous M5 reinforcement

Each column contains one continuous M5 × 0.8 threaded rod.

The rod is a **clamping member**, not a substitute for a proper compression load path.

Required load path:

```text
nut
↓
washer
↓
supported bearing seat / end block
↓
column walls + structural ribs
↓
splice bearing shoulders
↓
lower supported bearing seat
↓
washer
↓
nut
```

A thin pocket floor spanning the hollow cavity is not acceptable.

### Required end-block geometry

At both top and bottom of every column, the CAD shall provide a reinforced end block / crosshead that:

- directly supports the 20 mm washer,
- transfers washer load into at least two opposing column walls,
- includes ribs or a solid bearing bridge,
- leaves no unsupported thin membrane beneath the washer,
- maintains adequate material around the M5 bore,
- remains inspectable for cracking or creep.

The exact end-block thickness shall be determined by CAD section review and prototype testing.

### 4U-to-4U splice

The male/female spigot concept remains, but must satisfy explicit interference constraints.

Baseline:

```text
Lower module: male spigot
Upper module: female socket
Engagement: 20-25 mm
Clearance: ~0.2-0.3 mm per side
Lead-in chamfer: ~0.5-1.0 mm
```

The splice must include positive bearing shoulders so compression is transmitted through printed structure rather than through the tie rod alone.

The spigot/socket geometry shall include reliefs where necessary to avoid:

- heat-set insert bosses,
- installed rack-screw tips,
- the M5 tie-rod bore,
- optional transverse splice-bolt hardware.

A transverse M4 splice bolt, if retained, must be intentionally offset so it cannot intersect the M5 rod.

### Required section checks

Detailed CAD must provide section views at:

1. an ordinary rack-insert location,
2. a rack-insert location overlapping the splice engagement zone,
3. an end-frame location near the tie-rod washer/nut pocket.

Each section must show:

- M5 rod channel,
- heat-set insert,
- maximum permitted rack-screw penetration,
- surrounding printed wall/rib thickness,
- spigot/socket material where applicable,
- required tool clearance.

## 13. Rack Hole Geometry and Rack Threads

The extension must function as a true continuation of the T1 rack.

### Geometry

- Nominal U pitch: `44.45 mm`
- The actual **hole phase** shall be measured from the physical T1 before final CAD.
- Extension holes shall continue the T1 pattern from a single measured datum.
- Each front/rear extension rail shall remain parallel and coplanar with its corresponding stock T1 rail.

### Rack-thread implementation

All four rack columns shall use the purchased M4 × 0.7 brass heat-set inserts.

Purchased insert:

```text
Thread: M4 × 0.7
Nominal OD: 6.0 mm
Length: 6.0 mm
Material: brass
```

### Boss requirements

Each insert boss shall have:

```text
minimum axial hole depth before blind back wall: 7.4 mm target
minimum insert containment depth: >6.0 mm
initial boss outside diameter target: 12-18 mm, subject to packaging
```

The 7.4 mm starting depth corresponds to:

```text
6.0 mm insert length
+ 2 × 0.7 mm thread pitches
```

This is a design starting point, not a validated PETG strength value.

Bosses shall be tied into adjacent column walls with ribs rather than existing as isolated cylinders.

Where adjacent bosses geometrically overlap, the CAD shall treat them as a **continuous reinforced rail strip**, not as intersecting independent cylinders. This is especially important near the 4U splice.

### Pilot diameter validation

The final pilot bore shall be determined by PETG coupon testing.

Suggested coupon set:

```text
5.2 mm
5.4 mm
5.6 mm
5.8 mm
```

### Rack-screw penetration limit

The design shall specify a maximum permitted screw penetration beyond the brass insert so an installed M4 screw cannot contact:

- the M5 tie rod,
- splice material,
- opposite wall,
- end-block hardware.

A blind rear wall, if used, is a **clearance boundary, not a tightening stop**.

The longest permitted rack screw shall retain positive clearance from that wall. Tightening force shall be reacted by the equipment ear and brass insert, never by bottoming the screw against PETG.

If practical, the permitted screw length shall be enforced geometrically and documented on the assembly drawing.

## 14. Top and Bottom Frames

The extension uses rigid upper and lower perimeter frames.

### Common envelope

```text
Outer envelope: 281 × 200 mm
Nominal frame zone: 12 mm
```

The frame zones are contained within the 355.6 mm lid-support-plane spacing.

### Usable rack-space requirement

The frame geometry must not consume usable rack positions.

Before the design is accepted, CAD must demonstrate that:

- all required rack-hole centers remain unobstructed,
- equipment ears can sit flat against the rails at the lowest and highest U positions,
- equipment chassis bodies clear the frame crossmembers,
- rack screws at extreme positions can be installed and removed.

If necessary, the front/rear frame crossmembers shall be moved behind the rack face, relieved, pocketed, or locally shaped rather than treated as full rectangular beams across the equipment opening.

### Bottom frame

The bottom frame shall:

- sit directly on the exposed T1 aluminum top structure,
- use the eight selected M4 × 0.7 mounting holes,
- align to the 30 mm side members,
- establish rail coplanarity through positive registration,
- connect all four columns,
- contain reinforced lower tie-rod end blocks.

### Top frame

The top frame shall:

- preserve the 281 × 200 mm envelope,
- connect all four columns,
- reproduce the factory handle-hole pattern,
- support the original 281 × 200 × 4.4 mm acrylic top plate,
- contain reinforced upper tie-rod end blocks,
- keep tie-rod hardware below the factory lid-support surface.

### Tie-rod bearing seats

The purchased M5 nyloc nut height is now physically measured at:

```text
7.8 mm
```

This invalidates the earlier 5 mm nut assumption. The end-block / hardware pocket must be designed around the actual 7.8 mm nut, and the old nominal 8 mm recess concept is **retired**.

The tie-rod end geometry may use the 12 mm frame zone only if the supported bearing seat, nut/washer stack, thread protrusion, tip allowance, and exterior clearance all coexist without reducing the required structural bridge. Local end-block structure may extend into the column overlap region while remaining inside the overall 355.6 mm envelope.

The purchased washer remains:

```text
ID: 5.3 mm
OD: 20.0 mm
Thickness: 1.2 mm
```

The washer shall not bear on a thin recessed floor spanning a hollow cavity.

Each washer seat must be supported by a structural end block that carries preload into the column walls and frame ribs.

Any change to nut height or recess depth shall trigger a new section review of:

- residual web thickness,
- rib geometry,
- washer support,
- tool access,
- PETG creep path.

Pocket depth is therefore **not** a free parameter.

### Bottom-nut capture and serviceability

The bottom fastener arrangement must be operable before the extension is seated on the T1 and must not require access from below afterward.

The design shall include one of:

- anti-rotation hex capture for the lower nut,
- captive nut geometry,
- captive rod geometry with top-side adjustment.

The preferred arrangement shall allow final preload adjustment from the top side without the lower hardware spinning.

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
Current design estimate: ~355 mm each; final cut length remains TBD from measured assembled geometry
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
- **dimensioned stock-to-extension seam drawing** proving actual rack-hole continuity/usability across the original lid-support plane.
- **dimensioned critical corner section** showing, where applicable:
  - T1/frame attachment screws,
  - reinforced tie-rod bearing seat,
  - M5 rod,
  - extreme rack insert / boss,
  - maximum permitted rack-screw penetration,
  - splice engagement or nearest interference envelope,
  - overall outer width,
  - clear opening between opposing rails/columns,
  - rack-hole center spacing,
  - tool-access envelope.

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

## 30. Locked Architecture and Audit Gates

The following architecture is selected for Revision 1 unless audit-driven interference analysis forces a change:

- top-mounted 8U extension,
- 281 × 200 mm envelope,
- original acrylic lid and handles relocated to the new top,
- eight M4 × 0.7 lower chassis fasteners,
- four ~30 × 30 mm hollow rack-capable columns,
- 4U + 4U modular printing,
- internal spigot splice with 20-25 mm engagement,
- one continuous M5 tie rod per column,
- M4 heat-set inserts on front and rear rack faces,
- upper/lower rear crossbars,
- one removable rear diagonal brace.

The following remain **audit gates**, not open architecture choices:

1. rack-hole phase, stock-to-extension seam continuity, extreme-U clearance, and transverse clear opening,
2. tie-rod washer-seat load path,
3. insert/splice/end-pocket interference,
4. tie-rod preload and PETG creep,
5. final rod cut length,
6. anti-tip implementation.

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

### RD-01: M5 nyloc height resolved; redesign end block around actual hardware

Measured purchased nut height:

```text
7.8 mm
```

The prior low-profile ~5 mm assumption is invalid. The detailed corner section must establish a supported load path and adequate space for the actual nut/washer/thread stack before the tie-rod pocket is accepted.

### RD-02: Finalize M5 threaded-rod cut length

Current design target:

```text
Overall extension height: 355.6 mm
Top/bottom hardware fully recessed inside that envelope
Current rod cut estimate: ~355 mm; final length TBD after prototype measurement
Recommended purchased stock: ≥400 mm
```

See the dedicated tie-rod section below.

### RD-03: Validate heat-set insert pilot diameter

Print a PETG test coupon before final rail production.

### RD-04: Decide final anti-tip hardware

The completed ~16U system shall have an external restraint strategy appropriate to its installed location.

---

## 33. Tie-Rod Preload, Creep, and Assembly Method

The M5 rods are intended to maintain structural clamping, but PETG is viscoelastic and will relax under sustained compression.

### Nyloc limitation

A nyloc nut resists nut rotation. It does **not** compensate for:

- PETG creep,
- compression-set,
- embedment of washer seats,
- dimensional relaxation of printed joints.

Therefore, "nut has not rotated" does not imply "preload is unchanged."

### Assembly requirement

Do not use generic steel-joint M5 torque tables.

Nyloc running resistance also contaminates torque readings, so tightening torque cannot be interpreted directly as clamp force without calibration.

### Prototype seating and creep procedure

1. Assemble one complete column with final washers, nuts, end blocks, splice, and printed materials.
2. Tighten gradually using either:
   - a calibrated torque procedure that separately characterizes nyloc running torque, or
   - a controlled nut-turn / compression method.
3. Confirm that all printed bearing shoulders are fully seated.
4. Record:
   - nut position,
   - column overall length,
   - visible joint gaps,
   - local end-block deformation.
5. Hold the column at representative compressive load and expected operating temperature.
6. Re-measure after:
   - 1 hour,
   - 24 hours,
   - 7 days.

### Retained-clamping validation

Seating alone is not sufficient.

After the creep / temperature dwell, the prototype shall undergo a representative **lateral and eccentric equipment-load test** applied through the rack interface.

Acceptance criteria shall include explicit limits for:

- joint opening,
- lateral slip,
- permanent column set,
- permanent rack-face misalignment,
- insert movement,
- end-block deformation.

No numeric payload rating may be claimed until those limits are defined and passed.

If a numeric retained preload is later claimed, it must be established by direct force measurement, calibrated rod strain, or another defensible measurement method rather than inferred from raw tightening torque alone.

### Service inspection

The final assembly instructions shall include:

- an initial re-check after the first 24-72 hours,
- periodic inspection for joint gaps or loosening,
- prohibition against simply increasing torque to compensate for creep without checking PETG deformation.

## 34. M5 Tie-Rod Length

### Status

The previous ~355 mm cut length remains **provisional**, not production-locked.

Purchased rods:

```text
M5 × 0.8
400 mm long
304 stainless steel
quantity: 4
```

### Correct final derivation

Let:

```text
S = measured distance between the two washer bearing seats
W1, W2 = actual washer thicknesses at each end
N1, N2 = actual nut heights at each end
P1, P2 = required FULL-THREAD protrusion beyond each nut
T1, T2 = non-full-thread tip allowance at each rod end caused by chamfer / incomplete threads
C1, C2 = required exterior clearance at each end
```

If the two ends use identical hardware, the simplified nominal equation is:

```text
L = S + 2 × (W + N + P + T)
```

More generally:

```text
L = S
  + (W1 + N1 + P1 + T1)
  + (W2 + N2 + P2 + T2)
```

Exterior pocket depth is a separate constraint at each end:

```text
pocket_depth_1 ≥ W1 + N1 + P1 + T1 + C1
pocket_depth_2 ≥ W2 + N2 + P2 + T2 + C2
```

`P` means **full-thread** protrusion through the locking element. Any chamfered or incomplete thread at the rod tip must be accounted for separately as `T`.

**Do not subtract exterior clearance from the rod-length equation.**

### Infeasible legacy example

The earlier example retained the old 339.6 mm seat spacing while substituting the newly measured 7.8 mm nut height:

```text
S = 339.6 mm
W = 1.2 mm
N = 7.8 mm
P = 1.6 mm
T = 0.0 mm

L = 339.6 + 2 × (1.2 + 7.8 + 1.6)
  = 360.8 mm
```

This is **physically infeasible inside the 355.6 mm extension envelope**.

Its purpose is only to demonstrate that the bearing seats must move inward when using the taller nuts.

### Feasible illustrative geometry

For illustration only, if:

```text
W = 1.2 mm
N = 7.8 mm
P = 1.6 mm
T = 0.0 mm
C = 0.2 mm
```

then each required pocket depth is:

```text
1.2 + 7.8 + 1.6 + 0.2 = 10.8 mm
```

If both bearing seats are therefore located 10.8 mm inward from the two exterior planes:

```text
S = 355.6 - 2 × 10.8
  = 334.0 mm
```

and the idealized rod length becomes:

```text
L = 334.0 + 2 × (1.2 + 7.8 + 1.6)
  = 355.2 mm
```

This leaves only:

```text
12.0 - 10.8 = 1.2 mm
```

within a nominal 12 mm frame zone behind the recess.

Therefore, the reinforced tie-rod end block must extend structurally into the column/frame overlap region rather than relying on a thin 1.2 mm residual web.

The detailed corner section shall prove that this enlarged end block does not interfere with:

- extreme rack insert bosses,
- rack-screw penetration,
- M5 rod channel,
- T1 attachment screws,
- equipment clearance.

This example still excludes nonzero tip allowance `T` and is **not** a production rod-length instruction.

After final tightening, compression dwell, and any re-seat procedure, exterior clearance must be checked at both ends independently. Do not assume the rod remains centered.

### Final production rule

Do not cut rods from the nominal example.

After prototype parts are printed:

1. assemble the final upper/lower end-block geometry,
2. measure the actual washer-seat spacing,
3. measure actual washer thickness,
4. measure actual nyloc height,
5. define required full-thread protrusion through the nylon locking element,
6. define explicit exterior clearance,
7. measure or bound the non-full-thread tip allowance at each cut/chamfered end,
8. calculate final rod length from the equation above,
9. verify both end clearances after final tightening and compression dwell.

Final cutting tolerance shall be derived from the available clearance margin rather than preassigned.

The purchased 400 mm rods remain appropriate.

## 35. M5 Threaded-Rod Cutting Procedure

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
Current estimate: approximately 355 mm
Final cut length and tolerance: TBD from measured assembled washer-seat spacing and required thread protrusion
```

Do not cut the rods until:

- actual purchased M5 nyloc nut height has been measured,
- top and bottom tie-rod pocket geometry is finalized,
- the final rod-length equation has been evaluated from measured assembled geometry.

---

## 36. Audit Checklist

Before detailed CAD implementation, an independent reviewer should explicitly verify the following.

### Geometry

- 281 × 200 mm external T1 / top-plate envelope is used consistently.
- 355.6 mm added height represents exactly 8U.
- The 12 mm top and bottom frames are contained **within**, not added to, the 355.6 mm height.
- Each front/rear extension rack face remains coplanar with its corresponding stock T1 rack face.
- The 4U splice does not shift the external rack-hole datum.
- Transverse clear opening is proven against the physically measured stock T1 opening.
- Stock-to-extension seam drawing classifies each theoretical rack-hole position as present, provided, obstructed, or intentionally omitted.

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
- Rod-length formula separates required protrusion from exterior pocket clearance.

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
- **Do not lift or carry the populated rack by the relocated factory handles.** The handles are treated as cosmetic/service handles only unless a separate handle load path is designed and proof-tested.

---

## 37. Sources / Evidence

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

- approximately 281 mm external width
- approximately 200 mm depth
- approximately 236.53 mm rail-hole center spacing
- approximately 222.25 mm clear rail opening

These values should be verified against the physical rack before final CAD.

---

## 38. Revision History

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-09-13 | Initial PRD. Defines upper-mounted 8U architecture, T1 handle-hole interface concept, A1-compatible modular structure, measurement requirements, and prototype strategy. |
| 0.2 | 2026-09-13 | Adds verified physical T1 geometry, confirms M4×0.7 top-frame threads, adopts factory lid/handle relocation, eight-bolt lower interface, reinforced 4U+4U columns with M5 tie rods, M4 heat-set rack threads, and purchased hardware BOM. |
| 0.3 | 2026-09-13 | Locks 30×30 mm rack-capable front/rear columns, exact rail coplanarity, 20-25 mm spigot splice, 12 mm frames within the 8U envelope, rear crossbars plus removable diagonal brace, and 355 mm target M5 tie-rod cut length. |
| 0.4 | 2026-09-13 | Records purchased HIPICCO M5×0.8×400 mm stainless tie rods, adds rod cutting/deburring procedure, and adds an independent-audit checklist covering geometry, interfaces, inserts, tie rods, bracing, and safety assumptions. |
| 0.5 | 2026-09-13 | Incorporates independent mechanical audit: defines lid-support datums and usable-8U clearance checks, requires reinforced tie-rod end blocks, makes preload/creep testing mandatory, tightens heat-set boss and screw-depth requirements, adds splice/end-pocket interference sections, makes 355 mm rod length provisional, corrects stale M4/281 mm references, and prohibits lifting a populated rack by relocated handles. |
| 0.6 | 2026-09-13 | Incorporates second audit: corrects tie-rod length equation, adds retained-clamping lateral/eccentric load validation, requires transverse clear-opening proof, clarifies merged boss strips and non-bottoming rack screws, fixes stale M4/BOM/section-numbering issues, and adds a required dimensioned critical corner section before detailed CAD is accepted. |
| 0.6.1 | 2026-09-13 | Audit clarification: rod-length derivation now distinguishes full-thread protrusion from chamfer/incomplete-tip allowance, supports asymmetric end hardware, and requires independent post-tightening clearance checks at both rod ends. |
| 0.6.2 | 2026-09-14 | Records measured 222.5 mm stock clear opening, 28.8 mm top-hole phase and 15.9/15.9 mm spacing, and 7.8 mm actual M5 nyloc height. Limits symmetric inward column projection to 29.25 mm, retires the old 8 mm tie-rod recess assumption, and leaves only the optional hole-3→hole-4 phase confirmation before production rail geometry. |
| 0.6.3 | 2026-09-14 | Incorporates latest audit: labels the 360.8 mm rod case explicitly infeasible, derives a feasible illustrative 334.0 mm seat spacing / 355.2 mm idealized rod example, requires end blocks to extend into column overlap, and adds a mandatory stock-to-extension seam drawing because measured hole phase places theoretical positions below the extension plane. |
| 0.6.4 | 2026-09-14 | Records measured hole-3→hole-4 spacing of approximately 12.7 mm, confirming the conventional 15.9 / 15.9 / 12.7 mm rack-hole pattern for preliminary CAD. R-04 is no longer an open measurement; the seam drawing remains mandatory. |
