# Manufacturing artifact workflow

SPDX-License-Identifier: CC-BY-SA-4.0

The KiCad source is the controlled artifact. Generated files in
`review-output/` are deliberately ignored because they must be regenerated
from the reviewed commit and the selected fabricator settings.

```sh
python3 hardware/manufacturing/preflight.py --source-only
python3 hardware/manufacturing/preflight.py
hardware/manufacturing/export.sh
```

`--source-only` is the CI check: it validates source, critical nets, BOM and
outline, while reporting DRC/unconnected/provisional-footprint work as pending.
It is not permission to order. The default preflight is the manufacturing gate
and fails until the KiCad DRC, routing and exact vendor footprints pass.

`export.sh` runs the default manufacturing gate, then proves that the PCB parses
in the installed KiCad version by
exporting SVG, Gerbers, drill, and placement review files. KiCad 7.0's CLI
does not expose a DRC command, so preflight uses its Python `pcbnew` binding.
Archive the final DRC/ERC reports with release evidence. A clean export alone is
not a fabrication approval.
