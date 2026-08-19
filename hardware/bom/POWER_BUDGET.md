# Power budget

Populate from selected-part maximums, then replace estimates with measurements.

| State | Rail | Load | Estimated | Measured |
|---|---|---|---:|---:|
| Shutdown | Battery | charger + load switch + protection | TBD | Required: <=10 uA |
| Acquire | 3.3 V | RP2040 + GNSS | TBD | |
| Display | 5 V | LCD logic + full backlight | TBD | |
| Dim | 5 V | LCD logic + dim backlight | TBD | |
| USB idle | VBUS | RP2040, LCD/GNSS off | TBD | |

The one-year reserve check must use the selected cell maker's self-discharge and
aging data in addition to measured electronic shutdown current.
