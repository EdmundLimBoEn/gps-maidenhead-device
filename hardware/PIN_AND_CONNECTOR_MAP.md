# Pin and connector map — Revision A

SPDX-License-Identifier: CC-BY-SA-4.0

This table is the electrical contract between the board and
`firmware/include/pocket_locator/board/pins.hpp`. A PCB release must reconcile
it against the *purchased* GP-02, LCD and charger datasheets; a named net is
not evidence that a symbol pin is correct.

## RP2040 assignment

| RP2040 pin/function | Net | Connected hardware | Electrical notes |
|---|---|---|---|
| GPIO2 | `LOCATE_N` | SW1 | Active low; local pull-up to 3V3; the same actuator starts the hardware latch through an isolated transistor path. |
| GPIO3 | `OFF_N` | SW2 | Active low; local pull-up to 3V3. |
| GPIO4 | `POWER_HOLD` | Q2 gate/control | Assert high only after one-second LOCATE validation. Must default low/Hi-Z at reset. |
| GPIO5 | `LCD_POWER_EN` | U5 EN | Active high; USB idle keeps the 5 V LCD rail disconnected. |
| GPIO6 | `LCD_RS_3V3` | U6 A0 | U6 B0 -> J3 pin 4. |
| GPIO7 | `LCD_E_3V3` | U6 A1 | U6 B1 -> J3 pin 6. |
| GPIO8 | `LCD_D4_3V3` | U6 A2 | U6 B2 -> J3 pin 11. |
| GPIO9 | `LCD_D5_3V3` | U6 A3 | U6 B3 -> J3 pin 12. |
| GPIO10 | `LCD_D6_3V3` | U6 A4 | U6 B4 -> J3 pin 13. |
| GPIO11 | `LCD_D7_3V3` | U6 A5 | U6 B5 -> J3 pin 14. |
| GPIO12 / PWM | `BL_PWM` | Q3 gate | Q3 is LCD backlight low-side switch; do not drive LCD logic supply with PWM. |
| GPIO16 / UART0 TX | `GNSS_RX` | U7 UART input | MCU output to receiver input. |
| GPIO17 / UART0 RX | `GNSS_TX` | U7 UART output | Receiver output to MCU input. |
| GPIO18 | `GNSS_EN` | U7 enable/load switch | Default low; does not supply GNSS backup power during shutdown. |
| GPIO19 | `VBUS_PRESENT` | VBUS sense divider | Series/diode isolated: VBUS must never power 3V3 through this pin. |
| GPIO20 | `CHG_N` | U3 CHG output | Open drain/active low; RCHGPU1 is the explicit 100 kΩ logic pull-up, in parallel with the separately current-limited RCHG1/LED indicator branch. |
| GPIO21 | `BAT_SENSE_EN` | Q5/Q4 divider switch | Pulse high, wait for the 100 nF ADC node to settle, sample, then return low. |
| GPIO26 / ADC0 | `BAT_ADC` | switched divider | Q4 isolates BAT whenever GPIO21 is low or 3V3 is absent; calibrate before setting battery icon thresholds. |
| QSPI CSn (ROM BOOTSEL) | `BOOTSEL_N` | SW3 to GND | Physical recovery switch only. Never connect to ordinary GPIO or LCD. |
| RUN | `RUN_N` | SW4 to GND / TP | Reset; pull-up and capacitor must follow RP2040 reference circuit. |
| XIN / XOUT | `XIN` / `XOUT` | X1 ABM8-272-T3 | 15 pF C0G loads; XOUT passes through 1 kΩ RXTAL1 to `XOUT_XTAL` to limit crystal drive. |
| SWDIO / SWCLK | `SWDIO`, `SWCLK` | TP pads | Test pads, no production debug connector required. |

Unused GPIOs are not routed to external connectors. Keep their reset pulls as
recommended by the RP2040 hardware design guide.

## External connectors and LCD header

| Connector / pin | Net | Direction / purpose |
|---|---|---|
| J1 USB-C A4/A9/B4/B9 | `VBUS_RAW` | 5 V receptacle input; F1 creates protected `VBUS` for charger and sensing. No PD source capability. |
| J1 USB-C A6/B6 | `USB_DP_CONN` | USB 2.0 D+ into D1; D1 output and RUSB1 create `USB_DP` at RP2040. |
| J1 USB-C A7/B7 | `USB_DM_CONN` | USB 2.0 D− into D1; D1 output and RUSB2 create `USB_DM` at RP2040. |
| J1 CC1, CC2 | `CC1`, `CC2` | Independent 5.1 kΩ Rd to GND. |
| J1 shield and GND pins | `GND` | Tie to ground plane at connector; final EMI treatment requires review. |
| J2 pin 1 | `BAT` | Protected cell positive to BQ24074 BAT. BQ24074 OUT, rather than the raw cell, creates `SYS_RAW`. |
| J2 pin 2 | `CHG_TS` | Cell thermistor to BQ24074 TS; TH1 is alternative only. |
| J2 pin 3 | `GND` | Cell return. |
| J3 pin 1 / 2 | `GND` / `5V_LCD` | LCD logic supply. |
| J3 pin 3 | `LCD_VO` | Contrast potentiometer/divider, 5 V-safe. |
| J3 pin 4 / 6 | `LCD_RS` / `LCD_E` | From U6 B0/B1. |
| J3 pin 5 | `GND` | LCD R/W permanently low. |
| J3 pins 7–10 | `GND` | LCD D0–D3 unused in 4-bit mode. |
| J3 pins 11–14 | `LCD_D4`–`LCD_D7` | From U6 B2–B5. |
| J3 pin 15 / 16 | `LCD_BL_A` / `LCD_BL_K` | Positive through verified current limit; Q3 PWM low side. |
| J4 centre / shell | `GNSS_RF_50R` / `GND` | u.FL to enclosure patch; centre trace has 50-ohm grounded-coplanar target. |

## Required test points

`VBUS`, `BAT`, `SYS_RAW`, `3V3`, `5V_LCD`, `GND`, `POWER_HOLD`, `GNSS_TX`,
`GNSS_RX`, `SWDIO`, `SWCLK`, `RUN_N`, and `BOOTSEL_N` shall be present as
labelled, probe-accessible pads. Test pad placement must preserve the GNSS
RF keep-out and never turn a debug probe ground lead into the RF return path.
