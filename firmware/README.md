# Pocket Locator firmware

The firmware uses one C++ core for native tests and the RP2040 UF2. Hardware
code is deliberately isolated under `src/{board,display,gnss,storage,device}`;
the Maidenhead, NMEA, session, layout, configuration validation, and protocol
modules remain host-testable.

## Native tests

```sh
cmake -S firmware -B build/firmware-host
cmake --build build/firmware-host
ctest --test-dir build/firmware-host --output-on-failure
```

## Build a UF2

Install the Raspberry Pi Pico SDK, then either export `PICO_SDK_PATH` or pass
it to CMake.

```sh
cmake -S firmware -B build/rp2040 \
  -DPOCKET_LOCATOR_BUILD_HOST_TESTS=OFF \
  -DPOCKET_LOCATOR_BUILD_RP2040=ON \
  -DPICO_SDK_PATH=/path/to/pico-sdk
cmake --build build/rp2040
```

The resulting `pocket_locator_rp2040.uf2` is an RP2040 ROM-BOOTSEL image.
The application command `reboot_to_bootloader` uses `reset_usb_boot`; the
internal physical BOOTSEL switch remains the recovery mechanism if firmware
does not start.

## Rev-A electrical contract

`include/pocket_locator/board/pins.hpp` is the single source of MCU pin
assignments. The current pin map is deliberately named, not inferred from a
schematic, so production routing must be checked against it before releasing a
PCB revision.

| Function | GPIO | Notes |
| --- | ---: | --- |
| LOCATE / OFF | 2 / 3 | Active-low switches using internal pull-ups and 25 ms polling debounce |
| POWER_HOLD | 4 | High holds the system latch; firmware releases it on shutdown |
| LCD 5 V enable | 5 | Active-high TPS61023 enable; remains low in USB idle |
| LCD RS, E, D4–D7 | 6–11 | 3.3 V outputs into the SN74LVC8T245PWR A-side; LCD R/W is grounded |
| LCD backlight | 12 | PWM into the logic-level backlight MOSFET |
| GP-02 UART TX/RX | 16 / 17 | UART0 at 9,600 8N1; RX is receiver output |
| GNSS enable | 18 | Active-high switched receiver enable; firmware waits 5 ms for the rail before assigning UART pins |
| Battery divider | 26 / ADC0 | 100 kΩ / 100 kΩ (2:1) with 100 nF; firmware waits 30 ms (6× the 5 ms RC constant) before sampling |
| USB VBUS / charger status | 19 / 20 | VBUS active-high; USB device pull-up is enabled only while VBUS is present; charger status active-low/open-drain |
| Battery-divider enable | 21 | Active-high only for the ADC sampling window |

The selected power circuit must permit USB VBUS to sustain the MCU after
`POWER_HOLD` is released. `POWER_HOLD` must not be connected to any reset or
watchdog output. The GP-02 is explicitly disabled in USB idle, and no GNSS
coordinates are written to flash.

On a battery start, `POWER_HOLD` remains low until the software has observed
the continuous LOCATE hold for one second. A LOCATE already held while the MCU
comes out of reset is timestamped at boot (`0 ms`), so the accepted-session
deadlines retain the physical press edge as closely as the latch power-up
latency permits; they are never rebased to the end of debounce or hold checks.

## Flash configuration reservation

`FlashConfigStore` uses the final two physical flash sectors (8 KiB) on the
2 MiB production flash: inactive sector erase/write, XIP read-back/CRC
verification, then a one-way commit marker. The application image must remain
below that reserved tail. Check the generated `.elf`/map in release CI and do
not change the configured flash size without revisiting this reservation.

The linker asserts that the image ends before the reserved region. A power loss
at any write phase leaves the previous committed record valid. Factory reset
commits defaults through the same inactive-slot transaction; it never erases
application firmware or destroys the prior record before defaults verify.
