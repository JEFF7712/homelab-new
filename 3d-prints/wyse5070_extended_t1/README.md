# Wyse 5070 Extended mount for DeskPi RackMate T1

Parametric Build123d source. The design adapts the open-frame architecture of
`../dell-wyse-5070-1u-10-inch-rack.stl` to the 66 mm-thick Extended chassis.
The STL is generated, never hand edited.

## Layout

* `params.py`: source of truth (measured 184x59.5x184 overall, T1 212w x
  200d, 2U, A1 256 cube)
* `model.py`: Build123d build plus `validate()` and `--export`
* `test_model.py`: offline unit tests, no CAD kernel required

## Measured inputs, no caliper needed

* Ear hole pattern extracted from DeskPi's own 1U blank panel 3MF
  (`Model_7_1U_Blank_Panel`, 254x43x3mm): mounting slots centered 10mm
  from each outer edge, 30mm vertical spacing. We use 5mm holes at slot
  centers for M4 screws + washers. Re-run the mesh analysis in git
  history if DeskPi revises the panel.
* The standard-Wyse STL establishes the 254x44x190.5 mm rack envelope, open
  underside, vertical ear slots, and slide-in rail layout. It cannot simply be
  scaled because the Extended chassis is substantially thicker. This design
  uses 2U to preserve airflow and robust retention around the measured unit.
* The physical 2022 N12D unit measures 55.9 mm without feet and 59.5 mm with
  feet. Those measurements control the fit; Dell's published 66 mm value is
  retained only as a nominal upright envelope reference.
* Four measured 5.8x20 mm feet sit in 1.6 mm-deep locating pockets. The feet
  begin 10 mm from each side and 24.8 mm from the front, with 128.7 mm row
  spacing. That geometry implies a 10.5 mm rear inset, within 1 mm of the
  separately measured 9.5 mm rear inset; 0.4 mm pocket clearance absorbs the
  discrepancy without closing the central bottom vent field.
* The Extended unit rests on two 15 mm edge rails instead of a solid floor.
  This avoids depending on unpublished foot locations and leaves the underside
  open for airflow. C-channel side rails, a removable rear retainer, and two
  tie locations prevent movement without blocking the front ports.
* Eight rounded windows in each side wall reduce material and expose the chassis
  vents. The intermediate web is 2.6 mm thick, while the upper and lower rails,
  front and rear columns, and 8.4 mm intermediate ribs retain the load path.
* Three short capture tabs replace each continuous top lip. A separate rear
  retainer installs after the Wyse slides into the cradle and is held by two M3
  screws into heat-set inserts in the retainer ends. Its raised contact pads
  touch only the chassis corners, leaving the asymmetric rear I/O area open.
* 32 mm triangular shelf gussets run flat beneath the support rails and transfer
  their cantilevered load into the lower front flange.
* Four 2x8 mm corner stops set the front bezel 1.2 mm behind the rack face
  without entering the port field. Two cantilever tabs per side provide 0.2 mm
  nominal preload and flex into dedicated relief windows to prevent rattling.
* The seated-height calculation accounts for the feet dropping 1.6 mm into
  their pockets, leaving 0.8 mm above the chassis. Capture tabs are 6 mm wide
  and 4 mm thick, backed by a 10 mm upper side rail and a full-width 4 mm front
  top brace.

## Iterate

```sh
PYTHONPATH=3d-prints python -m unittest wyse5070_extended_t1.test_model -v
PYTHONPATH=3d-prints uv run --with build123d \
  python -m wyse5070_extended_t1.model \
    --export /tmp/wyse5070_t1.stl \
    --export-retainer /tmp/wyse5070_t1_retainer.stl \
    --export-fit-test /tmp/wyse5070_t1_fit_test.stl
```

`wyse5070_extended_t1.stl` and `wyse5070_extended_t1_retainer.stl` are generated
outputs committed for printing. Never edit them, regenerate from `model.py`.

`wyse5070_extended_t1_fit_test.stl` is a 32 mm-deep two-rail gauge. It includes
the four bezel stops, leading portions of the front foot pockets, and the first
10 mm of the reinforced capture tabs. A small lower connector preserves the
true cradle width while the rack ears and unused center are omitted. Print it
with the front face on the build plate, then slide only the front of the Wyse
into it. It is a fit coupon, not a load-bearing rack mount.

NixOS note: OCP needs system GL/X C libraries. If import fails with
`libGL.so.1: cannot open shared object file`, point `LD_LIBRARY_PATH`
at your store's `gcc-lib`, `libglvnd`, `libx11`, `expat`, `zlib` lib
dirs plus `/run/opengl-driver/lib` (find candidates with `ldd` on the
`OCP*.so` in the uv cache).

## Fit refinement

The model uses the measured 184x59.5x184 mm envelope with 0.6 mm side and 0.8 mm
top clearance. Before a full print, print a 15 mm-deep rear cross-section
and confirm that the chassis slides between the walls and below the capture
lips. Adjust only `SIDE_CLEARANCE_MM` and `TOP_CLEARANCE_MM` if needed.
