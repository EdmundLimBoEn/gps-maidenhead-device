# ADR-0003: Use GP-02 with a remote internal passive patch for V1

- Status: accepted
- Date: 2026-08-19

## Context

The first five complete units must each land below US$30. A proven integrated-patch Quectel L86-M33 consumes too much of that budget and constrains antenna orientation behind the LCD-sized front face.

## Decision

Use a JLCPCB-assembled Ai-Thinker GP-02 receiver and connect it through a short controlled-impedance trace, u.FL/I-PEX, and short coax to a passive ceramic patch mounted beneath the enclosure's top wall. Keep the device sealed with no external antenna port.

Retain L86-M33 as a documented fallback only if the primary design fails its open-sky acquisition criterion after placement and noise experiments.

## Consequences

- Expected receiver cost falls by roughly US$4–5 per unit at the prices observed during planning.
- Final assembly gains one coax connection and antenna adhesive operation.
- RF layout, antenna sourcing, placement, and boost-converter noise become explicit validation risks.
- Cost must still be verified from a complete five-unit landed quote before ordering.

