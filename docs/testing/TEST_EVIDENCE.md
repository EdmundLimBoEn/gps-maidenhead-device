# V1 test evidence index

This file is the release index for **measured** V1 evidence. It starts empty on
purpose: software checks and CAD exports are not evidence that a physical unit
passed the acceptance criteria. Add immutable raw files or dated records below,
then link them from the release tag.

| Gate | Required raw record | Release status |
|---|---|---|
| Software | CI run URL; native/unit test output; RP2040 build hash | Pending hardware release |
| Cold-start GNSS | Ten rows in `cold-start-record.csv`; at least 9 within timeout | Not measured |
| Eight-hour outing | 32 sessions plus reserve row in `outing-record.csv` | Not measured |
| Shutdown current | Three voltages and instrument burden in `power-record.csv` | Not measured |
| Charger / NTC / power path | Current, termination, thermal/NTC results | Not measured |
| USB / update / BOOTSEL | Normal and recovery update records | Not measured |
| RF / orientation | Face-up, handheld, desk, vehicle, interference comparison | Not measured |
| Mechanical / environment | Drizzle, sand, drops, cycles, reseals, 40 °C | Not measured |
| Cost | Saved five-unit carts, shipping/tax/setup total ≤ US$150 | Not quoted |

Do not replace “Not measured” with an assertion. Record failed trials, rework,
and retests alongside passing evidence.
