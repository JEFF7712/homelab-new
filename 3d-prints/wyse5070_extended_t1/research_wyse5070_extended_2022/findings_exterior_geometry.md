# Dell Wyse 5070 Extended exterior geometry findings

## Scope and identification

- Dell identifies the Extended chassis as regulatory model **N12D**, regulatory
  type **N12D001**. The guide itself is dated October 2018, so "2022" is likely
  the production or acquisition year, not a distinct exterior revision.
- Independent hardware documentation distinguishes N12D Extended from the N11D
  standard chassis. This matters because photographs and models labeled only
  "Wyse 5070" are often the narrower standard unit.

Sources:

- [Dell Wyse 5070 Extended Thin Client User Guide](https://dl.dell.com/topicspdf/wyse-5070-thin-client_Users-Guide2_en-us.pdf)
- [ParkyTowers Wyse 5070 hardware description](https://www.parkytowers.me.uk/thin/wyse/5070/)

## Ventilation geometry

- The lead industrial designer states that the production 5070 requires
  ventilation on **three surfaces: top, left side, and bottom** when standing in
  Dell's intended vertical orientation. This is the clearest source found for
  the actual airflow-sensitive faces.
- Dell's official setup guide says the unit must be mounted vertically. The
  designer explains that the vertical stand elevates the chassis to preserve
  bottom airflow. A horizontal rack cradle therefore departs from Dell's
  validated orientation and should leave large open areas at the original top,
  left-side, and bottom vent fields.
- The same designer shows that Dell's own wide-compatible mounts use hole
  patterns corresponding to the chassis ventilation. He also notes that an
  early mount with more open area lacked structural integrity. This supports a
  ribbed or perimeter-supported opening pattern rather than removing an entire
  wall.
- StorageReview's Extended unit description confirms that the side, top, and
  bottom plastic surfaces share the diamond-weave treatment. That treatment is
  not proof that every patterned area is open ventilation, so CAD cutouts should
  not be aligned from the decorative texture alone.

Sources and imagery:

- [Sachin Mistry, lead designer, Dell Wyse 5070](https://www.sachinmistry.com/dellwyse5070)
- [Designer cooling illustration](https://images.squarespace-cdn.com/content/v1/5533b452e4b02842e06699b8/7f9cc677-1e94-48ce-aca5-1c10abdc0d6e/San%2BBernarndino_cooling.png)
- [Designer mount and ventilation illustration](https://images.squarespace-cdn.com/content/v1/5533b452e4b02842e06699b8/f0d48e57-3a4e-44ff-b327-163e0f0d68d8/San%2BBernarndino_Mounts%2B06062026.png)
- [StorageReview Extended chassis review](https://www.storagereview.com/review/wyse-5070-client-review)

## Front, rear, and asymmetry

- The front is a deep, block-like plastic bezel rather than a thin flat sheet.
  The designer explicitly says its depth was increased during development. A
  rack stop should contact a robust bezel corner or the main chassis face, not
  press on the port field.
- The official chassis overview shows a strongly asymmetric Extended rear. The
  motherboard I/O occupies one region, while the expansion-card area adds a
  half-height PCIe opening and may contain GPU mini-DisplayPorts or other card
  connectors. Optional RJ45, SFP, or VGA modules and wireless antennas can also
  alter rear clearance.
- Do not use a rear crossbar that spans the connector field at connector height.
  Keep the rear retainer at chassis-edge contact points and allow clearance for
  the PCIe bracket, cables, power-cable hook, optional antennas, and the chassis
  cover thumbscrew.
- The official service procedure says the chassis cover slides toward the front
  before lifting away. Any top capture tabs that overlap that cover will require
  removal of the Wyse from the rack before servicing, unless the mount provides
  deliberate release clearance.

Direct exterior photographs of an Extended review sample:

- [StorageReview front three-quarter photograph](https://www.storagereview.com/wp-content/uploads/2018/10/StorageReview-Dell-Wyse-5070.jpg)
- [StorageReview rear photograph](https://www.storagereview.com/wp-content/uploads/2018/10/StorageReview-Dell-Wyse-5070-Back.jpg)
- [Dell official chassis overview and service imagery](https://dl.dell.com/topicspdf/wyse-5070-thin-client_Users-Guide2_en-us.pdf)

## Bottom and feet

- StorageReview reports **three stand-mounting slots on the bottom**. The
  designer describes a keyhole fitting used by both chassis widths. These slots
  and the corresponding patterned/vented field should remain unobstructed where
  practical.
- No trustworthy dimensioned photograph was found for foot size or precise vent
  boundaries. The user's physical foot insets and height measurements should
  remain authoritative. The web evidence supports preserving an airflow gap,
  but does not justify inventing exact foot or vent coordinates.

## Dimensions relevant to interpreting photographs

- Published Extended dimensions are approximately **184 mm high x 56 mm wide x
  184 mm deep**. This agrees closely with the user's 184 x 55.9 x 184 mm body
  measurement and 59.5 mm overall height including feet.
- Images of the standard chassis must not be scaled to infer the Extended width.
  The two variants share the 184 mm height and depth but not the width.

Source:

- [StorageReview specifications and Extended review](https://www.storagereview.com/review/wyse-5070-client-review)

## CAD implications

1. Treat the user's measured 184 x 55.9 x 184 mm body as the fit source of
   truth. Published nominal dimensions corroborate it.
2. Preserve generous openings beneath the original bottom and alongside the
   original left-side vent field. Do not infer precise cutout registration from
   the diamond texture.
3. Ensure feet or small standoffs maintain a real air gap when the unit is laid
   horizontally.
4. Make the rear retention geometry asymmetric or edge-only so it cannot foul a
   PCIe card bracket or optional rear connectors.
5. Keep front stops small and confined to bezel corners, with the front face
   flush or slightly recessed as the user requested.
6. Consider serviceability explicitly because Dell's cover releases by sliding
   forward.

## Evidence limitations

- No exterior revision specific to calendar year 2022 was found.
- No source provided scale-controlled side or bottom photographs suitable for
  deriving exact vent boundaries or foot dimensions.
- Product photos establish qualitative shape and asymmetry, not sub-millimeter
  CAD coordinates. A square-on photograph of the user's exact unit with a ruler
  in-plane is still needed for chassis-specific vent alignment.
