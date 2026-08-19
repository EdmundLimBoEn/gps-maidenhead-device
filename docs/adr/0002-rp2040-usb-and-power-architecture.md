# ADR-0002: Use RP2040, USB-C, power-path charging, and hardware shutdown

- Status: accepted
- Date: 2026-08-19

## Context

The device needs cross-platform USB configuration, end-user firmware updates, operation while charging, eight-hour outing endurance, and enough retained charge for one check after a year of storage. Custom firmware is explicitly allowed.

## Decision

Use an RP2040 with native USB and external QSPI flash. USB-C carries 5 V charging and USB 2.0 data. Use a BQ24074-class power-path charger and a low-leak hardware soft latch that physically removes switched system power. USB VBUS may keep the MCU in a dark, GNSS-off configuration state.

Normal and recovery updates use RP2040 ROM BOOTSEL and UF2. Normal firmware can reboot itself into BOOTSEL. If application firmware cannot run, removing the rear cover and holding a labelled internal BOOTSEL switch while attaching USB forces recovery without electrically multiplexing a runtime button onto QSPI flash control.

## Consequences

- Updates are recoverable without a debug probe.
- Shutdown current depends mainly on charger, load-switch, and protection leakage rather than MCU sleep quality.
- The PCB needs additional flash, USB protection, latch logic, and careful power sequencing.
- Unsigned custom firmware can replace all application behavior; the GUI must warn and back up configuration first.
