# V1 test evidence index

This file is the release index for **measured** V1 evidence. It starts empty on
purpose: software checks and CAD exports are not evidence that a physical unit
passed the acceptance criteria. Add immutable raw files or dated records below,
then link them from the release tag.

| Gate | Required raw record | Release status |
|---|---|---|
| Software | CI run URL; native/unit test output; RP2040 build hash | Automated locally; immutable release record pending |
| Cold-start GNSS | Ten rows in `cold-start-record.csv`; at least 9 within timeout | Not measured |
| Eight-hour outing | 32 sessions plus reserve row in `outing-record.csv` | Not measured |
| Shutdown current | Three voltages and instrument burden in `power-record.csv` | Not measured |
| Charger / NTC / power path | Rows in `charging-record.csv` | Not measured |
| USB / update / BOOTSEL | Rows in `controls-recovery-record.csv` | Not measured |
| RF / orientation | Face-up, handheld, desk, vehicle, interference comparison | Not measured |
| Mechanical fit | Exact-stack rows in `mechanical-fit-record.csv` | Not measured |
| Environment | Drizzle, sand, drops, cycles, reseals, 40 °C in `environment-record.csv` | Not measured |
| Cost | Saved five-unit carts, shipping/tax/setup total ≤ US$150 | Not quoted |

Do not replace “Not measured” with an assertion. Record failed trials, rework,
and retests alongside passing evidence.
