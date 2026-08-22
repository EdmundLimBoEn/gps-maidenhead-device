# Hardware design source

SPDX-License-Identifier: CERN-OHL-S-2.0

This directory contains the revision-A *engineering* KiCad source for the
Maidenhead Pocket Locator.  It is deliberately a source-controlled design,
not by itself a claim that an assembled product has been validated: the selected
LCD, patch antenna, cell and enclosure still require physical fit checks. No RF,
power, charger or thermal measurement has been performed on assembled hardware.

`design.yaml` is a review summary of the electrical architecture and constraints;
the component/pin contract is embedded in `generate_kicad.py`. The generator
writes the legacy schematic and cache while preserving the authoritative routed
PCB. Passing `--force-placement` explicitly replaces the PCB with its
deterministic unrouted placement. The source set contains:

* `maidenhead-pocket-locator.sch` — deterministic legacy Eeschema source;
* `maidenhead-pocket-locator.kicad_sch` — the committed modern KiCad source,
  synchronized from the legacy source with KiCad and used for PDF/netlist exports;
* `maidenhead-pocket-locator.kicad_pcb` — the authoritative routed 4-layer,
  81 x 37 mm board with edge connectors, test points and controlled RF/USB
  net classes. The default manufacturing preflight requires zero DRC errors,
  zero unconnected items, filled inner planes, no signal tracks on In1, and
  only the length-bounded `LCD_RS_3V3`, `LOCATE_N`, `QSPI_SCLK`, and
  `QSPI_SD2` crossovers on In2.

The generated board is useful for electrical/mechanical review and routing
iteration. It must not be sent to a fabricator until the
release checklist passes.  `../manufacturing/export.sh` runs the KiCad CLI
exports and DRC when KiCad is installed.

## Regenerate and inspect

```sh
python3 hardware/kicad/generate_kicad.py
# After an intentional electrical edit, open the legacy .sch in the pinned KiCad
# version, save the converted modern .kicad_sch, and run preflight to compare them.
# Only when intentionally restarting layout:
python3 hardware/kicad/generate_kicad.py --force-placement
python3 hardware/manufacturing/preflight.py --source-only
python3 hardware/manufacturing/preflight.py
kicad hardware/kicad/maidenhead-pocket-locator.kicad_pro
```

The source-only command is a diagnostic aid. CI and manufacturing exports use
the strict default command; it must pass before manufacturing exports are
accepted.

The board datum is the lower-left outside corner.  LCD/window centre is
`(40.5, 18.5)`.  The antenna is an enclosure-mounted patch, not a PCB
component; its 50-ohm route ends at J4.  Keep the top-wall patch projection
clear of copper and parts as documented in `../RF_AND_LAYOUT.md`.

The controlled stack is F.Cu signal/power, In1 uninterrupted GND reference,
In2 predominantly 3V3 power distribution, and B.Cu signal/GND. In2 carries only
the under-7 mm LCD RS, under-4 mm LOCATE, and under-6 mm QSPI SCLK/SD2
crossovers allowlisted by preflight. USB and GNSS RF stay on outer copper over
In1; the short QSPI inner runs also reference the uninterrupted In1 plane. Obtain
the fabricator's impedance calculation before release; nominal
trace widths in the source are starting values, not a substitute for a coupon.
Ordinary logic uses 0.15 mm traces and 0.50/0.20 mm through-vias. Dense QSPI
fanout uses 0.10 mm traces and local 0.46/0.20 mm standard through-vias; confirm
the 0.13 mm annular ring with the selected fabricator. The edge rule
is 0.20 mm for the unavoidable short escapes at J1, SW1 and SW2; confirm both
capabilities in the selected board quote.
