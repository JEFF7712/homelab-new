# Dell Wyse 5070 Extended mount and CAD research

Research date: 2026-09-14

## Device envelope and model distinction

Dell's Extended user guide specifies an upright envelope of 184 mm high, 66 mm wide, and 184 mm deep, with a starting weight of 1.47 kg. Dell's product data sheet gives the same 184 x 66 x 184 mm envelope and distinguishes it from the standard/slim chassis, which is 184 x 35.6 x 184 mm. When laid horizontally, the nominal Extended rack envelope is therefore 184 mm wide, 66 mm high, and 184 mm deep.

Rupan's measured unit is 184 mm wide, 55.9 mm body height, 59.5 mm overall height including feet, and 184 mm deep. The roughly 6.5 mm difference between Dell's nominal 66 mm chassis width and the measured 59.5 mm overall horizontal height should be resolved with the physical fit-test print rather than expanding the cradle to the datasheet dimension. It may reflect the published maximum envelope, orientation features, or measurement convention.

Sources:

- Dell Extended physical specifications: https://www.dell.com/support/manuals/en-us/wyse-5070-thin-client/5070_extd_ug/physical-specifications?guid=guid-5a72233b-732e-462f-997c-e9b983b350e3&lang=en-us
- Dell Extended user-guide PDF: https://dl.dell.com/topicspdf/wyse-5070-thin-client_Users-Guide2_en-us.pdf
- Dell product data sheet mirror, includes both slim and Extended dimensions and supported orientations: https://www.parkytowers.me.uk/thin/wyse/5070/5070data.pdf

## Extended-specific rack mounts found

The strongest comparable design found is Aurora Labs' Extended-specific 1.5U adapter for 10-inch racks. It uses:

- Recessed bottom slots that locate the chassis feet and resist lateral movement
- Side ventilation channels
- Internal gussets spanning the rack height to resist long-term flex
- PETG rather than PLA
- A universal/offset rack-ear hole pattern so the 1.5U body can be positioned against different rack-hole starting points

Source: https://www.etsy.com/listing/4406114905/wyse-5070-extended-15u-rackmount-adapter

The same vendor offers a 2U Extended-specific STL with a seven-keystone patch panel. Its device retention and structure use the same bottom foot-slot alignment, side vents, and internal gussets. The listing advises a test fit because printer dimensional output varies, and recommends supports for foot slots and vents. It is useful as evidence that a 2U Extended adapter is practical, but its downloaded geometry and exact clearances were not publicly inspectable.

Source: https://www.etsy.com/ie/listing/4446793313/wyse-5070-extended-2u-rackmount-adapter

No freely downloadable Extended-specific parametric CAD model with published internal clearances was found in the searched results. Search results predominantly returned standard/slim 5070 rack mounts. Those must not be used as dimensional bases without widening the horizontal chassis clearance from the slim model's nominal 35.6 mm to the Extended unit's measured 59.5 mm overall height.

## Accessory retention reference

Dell's official VESA wall-mount procedure uses a metal receiving bracket: the thin client is inserted into the bracket, then an adapter/cable box and cable cover are installed. This supports the general retention strategy of a guided insertion followed by a separate closure piece rather than relying on a permanently closed printed channel.

Source: https://www.dell.com/support/manuals/en-us/wyse-5070-thin-client/access_setup_5070/installing-the-thin-client-on-the-vesa-wall-mount?guid=guid-29440803-9dc1-457f-b235-b355d517440e&lang=en-us

## Applicable design conclusions

- Dimension the current cradle from the measured 184 x 184 x 59.5 mm unit, not from standard 5070 CAD and not blindly from Dell's 66 mm nominal width.
- Add underside foot pockets using the measured 10 mm left/right, 24.8 mm front, and 9.5 mm rear insets. The pockets should locate the chassis but retain clearance for FDM variation.
- Keep the removable rear retainer. It follows the guided-insertion-plus-closure approach seen in Dell's official accessory system.
- Retain side ventilation and front gussets. Both appear independently in the Extended-specific commercial designs.
- Produce a short fit-test section before the full print. There is no public Extended CAD with verified fit clearances, and the official versus measured vertical envelope differs materially.
- Do not borrow exact vent or port positions from slim 5070 models. The Extended adds the PCIe expansion region and has a distinct rear I/O layout.

## Limitations

The commercial STL listings expose descriptions and rendered product images, not source CAD or exact internal dimensions. Their geometry and clearances were therefore not copied. The search did not establish exact foot length/width, side-vent coordinates, rear connector projections, or the chassis' local taper; those still require measurements or rectified photographs of Rupan's unit.
