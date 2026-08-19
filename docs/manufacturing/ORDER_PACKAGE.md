# Five-unit order package

Prepare this package from a tagged, reviewed revision before placing any order.
The source tree contains engineering artifacts; this document is a controlled
checklist for turning them into an order without silently bypassing a gate.

## Include

- KiCad project, schematic PDF, Gerbers, drill, IPC/netlist, BOM, CPL, assembly
  drawing, and DRC/ERC reports generated from the same commit.
- Exact manufacturer part numbers, approved substitutes, stock snapshots, and
  physical drawings for the LCD, patch/coax, cell, switches, connectors, window,
  gasket, screws, and inserts.
- JLCPCB five-board/assembly cart export plus every external supplier cart.
- Enclosure source, STL exports, print material/setting sheet, and an unpopulated
  fit-check record.
- Firmware UF2 hash, configurator version/profile, assembly guide, bring-up
  procedure, and recovery instructions.

## Cost calculation

```
five_unit_total = JLC PCB + assembly + setup + stencil/fixture + shipping + tax
                + all non-JLC minimum quantities + enclosure consumables
per_finished_unit = five_unit_total / 5
```

The order gate passes only when `five_unit_total <= US$150`. Do not exclude spare
minimum quantities, shipping, taxes, fixture charges, or enclosure consumables.
Store the rendered carts and totals with the release evidence.

## Sign-off

| Role | Name | Date | Commit / revision |
|---|---|---|---|
| Electrical review |  |  |  |
| RF / layout review |  |  |  |
| Mechanical fit review |  |  |  |
| Cost gate |  |  |  |
| Order authorization |  |  |  |
