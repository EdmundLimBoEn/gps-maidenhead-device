# Acceptance test procedures

Every result must identify unit serial, PCB/enclosure/firmware revision, operator,
UTC date, equipment, ambient conditions, raw observations, and pass/fail outcome.
Failed units are not averaged away; record correction and a complete retest.
Use calibrated instruments within their current calibration interval. Attach raw
photos, logs, and instrument captures by content hash; do not put coordinates in
public artifacts.

## Dimensional fit and stack

Measure the PCB, LCD, window, cell dummy, antenna/coax, gasket, boots, connector,
and printed parts before applying power. Record worst-case clearances and compare
all connector/button/mount centers with `enclosure/INTERFACES.md`. Reject forced
compression, glass/PCB bending, cell pressure, pinched wires, coax below its stated
bend radius, blocked seals, or a total depth above 35 mm. Repeat after ten closures.

## Cold-start GNSS

Fully remove GNSS backup power for the receiver supplier's specified discharge
period. Place the assembled unit face-up at the same open-sky site for ten trials,
separated sufficiently to remain true cold starts. Start timing at initial LOCATE
button-down. Pass when at least 9 of 10 trials display a valid independently checked
grid within the configured 120-second timeout. Record satellites, fix quality, time,
orientation, and weather without retaining coordinates in released diagnostics.

## Shutdown current and one-year reserve

At 25 °C, insert a calibrated low-burden ammeter between cell and product. Measure
after hard shutdown at 4.2 V, nominal 3.7 V, and the released low-voltage threshold,
allowing transients to
settle. Pass only when every electronics measurement is at most 10 µA. Calculate
one-year remaining capacity from the worst measurement plus the selected cell
maker's self-discharge and aging limits; the conservative remainder must power one
measured full check session.

## Outing endurance

Use factory brightness and timers. Over eight hours, run four complete two-minute
checks per hour at evenly spaced intervals, 32 total. After the eighth hour, run one
additional complete reserve check. Record battery voltage/ADC before, periodically,
and after without recharging.

## Charging, NTC, and power path

With a protected fixture, verify input current limit, charge current, termination,
charge LED, operation while charging, and permitted absent-cell behavior. Simulate
the supplier-defined hot and cold NTC resistances without heating or freezing a
live pouch; charge current must stop. Repeat at 40 °C ambient and verify the actual
cell-adjacent sensor inhibits charging before the cell limit.

## RF interference and orientation

At one fixed site compare time-to-fix and signal diagnostics with LCD/boost off,
full brightness, dim brightness, USB active, and LCD updates. Repeat face-up,
handheld, desk-angle, and vehicle-dashboard orientations. A material degradation
triggers placement, grounding, switching-frequency, or filtering review before any
receiver substitution.

## Controls, recovery, and configuration

Exercise 100 ms and 500 ms taps, bounce, 1.00 s accepted holds within the documented
timing tolerance, stuck inputs, simultaneous
holds, and 1,000 mechanical cycles per button on a sacrificial enclosure. Interrupt
configuration writes at every two-slot phase and firmware updates before copy,
during copy, and before reconnect. Prove internal BOOTSEL recovery with application
flash invalid and no debugger.

## Environmental and mechanical

- Record print material, slicer/settings, gasket/adhesive lot, fastener torque or
  hard-stop confirmation, and pre-test mass. Inspect all internals and place dry
  absorbent indicator paper near every seam.
- With the USB plug fitted, spray drizzle from multiple directions for ten minutes.
  Dry the exterior before opening; pass only with no visible ingress.
- Expose seams/buttons/cap to dry beach-like sand, brush clean, actuate controls,
  then open and inspect for grains at electronics.
- Open/reseal the battery compartment ten times and repeat button/seal inspection.
- Drop from 1.0 m onto dry short grass over firm soil once on each broad face and
  once on each enclosure edge/corner selected in the test record; never onto people.
- Soak at 40 ±2 °C for two hours unpowered, then operate a complete check and charge
  test while monitoring the cell-adjacent sensor. Inspect enclosure shape, LCD, GNSS, cell temperature, and
  charger inhibition. Do not perform immersion testing or infer an IP rating.
