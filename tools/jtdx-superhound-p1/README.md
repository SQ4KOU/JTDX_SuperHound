# JTDX SuperHound P1 — SQ4KOU

This branch moves the experimental JTDX SuperHound P1 work from the local Windows machine to GitHub Actions.

## P1 scope

- keep native JTDX FT8/Hound decoding unchanged,
- add a separate RX bridge for SuperFox periods,
- build the official WSJT-X `sfrx` target separately,
- do **not** copy SuperFox/QPC source code into JTDX,
- build and test on a clean GitHub Windows runner,
- publish logs, the generated JTDX patch and any produced `.exe` files as Actions artifacts.

## CI

Workflow: `.github/workflows/jtdx-superhound-p1.yml`

Branch: `jtdx-superhound-p1-ci`

The workflow clones current JTDX from SourceForge, applies `scripts/patch_jtdx.py`, builds the official WSJT-X `sfrx` target, then attempts a complete JTDX Windows build under MSYS2/UCRT64.

This branch is isolated from the normal Thetis branches and is used only as a CI/build harness for the JTDX experiment.
