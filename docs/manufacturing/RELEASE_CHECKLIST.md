# Manufacturing release checklist

## Source and electrical

- [ ] Exact BOM manufacturer part numbers and approved substitutes frozen
- [ ] Manufacturer reference circuits checked component by component
- [ ] LCD backlight current and resistor configuration verified on sample
- [ ] Cell capacity/current/temperature limits match charger programming
- [ ] Power-path, VBUS enable, hard latch, and reverse-polarity behavior reviewed
- [ ] GP-02 RF trace recomputed from the fabricator's ordered stack-up
- [ ] ERC and DRC clean with intentional exceptions documented
- [ ] All footprints checked against physical drawings and pin-1 orientation

## Mechanical

- [ ] PCB, LCD, window, buttons, USB, antenna, cell, gasket share one datum model
- [ ] 85 × 41 × ≤35 mm envelope confirmed from exported geometry
- [ ] Coax and battery leads meet bend/strain clearance without forced compression
- [ ] Unpopulated dimensional fit-check printed and measured
- [ ] One complete enclosure printed before committing the remaining four

## Manufacturing artifacts

- [ ] Schematic PDF, Gerbers, drill, IPC/netlist, BOM, and pick-and-place regenerated
- [ ] Gerbers inspected in an independent viewer
- [ ] Assembly drawing shows DNP, polarity, and hand-installed parts
- [ ] Test points and BOOTSEL/RUN recovery controls are labelled and accessible
- [ ] Five-unit carts include tax, shipping, setup, minimums, and consumables
- [ ] Complete five-unit landed total is ≤US$150 before ordering

## Release evidence

- [ ] First-board bring-up completed without unsafe rework
- [ ] Full acceptance procedure passed on the released revision
- [ ] Firmware/configurator releases are reproducible from the tagged commit
- [ ] LiPo, heat, water-resistance, and non-emergency warnings are prominent
- [ ] Released artifacts contain no coordinates, secrets, or private supplier data
- [ ] [Evidence index](../testing/TEST_EVIDENCE.md) contains raw measured results
- [ ] [Order package](ORDER_PACKAGE.md) is complete and signed off
