# Wyse 5070 Extended mount for DeskPi RackMate T1

Parametric Build123d source. STL is generated, never hand edited.

## Layout

* `params.py`: source of truth (Dell 184x66x184 worst case, T1 212w x 200d, 2U, A1 256 cube)
* `model.py`: Build123d build plus `validate()` and `--export`
* `test_model.py`: offline unit tests, no CAD kernel required

## Measured inputs, no caliper needed

* Ear hole pattern extracted from DeskPi's own 1U blank panel 3MF
  (`Model_7_1U_Blank_Panel`, 254x43x3mm): mounting slots centered 10mm
  from each outer edge, 30mm vertical spacing. We use 5mm holes at slot
  centers for M4 screws + washers. Re-run the mesh analysis in git
  history if DeskPi revises the panel.
* Foot positions are not published by Dell, Printables/Thingiverse files
  are login-walled, and the Etsy reference drawing leaves its foot slots
  undimensioned. The floor is therefore a vent waffle grid: feet catch on
  ribs anywhere, plus airflow and less filament.

## Iterate

```sh
PYTHONPATH=3d-prints python -m unittest wyse5070_extended_t1.test_model -v
PYTHONPATH=3d-prints uv run --with build123d \
  python -m wyse5070_extended_t1.model --export /tmp/wyse5070_t1.stl
```

`wyse5070_extended_t1.stl` is the generated output, committed for
printing. Never edit it, regenerate from `model.py`.

NixOS note: OCP needs system GL/X C libraries. If import fails with
`libGL.so.1: cannot open shared object file`, point `LD_LIBRARY_PATH`
at your store's `gcc-lib`, `libglvnd`, `libx11`, `expat`, `zlib` lib
dirs plus `/run/opengl-driver/lib` (find candidates with `ldd` on the
`OCP*.so` in the uv cache).

## Optional v2 refinement (phone photo, no caliper)

Top-down photo of the device bottom next to a ruler. Foot centers can be
measured in pixels against the 184mm chassis edge and turned into fitted
pockets. Test print v1 first.
