# ADR-0004: Put customization in an open Python desktop tool

- Status: accepted
- Date: 2026-08-19

## Context

Recipients should be able to rearrange the status row, change time/date presentation, select named time zones, adjust brightness and timers, switch GNSS behavior, reuse profiles, and install future or community firmware. The device itself has only two controls.

## Decision

Build a Python 3.11+ Tkinter configurator for Windows, macOS, and Linux. Communicate using versioned newline-delimited JSON over USB CDC. Provide a drag-and-drop display builder with exact 16-character preview, versioned JSON profiles, diagnostics, factory reset, and GUI-managed UF2 updates.

Use reciprocal licensing: GPL-3.0-or-later for software, CERN-OHL-S-2.0 for hardware/CAD, and CC-BY-SA-4.0 for documentation.

## Consequences

- Recipients must install Python and use a data-capable cable.
- Profiles make a 5–20 device gift batch practical.
- Named-zone transition data can be prepared on the host without placing a global geographic/time-zone database on the MCU.
- Third-party dependencies and contributed derivatives must remain license-compatible.

