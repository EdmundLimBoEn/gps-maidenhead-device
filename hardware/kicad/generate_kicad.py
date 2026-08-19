#!/usr/bin/env python3
"""Generate the connected Revision-A KiCad 7 PCB and review schematic.

The PCB uses only primitives embedded in the board file, so it is reproducible
without a local footprint library.  The schematic is legacy Eeschema v4 source
because KiCad 7 can import it while preserving the deliberately explicit net
labels.  Purchased-part drawings remain the authority before fabrication.

SPDX-License-Identifier: CERN-OHL-S-2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


NET_NAMES = [
    "GND", "VBUS", "USB_DP_CONN", "USB_DM_CONN", "USB_DP_ESD", "USB_DM_ESD",
    "USB_DP", "USB_DM", "CC1", "CC2", "BAT", "BAT_SENSE_SW", "SYS_RAW",
    "PWR_START_GATE", "PWR_START_OUT", "PWR_EN", "POWER_HOLD", "3V3",
    "1V1", "3V3_GNSS", "GNSS_EN", "GNSS_TX", "GNSS_RX", "GNSS_PPS",
    "GNSS_RF_50R", "LCD_POWER_EN", "5V_LCD", "LCD_RS_3V3", "LCD_E_3V3",
    "LCD_D4_3V3", "LCD_D5_3V3", "LCD_D6_3V3", "LCD_D7_3V3", "LCD_RS",
    "LCD_E", "LCD_D4", "LCD_D5", "LCD_D6", "LCD_D7", "LCD_VO",
    "LCD_BL_A", "LCD_BL_K", "BL_PWM", "LOCATE_N", "OFF_N", "VBUS_PRESENT",
    "CHG_N", "RUN_N", "BOOTSEL_N", "SWDIO", "SWCLK", "XIN", "XOUT",
    "QSPI_SCLK", "QSPI_SD0", "QSPI_SD1", "QSPI_SD2", "QSPI_SD3", "QSPI_CSN",
    "BB_SW1", "BB_SW2", "BB_FB", "LCD_SW", "LCD_FB", "CHG_TS", "CHG_ISET",
    "CHG_ILIM", "CHG_ITERM", "CHG_TMR", "BAT_ADC", "BAT_SENSE_EN",
    "BAT_SENSE_GATE", "START_SENSE",
]
NET = {name: index + 1 for index, name in enumerate(NET_NAMES)}


@dataclass(frozen=True)
class Pad:
    number: str
    x: float
    y: float
    net: str = ""
    kind: str = "smd"
    sx: float = 0.8
    sy: float = 0.8
    drill: float = 0.0


@dataclass
class Footprint:
    ref: str
    value: str
    x: float
    y: float
    pads: list[Pad]
    width: float
    height: float
    layer: str = "F.Cu"
    courtyard: bool = True


def q(value: str) -> str:
    return value.replace('"', "'")


def passive(ref: str, value: str, x: float, y: float, a: str, b: str, size: str = "0402") -> Footprint:
    length, width, gap = ((2.0, 1.25, 1.0) if size == "0603" else (1.45, 0.85, 0.7))
    return Footprint(ref, value, x, y, [Pad("1", -gap / 2, 0, a, sx=0.65, sy=width * 0.7), Pad("2", gap / 2, 0, b, sx=0.65, sy=width * 0.7)], length, width)


def sot23(ref: str, value: str, x: float, y: float, nets: tuple[str, str, str]) -> Footprint:
    return Footprint(ref, value, x, y, [
        Pad("1", -0.95, 0.95, nets[0], sx=1.0, sy=0.8),
        Pad("2", 0.95, 0.95, nets[1], sx=1.0, sy=0.8),
        Pad("3", 0, -0.95, nets[2], sx=1.0, sy=0.8),
    ], 3.0, 2.6)


def tssop(ref: str, value: str, x: float, y: float, pin_nets: list[str]) -> Footprint:
    count = len(pin_nets)
    half = count // 2
    pads: list[Pad] = []
    for i in range(half):
        yy = (i - (half - 1) / 2) * 0.65
        pads.append(Pad(str(i + 1), -3.1, yy, pin_nets[i], sx=1.5, sy=0.4))
        pads.append(Pad(str(count - i), 3.1, yy, pin_nets[count - i - 1], sx=1.5, sy=0.4))
    return Footprint(ref, value, x, y, pads, 6.8, half * 0.65 + 1.2)


def qfn(ref: str, value: str, x: float, y: float, pin_nets: list[str], body: float, pitch: float, epad: str = "GND") -> Footprint:
    side = len(pin_nets) // 4
    pads: list[Pad] = []
    reach = body / 2 + 0.35
    span = (side - 1) * pitch
    for i, net in enumerate(pin_nets):
        edge, offset = divmod(i, side)
        p = offset * pitch - span / 2
        if edge == 0:
            pads.append(Pad(str(i + 1), -reach, p, net, sx=0.75, sy=pitch * 0.58))
        elif edge == 1:
            pads.append(Pad(str(i + 1), p, reach, net, sx=pitch * 0.58, sy=0.75))
        elif edge == 2:
            pads.append(Pad(str(i + 1), reach, -p, net, sx=0.75, sy=pitch * 0.58))
        else:
            pads.append(Pad(str(i + 1), -p, -reach, net, sx=pitch * 0.58, sy=0.75))
    pads.append(Pad(str(len(pin_nets) + 1), 0, 0, epad, sx=body * 0.46, sy=body * 0.46))
    return Footprint(ref, value, x, y, pads, body + 1.8, body + 1.8)


def rp2040(x: float, y: float) -> Footprint:
    pins = [""] * 56
    for pin in (1, 10, 22, 33, 42, 49): pins[pin - 1] = "3V3"
    for pin in (23, 50): pins[pin - 1] = "1V1"
    gpio = {4: "LOCATE_N", 5: "OFF_N", 6: "POWER_HOLD", 7: "LCD_POWER_EN", 8: "LCD_RS_3V3", 9: "LCD_E_3V3", 11: "LCD_D4_3V3", 12: "LCD_D5_3V3", 13: "LCD_D6_3V3", 14: "LCD_D7_3V3", 15: "BL_PWM", 27: "GNSS_RX", 28: "GNSS_TX", 29: "GNSS_EN", 30: "VBUS_PRESENT", 31: "CHG_N", 32: "BAT_SENSE_EN", 38: "BAT_ADC"}
    for pin, net in gpio.items(): pins[pin - 1] = net
    pins[18] = "GND"       # TESTEN pin 19
    pins[19] = "XIN"; pins[20] = "XOUT"
    pins[23] = "SWCLK"; pins[24] = "SWDIO"; pins[25] = "RUN_N"
    pins[42] = "3V3"       # ADC_AVDD pin 43
    pins[43] = "3V3"       # VREG_VIN pin 44
    pins[44] = "1V1"       # VREG_VOUT pin 45
    pins[45] = "USB_DM"; pins[46] = "USB_DP"; pins[47] = "3V3"
    pins[50] = "QSPI_SD3"; pins[51] = "QSPI_SCLK"; pins[52] = "QSPI_SD0"
    pins[53] = "QSPI_SD2"; pins[54] = "QSPI_SD1"; pins[55] = "QSPI_CSN"
    return qfn("U1", "RP2040", x, y, pins, 7.0, 0.4)


def usb_c(x: float, y: float) -> Footprint:
    pads = [
        Pad("A1", 0.8, -3.2, "GND", "smd", 1.2, 0.6), Pad("A4", 0.8, -2.4, "VBUS", "smd", 1.2, 0.6),
        Pad("A5", 0.8, -1.6, "CC1", "smd", 1.2, 0.6), Pad("A6", 0.8, -0.8, "USB_DP_CONN", "smd", 1.2, 0.6),
        Pad("A7", 0.8, 0.0, "USB_DM_CONN", "smd", 1.2, 0.6), Pad("A9", 0.8, 0.8, "VBUS", "smd", 1.2, 0.6),
        Pad("A12", 0.8, 1.6, "GND", "smd", 1.2, 0.6), Pad("B1", 0.8, 2.4, "GND", "smd", 1.2, 0.6),
        Pad("B4", 0.8, 3.2, "VBUS", "smd", 1.2, 0.6), Pad("B5", 0.8, 4.0, "CC2", "smd", 1.2, 0.6),
        Pad("B6", 0.8, 4.8, "USB_DP_CONN", "smd", 1.2, 0.6), Pad("B7", 0.8, 5.6, "USB_DM_CONN", "smd", 1.2, 0.6),
        Pad("B9", 0.8, 6.4, "VBUS", "smd", 1.2, 0.6), Pad("B12", 0.8, 7.2, "GND", "smd", 1.2, 0.6),
        Pad("S1", -1.2, -4.0, "GND", "thru_hole", 2.2, 2.2, 1.2), Pad("S2", -1.2, 8.0, "GND", "thru_hole", 2.2, 2.2, 1.2),
    ]
    return Footprint("J1", "USB4105-GF-A", x, y - 2.0, pads, 5.0, 13.0)


def connector(ref: str, value: str, x: float, y: float, nets: list[str], pitch: float = 2.54, horizontal: bool = True) -> Footprint:
    pads: list[Pad] = []
    for i, net in enumerate(nets):
        px, py = ((i - (len(nets) - 1) / 2) * pitch, 0) if horizontal else (0, (i - (len(nets) - 1) / 2) * pitch)
        pads.append(Pad(str(i + 1), px, py, net, "thru_hole", 1.7, 1.7, 1.0))
    width = len(nets) * pitch if horizontal else 3.0
    height = 3.0 if horizontal else len(nets) * pitch
    return Footprint(ref, value, x, y, pads, width, height)


def gp02(x: float, y: float) -> Footprint:
    # Provisional 18-pad 16 x 12 mm castellated outline. Purchased module drawing is a release gate.
    pin_nets = ["3V3_GNSS", "GND", "GNSS_TX", "GNSS_RX", "GNSS_PPS", "", "", "", "", "", "", "", "", "", "", "", "GND", "GNSS_RF_50R"]
    pads: list[Pad] = []
    for i in range(9):
        pads.append(Pad(str(i + 1), -8.0, -5.0 + i * 1.25, pin_nets[i], sx=1.6, sy=0.75))
        pads.append(Pad(str(18 - i), 8.0, -5.0 + i * 1.25, pin_nets[17 - i], sx=1.6, sy=0.75))
    return Footprint("U7", "Ai-Thinker GP-02 PROVISIONAL FOOTPRINT", x, y, pads, 17.5, 12.0)


def fp_text(ref: str, value: str, x: float, y: float, w: float, h: float, layer: str = "F.SilkS") -> str:
    justify = " (justify mirror)" if layer.startswith("B.") else ""
    return f'    (fp_text reference "{q(ref)}" (at 0 {-h / 2 - 0.9:.3f}) (layer "{layer}") (effects (font (size 0.7 0.7) (thickness 0.12)){justify}))\n    (fp_text value "{q(value)}" (at 0 {h / 2 + 0.9:.3f}) (layer "F.Fab") hide (effects (font (size 0.55 0.55) (thickness 0.1))))'


def render_footprint(fp: Footprint) -> str:
    lines = [f'  (footprint "RevA:{q(fp.ref)}" (layer "{fp.layer}") (at {fp.x:.3f} {fp.y:.3f})', fp_text(fp.ref, fp.value, fp.x, fp.y, fp.width, fp.height)]
    lines.append(f'    (fp_rect (start {-fp.width / 2:.3f} {-fp.height / 2:.3f}) (end {fp.width / 2:.3f} {fp.height / 2:.3f}) (stroke (width 0.15) (type default)) (fill none) (layer "F.SilkS"))')
    for pad in fp.pads:
        net = f' (net {NET[pad.net]} "{pad.net}")' if pad.net else ""
        if pad.kind == "thru_hole":
            lines.append(f'    (pad "{pad.number}" thru_hole circle (at {pad.x:.3f} {pad.y:.3f}) (size {pad.sx:.3f} {pad.sy:.3f}) (drill {pad.drill:.3f}) (layers "*.Cu" "*.Mask"){net})')
        else:
            shape = "rect" if pad.number == "1" else "roundrect"
            rr = " (roundrect_rratio 0.2)" if shape == "roundrect" else ""
            lines.append(f'    (pad "{pad.number}" smd {shape} (at {pad.x:.3f} {pad.y:.3f}) (size {pad.sx:.3f} {pad.sy:.3f}) (layers "F.Cu" "F.Paste" "F.Mask"){rr}{net})')
    lines.append("  )")
    return "\n".join(lines)


def all_footprints() -> list[Footprint]:
    fps: list[Footprint] = []
    fps.append(usb_c(1.6, 16.0))
    fps += [passive("F1", "500mA PTC", 5.2, 11.2, "VBUS", "VBUS", "0603"), passive("RCC1", "5.1k", 5.4, 14.2, "CC1", "GND"), passive("RCC2", "5.4k", 5.4, 15.8, "CC2", "GND")]
    fps.append(qfn("D1", "USBLC6-2SC6", 8.0, 18.2, ["USB_DP_CONN", "GND", "USB_DM_CONN", "USB_DM_ESD", "VBUS", "USB_DP_ESD"], 2.0, 0.65))
    fps += [passive("RUSB1", "27R", 11.0, 17.4, "USB_DP_ESD", "USB_DP"), passive("RUSB2", "27R", 11.0, 19.0, "USB_DM_ESD", "USB_DM")]

    bq_pins = ["VBUS", "BAT", "BAT", "CHG_TS", "GND", "VBUS", "CHG_TMR", "GND", "CHG_N", "SYS_RAW", "SYS_RAW", "CHG_ILIM", "CHG_ISET", "VBUS_PRESENT", "CHG_ITERM", "GND"]
    fps.append(qfn("U3", "BQ24074RGTR", 10.0, 28.2, bq_pins, 3.0, 0.5))
    fps += [passive("CIN1", "1uF", 6.7, 27.0, "VBUS", "GND", "0603"), passive("CBAT1", "4.7uF", 7.0, 30.0, "BAT", "GND", "0603"), passive("COUT1", "4.7uF", 13.4, 28.0, "SYS_RAW", "GND", "0603"), passive("RISET", "2.20k 404mA", 9.0, 32.0, "CHG_ISET", "GND"), passive("RILIM", "2.00k", 11.0, 32.0, "CHG_ILIM", "GND"), passive("RITERM", "3.30k", 13.0, 32.0, "CHG_ITERM", "GND"), passive("RTMR", "48.7k", 15.0, 32.0, "CHG_TMR", "GND"), passive("RVB1", "150k", 5.8, 24.0, "VBUS", "VBUS_PRESENT"), passive("RVB2", "100k", 7.5, 24.0, "VBUS_PRESENT", "GND")]
    fps.append(connector("J2", "JST-PH-3 BAT/NTC/GND", 10.0, 35.3, ["BAT", "CHG_TS", "GND"]))
    fps.append(passive("TH1", "10k NTC DNP", 16.8, 34.5, "CHG_TS", "GND", "0603"))
    fps.append(passive("RCHG", "1k", 4.7, 28.5, "3V3", "CHG_N", "0603"))

    # Signal-only power latch: no battery current passes through Q1.
    fps.append(sot23("Q1", "DMP3098L P-MOS", 18.0, 31.0, ("PWR_START_GATE", "SYS_RAW", "PWR_START_OUT")))
    fps.append(sot23("Q2", "DMN2050L N-MOS", 21.3, 31.0, ("POWER_HOLD", "GND", "PWR_START_GATE")))
    fps += [passive("RSTART", "1M", 17.5, 34.0, "SYS_RAW", "PWR_START_GATE"), passive("REN", "1M", 22.5, 34.0, "PWR_EN", "GND"), passive("D2", "BAT54 VBUS OR", 20.0, 27.0, "VBUS", "PWR_EN"), passive("D3", "BAT54 LOCATE isolate", 22.0, 27.0, "PWR_START_GATE", "LOCATE_N"), passive("D4", "BAT54 START OR", 24.0, 27.0, "PWR_START_OUT", "PWR_EN")]

    bb_pins = ["BB_SW1", "SYS_RAW", "PWR_EN", "GND", "BB_FB", "3V3", "BB_SW2", "3V3", "GND", "3V3"]
    fps.append(qfn("U4", "TPS63802DLAR 3V3 buck-boost", 25.0, 30.5, bb_pins, 3.0, 0.5))
    fps += [passive("LBB", "0.47uH", 25.0, 26.3, "BB_SW1", "BB_SW2", "0603"), passive("CBBIN", "10uF", 28.5, 32.5, "SYS_RAW", "GND", "0603"), passive("CBBOUT", "22uF", 31.0, 32.5, "3V3", "GND", "0603"), passive("RBB1", "511k", 29.0, 28.0, "3V3", "BB_FB"), passive("RBB2", "91k", 31.0, 28.0, "BB_FB", "GND")]

    fps.append(rp2040(31.0, 18.5))
    fps += [passive(f"C{i}", "100nF", 22.5 + (i % 6) * 1.5, 12.0 + (i // 6) * 1.5, "3V3", "GND") for i in range(1, 9)]
    fps += [passive("CVREG", "1uF", 27.5, 24.0, "1V1", "GND", "0603"), passive("CADC", "1uF", 29.5, 24.0, "3V3", "GND", "0603"), passive("RRESET", "100k", 34.0, 24.0, "3V3", "RUN_N"), passive("CRESET", "100nF", 36.0, 24.0, "RUN_N", "GND")]
    fps.append(passive("X1", "12MHz crystal", 31.0, 10.0, "XIN", "XOUT", "0603"))
    fps += [passive("CX1", "12pF C0G", 29.5, 8.5, "XIN", "GND"), passive("CX2", "12pF C0G", 32.5, 8.5, "XOUT", "GND")]

    flash_pins = ["QSPI_CSN", "QSPI_SD1", "QSPI_SD2", "GND", "QSPI_SD0", "QSPI_SCLK", "QSPI_SD3", "3V3"]
    fps.append(qfn("U2", "W25Q16JVUXIQ", 41.0, 18.5, flash_pins, 3.0, 0.5))
    fps += [passive("CFLASH", "100nF", 41.0, 22.0, "3V3", "GND"), passive("RBOOT", "1k", 38.0, 20.5, "QSPI_CSN", "BOOTSEL_N")]
    fps.append(sot23("SW3", "BOOTSEL tact", 46.0, 20.0, ("BOOTSEL_N", "GND", "")))
    fps.append(sot23("SW4", "RUN tact", 46.0, 23.5, ("RUN_N", "GND", "")))

    # GPIO21 switches the divider.  BAT is isolated from an unpowered ADC.
    fps.append(sot23("Q4", "DMP3098L BAT sense", 39.0, 29.0, ("BAT_SENSE_GATE", "BAT", "BAT_SENSE_SW")))
    fps.append(sot23("Q5", "DMN2050L BAT sense gate", 42.0, 29.0, ("BAT_SENSE_EN", "GND", "BAT_SENSE_GATE")))
    fps += [passive("RBATG", "1M", 39.5, 32.0, "BAT", "BAT_SENSE_GATE"), passive("RBAT1", "100k", 44.5, 29.0, "BAT_SENSE_SW", "BAT_ADC"), passive("RBAT2", "100k", 46.5, 29.0, "BAT_ADC", "GND"), passive("CBATADC", "100nF", 48.5, 29.0, "BAT_ADC", "GND")]

    fps.append(qfn("U8", "TPS22916 GNSS load switch", 49.0, 28.0, ["3V3", "GND", "GNSS_EN", "3V3_GNSS", "3V3_GNSS", "GND"], 2.0, 0.65))
    fps += [passive("CGIN", "1uF", 46.5, 25.5, "3V3", "GND", "0603"), passive("CGOUT", "4.7uF", 51.5, 25.5, "3V3_GNSS", "GND", "0603"), passive("RGNSSEN", "100k", 49.0, 31.0, "GNSS_EN", "GND")]
    fps.append(gp02(61.0, 28.5))
    fps.append(connector("J4", "Hirose 20449-001E u.FL", 78.0, 28.5, ["GNSS_RF_50R", "GND"], 1.6, False))

    lcd_boost = ["LCD_FB", "LCD_POWER_EN", "SYS_RAW", "GND", "LCD_SW", "5V_LCD"]
    fps.append(qfn("U5", "TPS61023DRLR LCD boost", 15.0, 7.0, lcd_boost, 2.0, 0.65))
    fps += [passive("LLCD", "1uH", 11.5, 7.0, "SYS_RAW", "LCD_SW", "0603"), passive("CLCDIN", "4.7uF", 12.0, 9.5, "SYS_RAW", "GND", "0603"), passive("CLCDO1", "10uF", 18.0, 6.0, "5V_LCD", "GND", "0603"), passive("CLCDO2", "10uF", 18.0, 8.0, "5V_LCD", "GND", "0603"), passive("RLCD1", "732k", 20.0, 6.0, "5V_LCD", "LCD_FB"), passive("RLCD2", "100k", 20.0, 8.0, "LCD_FB", "GND"), passive("RLCDEN", "100k", 15.0, 10.0, "LCD_POWER_EN", "GND")]
    level_nets = ["LCD_RS_3V3", "LCD_E_3V3", "LCD_D4_3V3", "LCD_D5_3V3", "LCD_D6_3V3", "LCD_D7_3V3", "", "", "GND", "GND", "GND", "3V3", "5V_LCD", "", "", "LCD_D7", "LCD_D6", "LCD_D5", "LCD_D4", "LCD_E", "LCD_RS", "", "GND", "5V_LCD"]
    fps.append(tssop("U6", "SN74LVC8T245PWR dual-rail", 40.0, 7.0, level_nets))
    fps += [passive("CULS", "100nF", 35.5, 4.0, "3V3", "GND"), passive("CULD", "100nF", 44.5, 4.0, "5V_LCD", "GND")]
    fps.append(passive("RVO1", "4.7k", 48.0, 5.0, "5V_LCD", "LCD_VO"))
    fps.append(passive("RVO2", "560R", 50.0, 5.0, "LCD_VO", "GND"))
    fps.append(sot23("Q3", "DMN2050L backlight", 53.0, 7.0, ("BL_PWM", "GND", "LCD_BL_K")))
    fps.append(passive("RBL", "68R safe-start", 56.0, 5.0, "5V_LCD", "LCD_BL_A", "0603"))

    lcd_nets = ["GND", "5V_LCD", "LCD_VO", "LCD_RS", "GND", "LCD_E", "GND", "GND", "GND", "GND", "LCD_D4", "LCD_D5", "LCD_D6", "LCD_D7", "LCD_BL_A", "LCD_BL_K"]
    fps.append(connector("J3", "WH1602B 1x16 LCD", 39.0, 1.4, lcd_nets))
    fps.append(sot23("SW1", "LOCATE TL3305", 74.0, 8.0, ("LOCATE_N", "GND", "")))
    fps.append(sot23("SW2", "OFF TL3305", 74.0, 14.0, ("OFF_N", "GND", "")))
    fps += [passive("RLOC", "100k", 69.0, 8.0, "3V3", "LOCATE_N"), passive("ROFF", "100k", 69.0, 14.0, "3V3", "OFF_N")]

    test_nets = ["VBUS", "BAT", "SYS_RAW", "3V3", "5V_LCD", "GND", "POWER_HOLD", "GNSS_TX", "GNSS_RX", "SWDIO", "SWCLK", "RUN_N", "BOOTSEL_N"]
    for i, net in enumerate(test_nets):
        fps.append(Footprint(f"TP{i+1}", net, 48.0 + (i % 7) * 4.2, 18.0 + (i // 7) * 4.0, [Pad("1", 0, 0, net, sx=1.3, sy=1.3)], 1.6, 1.6))
    return fps


def pad_locations(fps: list[Footprint]) -> dict[str, list[tuple[float, float]]]:
    locations: dict[str, list[tuple[float, float]]] = {name: [] for name in NET_NAMES}
    for fp in fps:
        for pad in fp.pads:
            if pad.net:
                locations[pad.net].append((fp.x + pad.x, fp.y + pad.y))
    return locations


def route_segments(fps: list[Footprint]) -> list[str]:
    locations = pad_locations(fps)
    special = {"GND", "USB_DP_CONN", "USB_DM_CONN", "USB_DP_ESD", "USB_DM_ESD", "USB_DP", "USB_DM", "GNSS_RF_50R"}
    routable = [name for name in NET_NAMES if name not in special and len(locations[name]) > 1]
    forbidden = [(13.4, 14.6), (21.4, 22.6), (27.5, 29.5)]
    lanes: list[float] = []
    y = 3.1
    while len(lanes) < len(routable) and y < 35.0:
        if not any(lo <= y <= hi for lo, hi in forbidden): lanes.append(y)
        y += 0.43
    lines: list[str] = []
    for net_index, name in enumerate(routable):
        pts = locations[name]
        lane = lanes[net_index]
        width = 0.55 if name in {"VBUS", "BAT", "SYS_RAW", "3V3", "3V3_GNSS", "5V_LCD"} else 0.20
        xs: list[float] = []
        for i, (x, py) in enumerate(pts):
            escape = min(80.2, max(0.8, x + ((i % 5) - 2) * 0.11))
            xs.append(escape)
            if abs(escape - x) > 0.001:
                lines.append(f'  (segment (start {x:.3f} {py:.3f}) (end {escape:.3f} {py:.3f}) (width {width:.2f}) (layer "F.Cu") (net {NET[name]}))')
            lines.append(f'  (segment (start {escape:.3f} {py:.3f}) (end {escape:.3f} {lane:.3f}) (width {width:.2f}) (layer "F.Cu") (net {NET[name]}))')
            lines.append(f'  (via (at {escape:.3f} {lane:.3f}) (size 0.65) (drill 0.30) (layers "F.Cu" "B.Cu") (net {NET[name]}))')
        lines.append(f'  (segment (start {min(xs):.3f} {lane:.3f}) (end {max(xs):.3f} {lane:.3f}) (width {width:.2f}) (layer "B.Cu") (net {NET[name]}))')
    # Short, explicit USB pair and RF feed. The generic router excludes these.
    def chain(name: str, points: list[tuple[float, float]], width: float = 0.23, layer: str = "F.Cu") -> None:
        for a, b in zip(points, points[1:]):
            lines.append(f'  (segment (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (width {width:.2f}) (layer "{layer}") (net {NET[name]}))')
    for name in ("USB_DP_CONN", "USB_DM_CONN", "USB_DP_ESD", "USB_DM_ESD", "USB_DP", "USB_DM"):
        if len(locations[name]) >= 2: chain(name, locations[name])
    chain("GNSS_RF_50R", locations["GNSS_RF_50R"], 0.45)
    # RF launch ground-via fence.
    for x in (69.8, 72.0, 74.2, 76.4):
        for yy in (27.2, 29.8):
            lines.append(f'  (via (at {x:.3f} {yy:.3f}) (size 0.70) (drill 0.32) (layers "F.Cu" "B.Cu") (net {NET["GND"]}))')
    return lines


def board_text() -> str:
    fps = all_footprints()
    out = ['(kicad_pcb (version 20221018) (generator rev_a_generator)', '  (general (thickness 1.6))', '  (paper "A4")', '  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "b.Silkscreen") (37 "F.SilkS" user "f.Silkscreen") (44 "Edge.Cuts" user))', '  (setup (pad_to_mask_clearance 0))']
    out.append('  (net 0 "")')
    out.extend(f'  (net {NET[name]} "{name}")' for name in NET_NAMES)
    out += [
        '  (gr_rect (start 0 0) (end 81 37) (stroke (width 0.2) (type default)) (fill none) (layer "Edge.Cuts"))',
        '  (gr_text "MAIDENHEAD POCKET LOCATOR REV A" (at 40.5 36) (layer "B.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify mirror)))',
        '  (gr_rect (start 52 22) (end 80 35) (stroke (width 0.25) (type dash)) (fill none) (layer "F.SilkS"))',
        '  (gr_text "GNSS / RF\\nKEEP SWITCH NODES OUT" (at 65.5 23.5) (layer "F.SilkS") (effects (font (size 0.65 0.65) (thickness 0.1))))',
        '  (gr_text "USB" (at 2.5 9.5 90) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.1))))',
    ]
    out.extend(render_footprint(fp) for fp in fps)
    out.extend(route_segments(fps))
    out.append(f'  (zone (net {NET["GND"]}) (net_name "GND") (layer "B.Cu") (hatch edge 0.5) (connect_pads (clearance 0.20)) (min_thickness 0.20) (fill yes (thermal_gap 0.25) (thermal_bridge_width 0.25)) (polygon (pts (xy 0.3 0.3) (xy 80.7 0.3) (xy 80.7 36.7) (xy 0.3 36.7))))')
    out.append(')')
    return "\n".join(out) + "\n"


def schematic_component(ref: str, value: str, lib: str, x: int, y: int) -> str:
    return f'''$Comp\nL {lib} {ref}\nU 1 1 {ref.replace("#", "PWR")}\nP {x} {y}\nF 0 "{ref}" H {x + 250} {y + 100} 50  0000 C CNN\nF 1 "{q(value)}" H {x + 350} {y - 100} 50  0000 C CNN\n\t1    {x} {y}\n\t1 0 0 -1\n$EndComp\n'''


def schematic_text() -> str:
    # A readable, label-connected review schematic. Generic connector symbols
    # intentionally expose every IC pin and avoid unreviewed local libraries.
    lines = ['EESchema Schematic File Version 4', 'LIBS:power', 'LIBS:Device', 'LIBS:Connector_Generic', 'EELAYER 29 0', 'EELAYER END', '$Descr A3 16535 11693', 'Sheet 1 1', 'Title "Maidenhead Pocket Locator — connected Revision A"', 'Date "2026-08-19"', 'Rev "A electrical"', 'Comp "Open hardware — CERN-OHL-S-2.0"', 'Comment1 "Do not fabricate until exact GP-02/LCD/cell footprints and physical validation pass"', '$EndDescr']
    lines += ['Text Notes 700 650 0 110 ~ 22\nUSB-C / BQ24074 POWER PATH', 'Text Notes 4200 650 0 110 ~ 22\nTPS63802 ENABLE LATCH / 3V3', 'Text Notes 7900 650 0 110 ~ 22\nRP2040 / FLASH / USB', 'Text Notes 12200 650 0 110 ~ 22\nGNSS / LCD']
    blocks = [
        ("J1", "USB-C: VBUS,CC1,CC2,D+,D-,GND", "Connector_Generic:Conn_01x06", 1200, 1800),
        ("U3", "BQ24074: IN,BAT,TS,EN2,EN1,TMR,CE,CHG,OUT,ILIM,ISET,PGOOD,ITERM,GND", "Connector_Generic:Conn_01x14", 2600, 2100),
        ("J2", "BAT+,NTC,GND", "Connector_Generic:Conn_01x03", 1100, 4300),
        ("Q1", "DMP3098L signal PMOS", "Connector_Generic:Conn_01x03", 4700, 1600),
        ("Q2", "DMN2050L hold NMOS", "Connector_Generic:Conn_01x03", 4700, 2500),
        ("U4", "TPS63802: VIN,L1,L2,VOUT,FB,EN,MODE,PG,GND", "Connector_Generic:Conn_01x09", 6100, 2100),
        ("U1", "RP2040 QFN56 — see pin map", "Connector_Generic:Conn_02x20_Odd_Even", 9000, 2600),
        ("U2", "W25Q16: CS,DO,WP,GND,DI,CLK,HOLD,VCC", "Connector_Generic:Conn_01x08", 10600, 1900),
        ("U8", "TPS22916 GNSS load switch", "Connector_Generic:Conn_01x06", 12500, 1600),
        ("U7", "GP-02: VCC,GND,TX,RX,PPS,RF", "Connector_Generic:Conn_01x06", 14000, 1700),
        ("U5", "TPS61023: FB,EN,VIN,GND,SW,VOUT", "Connector_Generic:Conn_01x06", 12400, 4500),
        ("U6", "SN74LVC8T245: VCCA/A0-A5/DIR/OE/B0-B5/VCCB/GND", "Connector_Generic:Conn_02x12_Odd_Even", 14000, 4800),
        ("J3", "LCD: GND,5V,VO,RS,RW,E,D0-D7,BL+,BL-", "Connector_Generic:Conn_01x16", 15300, 5000),
    ]
    for block in blocks: lines.append(schematic_component(*block))
    # Net-labelled subsystem connections. Labels on both ends are electrical connections in legacy Eeschema.
    contracts = {
        "J1": ["VBUS", "CC1", "CC2", "USB_DP_CONN", "USB_DM_CONN", "GND"],
        "U3": ["VBUS", "BAT", "CHG_TS", "GND", "VBUS", "CHG_TMR", "GND", "CHG_N", "SYS_RAW", "CHG_ILIM", "CHG_ISET", "VBUS_PRESENT", "CHG_ITERM", "GND"],
        "J2": ["BAT", "CHG_TS", "GND"], "Q1": ["PWR_START_GATE", "PWR_START_OUT", "SYS_RAW"],
        "Q2": ["POWER_HOLD", "GND", "PWR_START_GATE"],
        "U4": ["SYS_RAW", "BB_SW1", "BB_SW2", "3V3", "BB_FB", "PWR_EN", "GND", "3V3", "GND"],
        "U2": ["QSPI_CSN", "QSPI_SD1", "QSPI_SD2", "GND", "QSPI_SD0", "QSPI_SCLK", "QSPI_SD3", "3V3"],
        "U8": ["3V3", "GND", "GNSS_EN", "3V3_GNSS", "3V3_GNSS", "GND"],
        "U7": ["3V3_GNSS", "GND", "GNSS_TX", "GNSS_RX", "GNSS_PPS", "GNSS_RF_50R"],
        "U5": ["LCD_FB", "LCD_POWER_EN", "SYS_RAW", "GND", "LCD_SW", "5V_LCD"],
        "J3": ["GND", "5V_LCD", "LCD_VO", "LCD_RS", "GND", "LCD_E", "GND", "GND", "GND", "GND", "LCD_D4", "LCD_D5", "LCD_D6", "LCD_D7", "LCD_BL_A", "LCD_BL_K"],
    }
    positions = {ref: (x, y) for ref, _, _, x, y in blocks}
    for ref, nets in contracts.items():
        x, y = positions[ref]
        for index, net in enumerate(nets):
            yy = y - ((len(nets) - 1) * 50) + index * 100
            lines += [f'Wire Wire Line\n\t{x - 100} {yy} {x - 350} {yy}', f'Text Label {x - 350} {yy} 2    45   ~ 0\n{net}']
    # RP2040 functional contract is shown as an explicit labelled bus beside U1.
    rp_nets = ["3V3", "1V1", "LOCATE_N", "OFF_N", "POWER_HOLD", "LCD_POWER_EN", "LCD_RS_3V3", "LCD_E_3V3", "LCD_D4_3V3", "LCD_D5_3V3", "LCD_D6_3V3", "LCD_D7_3V3", "BL_PWM", "GNSS_RX", "GNSS_TX", "GNSS_EN", "VBUS_PRESENT", "CHG_N", "BAT_SENSE_EN", "BAT_ADC", "RUN_N", "SWDIO", "SWCLK", "USB_DP", "USB_DM", "XIN", "XOUT", "QSPI_CSN", "QSPI_SCLK", "QSPI_SD0", "QSPI_SD1", "QSPI_SD2", "QSPI_SD3", "GND"]
    for i, net in enumerate(rp_nets):
        xx = 7900 if i < 20 else 10100
        yy = 1300 + (i if i < 20 else i - 20) * 180
        lines += [f'Text Label {xx} {yy} 0    45   ~ 0\n{net}', f'Wire Wire Line\n\t{xx} {yy} {xx + (250 if xx < 9000 else -250)} {yy}']
    lines += ['Text Notes 900 10300 0 70 ~ 14\nPOWER FLOW: USB-C VBUS -> BQ24074 IN; cell -> BAT; BQ24074 OUT -> SYS_RAW only.\nTPS63802 EN = diode-OR(VBUS, signal PMOS enabled by LOCATE or POWER_HOLD).\nUSB therefore sustains 3V3 while LCD_POWER_EN and GNSS_EN remain low.', 'Text Notes 900 10800 0 60 ~ 12\nAll reference passives, exact pin numbers, values, footprints and test points are captured in design.yaml, BOM and PCB.\nThis schematic is review source, not evidence of vendor/physical validation.', '$EndSCHEMATC']
    return "\n".join(lines) + "\n"


PROJECT = '''{\n  "board": {},\n  "cvpcb": {},\n  "erc": {},\n  "meta": {"filename": "maidenhead-pocket-locator.kicad_pro", "version": 1},\n  "net_settings": {"classes": [{"name": "Default", "clearance": 0.2, "track_width": 0.2, "via_diameter": 0.65, "via_drill": 0.3}, {"name": "POWER", "clearance": 0.2, "track_width": 0.55, "via_diameter": 0.8, "via_drill": 0.35}, {"name": "RF", "clearance": 0.25, "track_width": 0.45, "via_diameter": 0.7, "via_drill": 0.32}]},\n  "pcbnew": {},\n  "schematic": {},\n  "text_variables": {"REVISION": "A-electrical"}\n}\n'''


def main() -> None:
    (ROOT / "maidenhead-pocket-locator.sch").write_text(schematic_text(), encoding="utf-8")
    (ROOT / "maidenhead-pocket-locator.kicad_pcb").write_text(board_text(), encoding="utf-8")
    (ROOT / "maidenhead-pocket-locator.kicad_pro").write_text(PROJECT, encoding="utf-8")
    print("Generated connected Revision-A KiCad engineering sources.")


if __name__ == "__main__":
    main()
