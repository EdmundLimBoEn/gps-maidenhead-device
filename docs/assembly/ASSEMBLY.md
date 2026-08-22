# Assembly guide

**Engineering draft — do not use for a production build until every item in the
[manufacturing release checklist](../manufacturing/RELEASE_CHECKLIST.md) is signed.**
The sequence below does not establish that the current PCB and enclosure fit.

## Safety

Use only the protected, keyed 1-cell LiPo listed in the released BOM. Never bend,
puncture, clamp, solder directly to, or reverse-connect a pouch cell. Stop if the
cell is swollen, damaged, hot, or below its supplier's safe voltage. This device
is not an emergency locator, navigation instrument, or immersion-rated product.

## Preparation

1. Complete the first-board electrical procedure in [BRINGUP.md](BRINGUP.md).
2. Confirm the PCB revision, firmware revision, enclosure revision, and BOM match.
3. Dry-fit the LCD, PCBA, cell dummy, patch antenna, coax, window, gasket, buttons,
   USB plug, and fasteners without the live cell.
4. Clean the window land and polycarbonate with materials compatible with both.

## Mechanical assembly

1. Install heat-set inserts using a temperature-controlled tool and a depth stop.
   Let the parts cool before checking screw alignment.
2. Bond the 71 × 25 × 1 mm polycarbonate window into the 1.1 mm lid recess with a
   continuous closed-cell adhesive seal. Leave no seam at the corners.
3. Fit the LCD behind the window without loading the display glass. Secure its PCB
   only with the released supports/fasteners and connect the keyed header.
4. Fit the two elastomer button boots. Verify their outer flanges remain flat and
   each tactile switch returns freely before installing electronics.
5. Mount the passive patch ceramic face toward the top wall. Keep the specified
   copper/metal/battery exclusion volume and avoid a sharp bend at either coax end.
6. Install the PCBA and route the coax away from the 5 V inductor, USB pair, LCD
   edge, and screw bosses. Seat the u.FL plug vertically with a plastic tool.
7. Place the protected cell between the retention rails with no foam pressure on
   the pouch. Route its lead without pinch points and connect the keyed plug last.
8. Fit the released nominal 1 mm silicone cord dry and continuous in its 0.7 mm
   groove. Do not stretch it; place the bonded splice only as the seal procedure specifies.
9. Close the lid and tighten screws in a diagonal sequence until the hard stops
   meet. Do not use screw torque to crush the gasket further.
10. Fit and tether the USB-C plug, then confirm the charging light pipe is visible.

Reject the assembly if any part requires force, bends the PCB/LCD, presses the
cell, violates the coax bend radius, prevents a seal from lying flat, or changes
button return. Do not “make it fit” by thinning a safety wall or omitting a gasket.

## Final functional check

- Confirm USB data, charging, configuration read-back, and BOOTSEL recovery.
- Confirm short button taps do not latch power and both one-second holds work.
- Acquire a current outdoor fix and compare the locator with an independent tool.
- Confirm the backlight dims and the unit shuts down at configured deadlines.
- Record unit serial, firmware, profile CRC, battery lot, and test result without
  recording the operator's coordinates.
