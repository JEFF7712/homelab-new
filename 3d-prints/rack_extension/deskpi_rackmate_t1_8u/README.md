# DeskPi RackMate T1 8U Extension (preliminary CAD)

Parametric Build123d source per PRD `deskpi_rackmate_t1_8u_extension_prd_v0.6.4.md`.
Preliminary only: solids exist for fit checks, but the audit gates below
block any production claim.

## Layout

* `params.py`: source of truth (measured T1 values + Path A stack math)
* `model.py`: Build123d solids plus `--export` and `--audit`
* `test_model.py`: offline unit tests, no CAD kernel required

## Phase 2 corner prototype

`phase2_corner_mount.stl` contains the accepted T1 interface, reinforced lower
end block, captive M5 hardware pocket, and a keyed upright spigot. Both M4
attachment screws remain accessible from above. `phase2_lower_upright.stl`
slides over the mount spigot and provides the lower half of the 4U seam.
`phase2_upper_upright.stl` contains the mating seam, upper 4U upright, and
reinforced upper end block. These are fit-test parts, not production approval.

Print the mount first and verify both M4 screws remain accessible. Then print
the lower upright vertically from its mount-socket end. Print the upper upright
vertically from its seam end only after both lower joints pass inspection.

## Iterate

```sh
PYTHONPATH=3d-prints/rack_extension python -m unittest deskpi_rackmate_t1_8u.test_model -v
LD_LIBRARY_PATH=<nix GL libs> uv run --python 3.13 --with build123d \
  python -m deskpi_rackmate_t1_8u.model --export-dir /tmp/opencode/rack_extension --audit
```

NixOS note: OCP needs system GL/X C libraries. Resolve them from the
pinned nixpkgs (`libglvnd`, `libx11`, `gcc-lib`, `zlib`, `expat`) and
export via `LD_LIBRARY_PATH`; see the adjacent `wyse5070_extended_t1`
README for the same pattern.

## Blocking audit gates (all open)

G1 seam drawing, G2 corner end-block section, G3 interference sections,
G4 creep/retained-clamp validation, G5 final rod length from measured
seats, G6 anti-tip hardware, G7 rail/handle M-01..M-12 measurements.
`model.audit_gates()` is the machine-readable list.
