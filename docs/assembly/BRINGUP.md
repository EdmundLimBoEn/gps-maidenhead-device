# First-board bring-up

This procedure applies after the pre-order sections of the manufacturing release
checklist and the default manufacturing preflight pass. Its recorded result is an
input to the later release-evidence section; it is not a substitute for schematic
review or an electrical-safe work area.

1. Keep the battery disconnected. Inspect polarity, QFN alignment, connectors,
   antenna lead, and solder bridges.
2. With power absent, verify ground continuity and check each rail for shorts.
3. Apply a current-limited USB source and verify VBUS, charger output, and 3.3 V in
   that order. The 5 V LCD and GNSS rails must remain off in USB-idle mode.
4. Load minimal firmware incrementally: power hold, USB, buttons, switched 5 V LCD
   rail, ADC, then switched GNSS rail. Verify each disabled rail returns off.
5. Validate charger limits and NTC hot/cold inhibition before fitting the cell.
6. Prove internal BOOTSEL recovery before closing the gasketed enclosure.

Stop on unexpected current, heating, rail voltage, reversed polarity, or damaged
cell wiring. Record any rework before deciding whether the remaining boards are safe.
