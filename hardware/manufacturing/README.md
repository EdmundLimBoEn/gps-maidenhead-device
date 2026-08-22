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

`--source-only` is a diagnostic check: it validates source, critical nets, BOM
and outline while reporting any DRC/unconnected work as pending. It is not
permission to order. CI and `export.sh` use the default manufacturing gate,
which fails until KiCad DRC, routing, and plane-fill checks pass. Exact ordered-part
drawings, physical overlays, and the three provisional external selections remain
explicit manual checklist gates.

`export.sh` runs the default manufacturing gate, archives its complete DRC,
then atomically replaces the review directory with SVG, top assembly PDF, Gerbers,
drill, IPC-D-356, a millimetre/SMD-only placement file, schematic PDF/netlist,
searchable HTML BOM and BOM CSVs. The BOM status column remains authoritative for
assembly-provider, hand-install, provisional, and do-not-fit decisions; the placement
file alone is not an assembly instruction. `assembly-bom.csv` and `placement.csv`
have matched one-reference-per-row contents; the CPL uses JLC's standard Designator,
Mid X, Mid Y, Layer, and Rotation headers. Supplier/LCSC part selections remain a
manual release gate until the exact quote is frozen.
KiCad 7.0's CLI does not expose schematic ERC, so archive the signed-off GUI ERC
report with release evidence. A clean export alone is not a fabrication approval.
