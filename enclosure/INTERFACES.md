# Mechanical interface contract

This is the release-blocking datum contract between PCB and enclosure source. It
records required coordinates without claiming that the current engineering PCB,
footprints, or purchased parts satisfy them.

## Datum and envelope

- Enclosure XY origin: lower-left corner of the 88 × 44 mm front profile, viewed
  from the display side. Z=0 is the outside face of the clear window.
- PCB outline: 81 × 37 × 1.6 mm, centered at enclosure `(3.5, 3.5)` in XY.
- Nominal outer-edge margin is 3.5 mm and shell-to-PCB interior clearance is 2 mm
  on every side. The 82 × 38 mm flange opening leaves 0.5 mm insertion clearance
  per side. These values must be revised
  from measured print and board tolerances; it is not an interference-fit spec.
- Maximum assembled outside depth: 35 mm; source target: 34.5 mm.
- The nominal Winstar WH1602B outline is 80 × 36 × 13.5 mm with 75 × 31 mm
  mounting-hole pitch and 66 × 16 mm viewing area. Centering it maps those holes
  to the four enclosure centers below. Verify the exact ordered suffix against
  the [manufacturer drawing](https://www.winstar.com.tw/uploads/files/cce99cb4f21c2bd9362dfadcc10c188a.pdf).

## Frozen XY centers for the routing datum

| Interface | PCB coordinate (mm) | Enclosure coordinate (mm) | Gate |
|---|---:|---:|---|
| USB-C mating-face center | left edge `(0, 14)` | left wall `(0, 17.5)` | Exact connector body/plug clearance still gated |
| LOCATE actuator tip | right edge `(81, 10)` | right wall `(88, 13.5)` | TL1014BF160QG drawing/boot stack still gated |
| OFF actuator tip | right edge `(81, 27)` | right wall `(88, 30.5)` | 17 mm center spacing |
| Mount 1, Ø2.7 NPTH | `(3, 3)` | `(6.5, 6.5)` | M2.5 hardware |
| Mount 2, Ø2.7 NPTH | `(78, 3)` | `(81.5, 6.5)` | M2.5 hardware |
| Mount 3, Ø2.7 NPTH | `(3, 34)` | `(6.5, 37.5)` | M2.5 hardware |
| Mount 4, Ø2.7 NPTH | `(78, 34)` | `(81.5, 37.5)` | M2.5 hardware |

The board-space coordinates are frozen so PCB routing cannot drift. Enclosure
coordinates are their (+3.5,+3.5) translation; the shell grew from the original
85 × 41 concept because that envelope left no material for a real gasket groove.
The USB footprint origin, connector body, switch footprint bodies, and all Z
coordinates must still come from exact drawings and the shared stack. Do not treat
the table as permission to order. The exact Winstar LCD,
USB receptacle, side switches, window, gasket, cell, antenna/coax, and fasteners
must be overlaid from manufacturer drawings and then checked with physical samples.

## Known unresolved stack constraints

- The 80 × 36 mm LCD nearly fills the front profile. Its mounting holes, header,
  bezel depth, glass keep-out, and enclosure fasteners must use one verified model.
- A 25 × 25 × 4 mm patch cannot be described merely as “under the top wall.” Its
  ceramic face direction and a metal/copper-free volume must be explicit in CAD.
- The battery, LCD body, populated PCB, antenna, coax bend, and wire/connector
  service loops need a single Z stack with tolerances. Nominal bounding boxes alone
  are insufficient because their allowed volumes currently overlap.
- The source has battery positioning rails but no frozen positive vertical/end
  retainer. Add a removable, non-compressing retainer only after the exact protected
  cell and PCB Z stack are measured; the pouch must never be used as a spring.
- USB and button openings must follow the final edge-mounted footprints. Moving
  openings independently from the PCB is prohibited after the datum is frozen.
