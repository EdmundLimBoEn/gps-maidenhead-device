# Hardware design source

SPDX-License-Identifier: CERN-OHL-S-2.0

This directory contains the revision-A *engineering* KiCad source for the
Maidenhead Pocket Locator.  It is deliberately a source-controlled design,
not a claim that the board is ready to order: the selected LCD, patch antenna,
cell and enclosure have not yet been physically checked, and the current routing
draft has known DRC failures. No RF, power, charger or thermal measurement has
been performed on hardware.

`design.yaml` is the reviewable electrical source of truth.  It records every
net, part, and connector pin without depending on local KiCad libraries.
`generate_kicad.py` produces:

* `maidenhead-pocket-locator.sch` — legacy Eeschema source that KiCad 7/8/9
  imports and migrates to `.kicad_sch` on first open;
* `maidenhead-pocket-locator.kicad_pcb` — a connected 2-layer, 81 x 37 mm
  engineering routing draft with edge connectors, test points and an RF zone.
  It exports in KiCad 7, but it is intentionally blocked from manufacturing
  until zero unreviewed DRC errors and zero unconnected items are recorded.

The generated board is useful for electrical/mechanical review and routing
iteration. It must not be sent to a fabricator until the
release checklist passes.  `../manufacturing/export.sh` runs the KiCad CLI
exports and DRC when KiCad is installed.

## Regenerate and inspect

```sh
python3 hardware/kicad/generate_kicad.py
python3 hardware/manufacturing/preflight.py --source-only
python3 hardware/manufacturing/preflight.py
kicad hardware/kicad/maidenhead-pocket-locator.kicad_pro
```

The source-only command is suitable for CI and must report the remaining DRC,
unconnected-item and provisional-footprint gates as pending. The default command
is deliberately strict and must pass before manufacturing exports are accepted.

The board datum is the lower-left outside corner.  LCD/window centre is
`(40.5, 18.5)`.  The antenna is an enclosure-mounted patch, not a PCB
component; its 50-ohm route ends at J4.  Keep the top-wall patch projection
clear of copper and parts as documented in `../RF_AND_LAYOUT.md`.
