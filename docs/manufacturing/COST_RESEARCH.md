# Five-unit cost research snapshot

Snapshot date: **2026-08-21 UTC**. Quantity basis: five finished units. Currency:
USD. Destination, shipping method, tax, duties, assembly stock class, and coupons
are intentionally unselected. This is attributable research, **not a cart, landed
quote, or cost-gate pass**.

## Exact-part storefront subtotal

The prices below are public LCSC storefront prices visible on the snapshot date.
They cover only seven exact engineering-BOM lines and use the applicable 1+ or 5+
tier. JLCPCB assembly inventory/prices can differ from the LCSC storefront.

| BOM part | Qty | Observed unit price | Five-unit extension | Source |
|---|---:|---:|---:|---|
| RP2040 | 5 | $0.9930 | $4.9650 | [LCSC C2040](https://www.lcsc.com/product-detail/Microcontroller-Units-MCUs-MPUs-SOCs_span-style-background-color-ff0-Raspberry-span-Pi-RP2040_C2040.html) |
| W25Q16JVUXIQ | 5 | $0.5066 | $2.5330 | [LCSC C2843335](https://lcsc.com/product-detail/NOR-FLASH_Winbond-Elec_C2843335.html) |
| BQ24074RGTR | 5 | $2.1335 | $10.6675 | [LCSC C54313](https://www.lcsc.com/product-detail/battery-management_ti-bq24074rgtr_C54313.html) |
| TPS63802DLAR | 5 | $1.0846 | $5.4230 | [LCSC C2845237](https://www.lcsc.com/product-detail/DC-DC-Converters_Texas-Instruments-TPS63802DLAR_C2845237.html) |
| TPS61023DRLR | 5 | $0.2673 | $1.3365 | [LCSC C919459](https://www.lcsc.com/product-detail/dc-dc%20converters_texas%20instruments_tps61023drlr_C919459.html) |
| SN74LVC8T245PWR | 5 | $0.3893 | $1.9465 | [LCSC C27643](https://www.lcsc.com/product-detail/Translators-Level-Shifters_Texas-Instruments_C27643.html) |
| USB4105-GF-A | 5 | $1.0330 | $5.1650 | [LCSC C3020560](https://www.lcsc.com/product-detail/C3020560.html) |
| **Observed subtotal** | | | **$32.0365** | Excludes every line below |

The GP-02 manufacturer listing was out of stock at LCSC in the available snapshot,
so no price is recorded. Substitution is not assumed.

## Public JLCPCB service floors

The production design uses four layers so USB and GNSS RF have an uninterrupted
In1 ground reference while In2 distributes 3.3 V around the under-7 mm LCD RS,
under-4 mm LOCATE, and under-6 mm QSPI SCLK/SD2 crossovers; USB and RF stay on
outer layers. These are the only preflight-allowlisted signal tracks on an
inner layer. The earlier two-layer cost
target was rejected after routing fragmented the ground return. For comparison,
JLCPCB advertises a standard two-layer board no larger than 100 × 100 mm at a
promotional fabrication price starting at $2 for five boards. Its published 2025
economic-PCBA schedule lists an $8 setup fee, $1.50 stencil fee, $0.0016 per
automated joint, $3 per extended component feeder, and separate component costs.
These are pricing rules, not a project quote: [PCB order guide](https://jlcpcb.com/help/article/how-do-i-place-an-order),
[assembly price schedule](https://jlcpcb.com/help/article/pcb-assembly-price).

The bare-board + setup + stencil public floor is therefore $11.50 before joints,
feeders, components, X-ray, hand assembly, shipping, tax, or duties. No coupon is
counted. The automated Gerber and footprint-contract gates are clean, but a complete
quote still requires the signed-off GUI ERC, exact ordered-part overlays, and populated
supplier/JLC carts.

## Unquoted release-blocking lines

- Remaining semiconductors, crystal, inductors, protection, passives, connectors,
  switches, LCD header, and charge LED
- GP-02, passive patch/coax, exact blue LCD, protected 3-wire LiPo, and harnesses
- PCB assembly joints, extended feeders, QFN inspection, excess/minimum parts
- Window, seal, gasket cord, boots/membrane, USB plug, inserts, screws, light pipe,
  PETG/ASA and flexible filament, failed-print allowance
- All supplier/JLC shipping, tax, import duty, payment/FX fees, setup and consumables

The authoritative gate remains a saved, date-stamped five-unit cart total of no
more than $150. Research subtotals must never be filled into that gate as landed cost.
