# ADR-0001: Use a two-button check-session interaction

- Status: accepted
- Date: 2026-08-19

## Context

The device must be quick to use alongside a radio, survive long storage, and remain understandable when given to another operator. On-device customization would conflict with the 16×2 display, weather-sealed controls, and simple “survival-kit” character.

## Decision

Use two matching recessed elastomer controls: `LOCATE` and `OFF`. Both require a continuous one-second hold. `LOCATE` begins a time-bounded check session; `OFF` ends it. A five-second hold of both controls restores factory settings. All other settings require USB and the Python configurator.

The device never displays a cached location. It shows `ACQUIRING GPS` until a current valid fix exists, then `GRID: XX00XX`. A successful fix flashes the backlight. Once a one-second hold is accepted, default dim and shutdown deadlines are 60 and 120 seconds from its initial button-down edge.

## Consequences

- Operation is obvious and accidental bag activation is less likely.
- The enclosure needs only two sealed actuators.
- Configuration requires a computer and data-capable USB cable.
- A cold start may consume the entire default session and return `NO GPS`; users can lengthen the timeout in the GUI.
