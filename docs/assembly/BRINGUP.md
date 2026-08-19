# First-board bring-up

1. Keep the battery disconnected. Inspect polarity, QFN alignment, connectors,
   antenna lead, and solder bridges.
2. With power absent, verify ground continuity and check each rail for shorts.
3. Apply a current-limited USB source and verify VBUS, charger output, 3.3 V, and
   5 V LCD rails in that order.
4. Load minimal firmware incrementally: power hold, USB, buttons, LCD, ADC, GNSS.
5. Validate charger limits and NTC hot/cold inhibition before fitting the cell.
6. Prove internal BOOTSEL recovery before closing the gasketed enclosure.

Stop on unexpected current, heating, rail voltage, reversed polarity, or damaged
cell wiring. Record any rework before deciding whether the remaining boards are safe.
