# Power budget

SPDX-License-Identifier: CC-BY-SA-4.0

This worksheet sizes Revision A; it is not a measurement or battery-life
claim. The exact LCD, protected cell, GP-02 lot and board leakage remain
physical release gates.

## Rail architecture

`BQ24074.OUT` is the only source of `SYS_RAW`. The protected cell connects only
to `BQ24074.BAT`; Q1 is a signal MOSFET that can source the TPS63802 enable pin,
not a load-path bypass. TPS63802 generates regulated 3.3 V across the useful
1S-cell range. USB VBUS diode-ORs into its enable so CDC remains available,
while GPIO5 and GPIO18 leave the true-disconnect LCD boost and GNSS load switch
off in USB idle.

## Battery-off leakage budget (USB absent)

| BAT-connected item | Conservative allocation (uA) | Verification gate |
|---|---:|---|
| BQ24074 BAT/OUT power-path standby | 2.0 | Replace with applicable datasheet maximum and measure through BAT |
| TPS63802 disabled VIN leakage | 0.6 | TI maximum through 85 °C; measure at 3.0/3.7/4.2 V |
| Q1 start PMOS and Q2 gate network | 1.2 | Include D2/D3/D4 and contamination over temperature |
| Q4/Q5 disabled battery-divider switch | 1.2 | Confirm BAT is isolated from divider and unpowered ADC |
| Remaining BAT-referred leakage / board margin | 2.0 | Measure assembled, cleaned board |
| **Predicted allocation** | **7.0** | **Not a pass result; every unit must measure ≤10 uA at 25 °C** |

The cell protection circuit, cell self-discharge and ageing are outside the
electronics-only 10 µA criterion but remain part of the one-year reserve
calculation. At 7 µA, electronics alone consume about 61.3 mAh/year. No storage
claim may use this arithmetic without worst-case cell-maker data and a measured
reserve session.

## Active-session worksheet

Sizing assumptions: 3.7 V cell, TPS63802 90% efficiency at the relevant load,
TPS61023 83%, GP-02 45 mA at 3.3 V, RP2040/flash 35 mA at 3.3 V, LCD logic
2 mA and representative backlight 25 mA at 5 V.

| Mode | Estimated battery current | Required measurement |
|---|---:|---|
| Acquiring, full LCD | `(3.3*(45+35)/0.90 + 5*(2+25)/0.83)/3.7` = 124 mA | True cold acquisition, full backlight |
| Display, full LCD | `(3.3*35/0.90 + 5*27/0.83)/3.7` = 79 mA | Valid-fix display |
| Display, dim 20% | `(3.3*35/0.90 + 5*7/0.83)/3.7` = 46 mA | PWM average and peak |
| USB idle | 0 mA battery-discharge target | Verify charger/power-path direction with cell present and absent |

Thirty-two 120-second worst-case acquisition sessions consume roughly 132 mAh
before cell ageing, cold-start variation and low-voltage converter loss. Final
capacity and charge current remain blocked on measured loads and the selected
cell datasheet.

## Measurement method

1. With USB absent, measure BAT current after hard shutdown at 4.2, 3.7 and
   3.0 V after transients settle.
2. Record active current for acquire, full/dim display, tracking, USB idle and
   charging. Capture PWM current with adequate bandwidth.
3. Safely simulate the frozen NTC hot/cold limits and verify charge inhibition,
   termination and power-path operation.
4. Record exact BOM revisions, firmware, ambient temperature and instruments in
   `docs/testing/`; never promote calculated values to acceptance evidence.
