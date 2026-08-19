# RF, placement, and routing constraints — Revision A

SPDX-License-Identifier: CC-BY-SA-4.0

The GP-02 to patch assembly is the principal reception risk. This document
defines constraints for the design; it does not certify antenna performance.
If the purchased GP-02 requires a different matching topology, its datasheet
supersedes this document and the schematic/PCB must be revised together.

## GNSS path

1. U7 RF pin to J4 is a continuous 50-ohm grounded coplanar waveguide on the
   outer layer. Calculate width, clearance, and via fence pitch from the
   *ordered* JLCPCB stack-up; do not copy a generic 50-ohm width.
2. Do not place a series DC-block or matching component unless required by the
   purchased receiver/patch data. Preserve a footprint land pattern for an
   optional 0402 series component and a shunt-to-ground component only when
   the actual reference circuit permits it.
3. Keep this route as short as practical, with no stubs, neck-downs, vias, or
   90-degree corners. Ground vias flank the line at a pitch no greater than
   one-tenth of the effective wavelength in board material; refine after the
   selected stack-up is known.
4. Keep the u.FL launch and its shell vias continuous with the RF ground. The
   coax may not be sharply folded, trapped under a screw boss, or routed across
   the 5V inductor, USB pair, LCD flex/header, or RP2040 crystal.
5. The 25 x 25 mm patch is mounted ceramic-face upward below the enclosure top
   wall. No battery, LCD PCB, screw, metallic paint, copper, or other conductor
   is allowed directly above it. Its ground-plane requirement is a purchased
   antenna-data-sheet gate, not an assumed rectangle of copper.

## Noise separation and plane strategy

- Use a solid, uninterrupted B.Cu ground plane except for approved RF
  clearances. Route low-speed signals on F.Cu where possible; never slit the
  return path beneath USB D+/D− or the RF line.
- Put U5/L1/C11 together on the side opposite U7/J4. The switch node is the
  smallest possible copper island and is surrounded by a ground return. Do not
  pour copper under the inductor unless its datasheet allows it.
- Keep the RP2040 crystal and its load capacitors adjacent to U1, with no USB,
  PWM, boost, or RF trace below/through the crystal keep-out.
- Put D1 at J1 before the USB pair enters the board. Route D+/D− as a short,
  matched differential pair over continuous ground, avoiding stubs at any
  optional series parts.
- PWM backlight current returns directly to the 5V boost output capacitor,
  not through the GNSS ground region. Verify the effect with satellite tests
  at backlight-off, dim, full, USB-active, and LCD-update conditions.

## Placement and board mechanics

The nominal PCB is 81 x 37 mm inside an approximately 85 x 41 mm front
enclosure. J1 is centred on the left wall; the LCD is rear-mounted at the
window datum; U7/J4 occupy the upper-right RF zone; power conversion occupies
the lower-left/centre away from RF. The final enclosure source controls exact
boss, gasket, window, button, and antenna locations.

Before ordering, import the enclosure datum model and verify these minimum
checks: board-to-wall clearance, USB shell/cap clearance, LCD glass/window
gap, battery pouch and lead bend radius, patch clearance, button travel,
light-pipe alignment, screw-boss keep-outs, and test-pad access with a probe.

## Two-layer release rules

- Board edge, holes, PCB thickness, and copper-to-edge clearance are confirmed
  against the fabricator capability selected for the quote.
- All component footprints are from a reviewed local library or vendor drawing
  and include pin-1/polarity markings. Never fabricate from the placeholder
  outline blocks in the early generated board.
- Assign net classes before routing: RF controlled impedance, USB differential
  pair, battery/charger high current, LCD boost/backlight, and ordinary logic.
- Run ERC and DRC with zero unreviewed errors, inspect Gerbers in an independent
  viewer, and use the fabrication checklist in `manufacturing/`.
