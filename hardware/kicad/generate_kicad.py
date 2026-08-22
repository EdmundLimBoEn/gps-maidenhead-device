#!/usr/bin/env python3
"""Generate the Revision-A KiCad PCB from reviewed package and net data.

Run with the system Python shipped with KiCad.  The generated board embeds all
footprints, while retaining library identifiers for footprint integrity checks.

SPDX-License-Identifier: CERN-OHL-S-2.0
"""

from __future__ import annotations

import os
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path

try:
    import pcbnew
except ImportError:
    system_python = "/usr/bin/python3"
    if Path(system_python).is_file() and Path(sys.executable) != Path(system_python):
        os.execv(system_python, [system_python, __file__, *sys.argv[1:]])
    raise


ROOT = Path(__file__).resolve().parent
BOARD_PATH = ROOT / "maidenhead-pocket-locator.kicad_pcb"
SCHEMATIC_PATH = ROOT / "maidenhead-pocket-locator.sch"
CACHE_LIB_PATH = ROOT / "maidenhead-pocket-locator-cache.lib"
GLOBAL_LIB = Path("/usr/share/kicad/footprints")
LOCAL_LIB = ROOT / "PocketLocator.pretty"

NET_NAMES = [
    "GND", "VBUS_RAW", "VBUS", "USB_DP_CONN", "USB_DM_CONN",
    "USB_DP", "USB_DM", "CC1", "CC2", "BAT", "BAT_SENSE_SW", "SYS_RAW",
    "PWR_START_GATE", "PWR_START_OUT", "PWR_EN", "POWER_HOLD", "3V3", "1V1",
    "3V3_GNSS", "GNSS_EN", "GNSS_TX", "GNSS_RX", "GNSS_TX_U7", "GNSS_RX_U7", "GNSS_PPS", "GNSS_RF_50R",
    "LOCATE_RAW", "LCD_POWER_EN", "5V_LCD", "LCD_RS_3V3", "LCD_E_3V3", "LCD_D4_3V3",
    "LCD_D5_3V3", "LCD_D6_3V3", "LCD_D7_3V3", "LCD_RS", "LCD_E", "LCD_D4",
    "LCD_D5", "LCD_D6", "LCD_D7", "LCD_VO", "LCD_BL_A", "LCD_BL_K", "BL_PWM",
    "LOCATE_N", "OFF_N", "VBUS_PRESENT", "CHG_N", "CHG_LED_A", "RUN_N",
    "BOOTSEL_N", "SWDIO", "SWCLK", "XIN", "XOUT", "XOUT_XTAL", "QSPI_SCLK", "QSPI_SD0",
    "QSPI_SD1", "QSPI_SD2", "QSPI_SD3", "QSPI_CSN", "BB_SW1", "BB_SW2",
    "BB_FB", "LCD_SW", "LCD_FB", "CHG_TS", "CHG_ISET", "CHG_ILIM",
    "CHG_ITERM", "CHG_TMR", "BAT_ADC", "BAT_SENSE_EN", "BAT_SENSE_GATE",
]

TEST_POINTS = list(zip(
    ["VBUS", "BAT", "SYS_RAW", "3V3", "5V_LCD", "GND", "POWER_HOLD",
     "GNSS_TX", "GNSS_RX", "SWDIO", "SWCLK", "RUN_N", "BOOTSEL_N"],
    [(61, 15.5), (63.5, 15.5), (66, 15.5), (68.5, 15.5), (71, 15.5),
     (73.5, 15.5), (76, 15.5), (61, 18.5), (64, 18.5), (67, 18.5),
     (70, 18.5), (73, 18.5), (76, 18.5)],
))


@dataclass(frozen=True)
class Component:
    ref: str
    value: str
    library: str
    footprint: str
    x: float
    y: float
    angle: float
    pads: dict[str, str]


def c(ref: str, value: str, footprint_id: str, x: float, y: float,
      pads: dict[str, str], angle: float = 0) -> Component:
    library, footprint = footprint_id.split(":", 1)
    return Component(ref, value, library, footprint, x, y, angle, pads)


def two(ref: str, value: str, footprint_id: str, x: float, y: float,
        a: str, b: str, angle: float = 0) -> Component:
    return c(ref, value, footprint_id, x, y, {"1": a, "2": b}, angle)


R0402 = "Resistor_SMD:R_0402_1005Metric"
R0603 = "Resistor_SMD:R_0603_1608Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"


def components() -> list[Component]:
    parts: list[Component] = [
        c("J1", "USB4105-GF-A", "PocketLocator:USB4105-GF-A", 4.785, 14, {
            "A1": "GND", "A4": "VBUS_RAW", "A5": "CC1", "A6": "USB_DP_CONN", "A7": "USB_DM_CONN",
            "A9": "VBUS_RAW", "A12": "GND", "B1": "GND", "B4": "VBUS_RAW", "B5": "CC2",
            "B6": "USB_DP_CONN", "B7": "USB_DM_CONN", "B9": "VBUS_RAW", "B12": "GND", "S1": "GND",
        }, 90),
        two("F1", "MF-MSMF050-2", "Fuse:Fuse_1812_4532Metric", 8.0, 5.0, "VBUS_RAW", "VBUS", 90),
        two("RCC1", "5.1k", R0402, 10.2, 11.5, "CC1", "GND", 90),
        two("RCC2", "5.1k", R0402, 10.2, 16.5, "CC2", "GND", 90),
        c("D1", "TPD2EUSB30DRTR", "PocketLocator:Texas_DRT0003A", 10.2, 14.0, {
            "1": "USB_DP_CONN", "2": "USB_DM_CONN", "3": "GND",
        }),
        two("RUSB1", "27R", R0402, 28.0, 17.0, "USB_DP_CONN", "USB_DP"),
        two("RUSB2", "27R", R0402, 28.0, 18.5, "USB_DM_CONN", "USB_DM"),
        c("U3", "BQ24074RGTR", "PocketLocator:Texas_RGT0016C", 14.0, 28.5, {
            "1": "CHG_TS", "2": "BAT", "3": "BAT", "4": "GND", "5": "GND", "6": "VBUS",
            "8": "GND", "9": "CHG_N", "10": "SYS_RAW", "11": "SYS_RAW", "12": "CHG_ILIM",
            "13": "VBUS", "14": "CHG_TMR", "15": "CHG_ITERM", "16": "CHG_ISET", "17": "GND",
        }),
        two("CIN1", "1uF", C0603, 17.0, 25.5, "VBUS", "GND", 90),
        two("CBAT1", "4.7uF", C0603, 10.5, 29.0, "BAT", "GND", 90),
        two("COUT1", "4.7uF", C0603, 17.5, 28.5, "SYS_RAW", "GND", 90),
        two("RISET1", "2.20k", R0402, 11.0, 21.5, "CHG_ISET", "GND"),
        two("RILIM1", "2.00k", R0402, 13.0, 21.5, "CHG_ILIM", "GND"),
        two("RITERM1", "3.30k", R0402, 15.0, 21.5, "CHG_ITERM", "GND"),
        two("RTMR1", "48.7k", R0402, 17.0, 21.5, "CHG_TMR", "GND"),
        two("RVB1", "82k", R0402, 10.5, 23.5, "VBUS", "VBUS_PRESENT"),
        two("RVB2", "100k", R0402, 12.5, 23.5, "VBUS_PRESENT", "GND"),
        c("J2", "B3B-PH-K-S(LF)(SN)", "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical", 14.0, 34.0,
          {"1": "BAT", "2": "CHG_TS", "3": "GND"}),
        two("TH1", "10k NTC DNP", R0603, 29.0, 35.0, "CHG_TS", "GND"),
        two("RCHG1", "1k", R0402, 6.0, 24.0, "3V3", "CHG_LED_A"),
        two("RCHGPU1", "100k", R0402, 8.0, 22.0, "3V3", "CHG_N"),
        c("LED1", "KP-2012EC", "LED_SMD:LED_0805_2012Metric", 7.5, 27.0,
          {"1": "CHG_N", "2": "CHG_LED_A"}, 90),
        c("Q1", "DMP3098L-7", SOT23, 20.5, 30.0,
          {"1": "PWR_START_GATE", "2": "SYS_RAW", "3": "PWR_START_OUT"}),
        c("Q2", "DMN2050L-7", SOT23, 24.5, 30.0,
          {"1": "POWER_HOLD", "2": "GND", "3": "PWR_START_GATE"}),
        two("RSTART1", "100k", R0402, 22.0, 35.0, "SYS_RAW", "PWR_START_GATE"),
        two("REN1", "1M", R0402, 24.0, 33.0, "PWR_EN", "GND"),
        two("D2", "BAT54H", "Diode_SMD:D_SOD-323", 19.5, 19.5, "PWR_EN", "VBUS"),
        two("D3", "1N4148WS", "Diode_SMD:D_SOD-323", 22.5, 26.5, "LOCATE_RAW", "PWR_START_GATE"),
        two("D5", "1N4148WS", "Diode_SMD:D_SOD-323", 21.5, 23.5, "LOCATE_RAW", "LOCATE_N"),
        two("D4", "BAT54H", "Diode_SMD:D_SOD-323", 25.0, 23.5, "PWR_EN", "PWR_START_OUT"),
        two("RHOLD1", "100k", R0402, 25.0, 35.0, "POWER_HOLD", "GND"),
        c("U4", "TPS63802DLAR", "PocketLocator:Texas_DLA0010A", 29.0, 30.0, {
            "1": "PWR_EN", "2": "GND", "3": "GND", "4": "BB_FB", "6": "3V3",
            "7": "BB_SW2", "8": "GND", "9": "BB_SW1", "10": "SYS_RAW",
        }),
        two("LBB1", "XFL4020-471MEC", "Inductor_SMD:L_Coilcraft_XxL4020", 32.8, 30.0, "BB_SW1", "BB_SW2"),
        two("CBBIN1", "10uF", C0805, 28.5, 26.5, "SYS_RAW", "GND", 270),
        two("CBBOUT1", "22uF", C0805, 35.5, 34.0, "3V3", "GND", 90),
        two("RBB1", "511k", R0402, 27.5, 33.0, "3V3", "BB_FB"),
        two("RBB2", "91k", R0402, 29.5, 33.0, "BB_FB", "GND"),
    ]

    rp = {str(pin): "3V3" for pin in (1, 10, 22, 33, 42, 43, 44, 48, 49)}
    rp.update({str(pin): "1V1" for pin in (23, 45, 50)})
    rp.update({
        "4": "LOCATE_N", "5": "OFF_N", "6": "POWER_HOLD", "7": "LCD_POWER_EN",
        "8": "LCD_RS_3V3", "9": "LCD_E_3V3", "11": "LCD_D4_3V3", "12": "LCD_D5_3V3",
        "13": "LCD_D6_3V3", "14": "LCD_D7_3V3", "15": "BL_PWM", "19": "GND",
        "20": "XIN", "21": "XOUT", "24": "SWCLK", "25": "SWDIO", "26": "RUN_N",
        "27": "GNSS_RX", "28": "GNSS_TX", "29": "GNSS_EN", "30": "VBUS_PRESENT",
        "31": "CHG_N", "32": "BAT_SENSE_EN", "38": "BAT_ADC", "46": "USB_DM",
        "47": "USB_DP", "51": "QSPI_SD3", "52": "QSPI_SCLK", "53": "QSPI_SD0",
        "54": "QSPI_SD2", "55": "QSPI_SD1", "56": "QSPI_CSN", "57": "GND",
    })
    parts.append(c("U1", "RP2040", "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm", 35.0, 18.0, rp))

    decoupling_xy = [(30.0, 15.4), (30.0, 19.0), (40.0, 24.5), (40.0, 19.0),
                     (41.0, 17.0), (39.2, 12.2), (37.7, 12.2), (36.2, 12.2), (30.0, 12.5)]
    for index, (x, y) in enumerate(decoupling_xy, 1):
        parts.append(two(f"C{index}", "100nF", C0402, x, y, "3V3", "GND", 90))
    parts += [
        two("CVREG1", "1uF", C0603, 37.8, 9.5, "1V1", "GND", 90),
        two("CDV1", "100nF", C0402, 40.5, 22.5, "1V1", "GND"),
        two("CDV2", "100nF", C0402, 32.6, 13.0, "1V1", "GND"),
        two("CADC1", "1uF", C0603, 41.0, 14.0, "3V3", "GND", 90),
        two("RRESET1", "100k", R0402, 42.0, 24.5, "3V3", "RUN_N"),
        two("CRESET1", "100nF", C0402, 44.0, 24.5, "RUN_N", "GND"),
        c("X1", "ABM8-272-T3", "Crystal:Crystal_SMD_Abracon_ABM8G-4Pin_3.2x2.5mm", 34.2, 25.0,
          {"1": "XIN", "2": "GND", "3": "XOUT_XTAL", "4": "GND"}),
        two("CX1", "15pF", C0402, 31.2, 24.5, "XIN", "GND", 90),
        two("CX2", "15pF", C0402, 37.2, 24.5, "XOUT_XTAL", "GND", 90),
        two("RXTAL1", "1k", R0402, 38.5, 23.0, "XOUT", "XOUT_XTAL"),
        c("U2", "W25Q16JVUXIQ", "PocketLocator:Winbond_UX_8", 33.8, 10.5, {
            "1": "QSPI_CSN", "2": "QSPI_SD1", "3": "QSPI_SD2", "4": "GND", "5": "QSPI_SD0",
            "6": "QSPI_SCLK", "7": "QSPI_SD3", "8": "3V3",
        }, 90),
        two("CFLASH1", "100nF", C0402, 33.0, 8.2, "3V3", "GND", 90),
        two("RBOOT1", "1k", R0402, 30.5, 10.5, "QSPI_CSN", "BOOTSEL_N"),
        c("SW3", "EVQ-P7A01P", "Button_Switch_SMD:SW_SPST_EVQP7A", 50.5, 19.0,
          {"1": "BOOTSEL_N", "2": "GND"}, 90),
        c("SW4", "EVQ-P7A01P", "Button_Switch_SMD:SW_SPST_EVQP7A", 56.5, 19.0,
          {"1": "RUN_N", "2": "GND"}, 90),
        c("Q4", "DMP3098L-7", SOT23, 38.5, 30.0,
          {"1": "BAT_SENSE_GATE", "2": "BAT", "3": "BAT_SENSE_SW"}),
        c("Q5", "DMN2050L-7", SOT23, 42.5, 30.0,
          {"1": "BAT_SENSE_EN", "2": "GND", "3": "BAT_SENSE_GATE"}),
        two("RBATG1", "100k", R0402, 39.0, 33.0, "BAT", "BAT_SENSE_GATE"),
        two("RSENSEEN1", "100k", R0402, 46.0, 33.0, "BAT_SENSE_EN", "GND"),
        two("RBAT1", "100k", R0402, 46.0, 25.5, "BAT_SENSE_SW", "BAT_ADC"),
        two("RBAT2", "100k", R0402, 47.0, 28.0, "BAT_ADC", "GND"),
        two("CBATADC1", "100nF", C0402, 49.0, 28.0, "BAT_ADC", "GND"),
        c("U8", "TPS22916BYFPR", "PocketLocator:Texas_YFP0004", 73.5, 27.2,
          {"A1": "3V3_GNSS", "A2": "3V3", "B1": "GND", "B2": "GNSS_EN"}),
        two("CGIN1", "1uF", C0402, 76.0, 22.0, "3V3", "GND"),
        two("CGOUT1", "4.7uF", C0603, 72.0, 29.5, "3V3_GNSS", "GND"),
        two("RGNSSEN1", "100k", R0402, 74.5, 31.5, "GNSS_EN", "GND"),
        c("U7", "Ai-Thinker GP-02", "PocketLocator:GP-02", 64.5, 29.0, {
            "1": "GND", "2": "GNSS_TX_U7", "3": "GNSS_RX_U7", "4": "GNSS_PPS",
            "8": "3V3_GNSS", "10": "GND", "11": "GNSS_RF_50R", "12": "GND",
        }, 270),
        c("J4", "Hirose 20449-001E", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", 55.0, 25.64,
          {"1": "GNSS_RF_50R", "2": "GND"}),
        two("CGNSS1", "100nF", C0402, 71.3, 25.8, "3V3_GNSS", "GND"),
        two("CGNSS2", "820pF", C0402, 73.2, 24.5, "3V3_GNSS", "GND"),
        two("CGNSS3", "10uF", C0805, 71.5, 21.5, "3V3_GNSS", "GND"),
        two("RGNSSTX1", "33R", R0402, 71.5, 32.3, "GNSS_TX_U7", "GNSS_TX"),
        two("RGNSSRX1", "33R", R0402, 71.5, 30.8, "GNSS_RX", "GNSS_RX_U7"),
        c("U5", "TPS61023DRLR", "Package_TO_SOT_SMD:SOT-563", 16.0, 7.0, {
            "1": "LCD_FB", "2": "LCD_POWER_EN", "3": "SYS_RAW", "4": "GND", "5": "LCD_SW", "6": "5V_LCD",
        }),
        two("LLCD1", "LQH2MCN1R0M02L", "Inductor_SMD:L_0805_2012Metric", 19.2, 7.0, "SYS_RAW", "LCD_SW"),
        two("CLCDIN1", "10uF", C0805, 12.8, 7.0, "SYS_RAW", "GND"),
        two("CLCDO1", "10uF", C0805, 22.5, 5.0, "5V_LCD", "GND"),
        two("CLCDO2", "10uF", C0805, 20.5, 10.0, "5V_LCD", "GND"),
        two("RLCD1", "909k", R0402, 13.0, 4.5, "5V_LCD", "LCD_FB"),
        two("RLCD2", "100k", R0402, 13.0, 10.0, "LCD_FB", "GND"),
        two("RLCDEN1", "100k", R0402, 16.0, 10.0, "LCD_POWER_EN", "GND"),
        c("U6", "SN74LVC8T245PWR", "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", 47.0, 9.0, {
            "1": "3V3", "2": "3V3", "3": "LCD_RS_3V3", "4": "LCD_E_3V3", "5": "LCD_D4_3V3",
            "6": "LCD_D5_3V3", "7": "LCD_D6_3V3", "8": "LCD_D7_3V3", "9": "GND", "10": "GND", "11": "GND", "12": "GND",
            "13": "GND", "16": "LCD_D7", "17": "LCD_D6", "18": "LCD_D5", "19": "LCD_D4",
            "20": "LCD_E", "21": "LCD_RS", "22": "GND", "23": "5V_LCD", "24": "5V_LCD",
        }, 90),
        two("CULS1", "100nF", C0402, 39.0, 6.0, "3V3", "GND"),
        two("CULD1", "100nF", C0402, 53.0, 6.0, "5V_LCD", "GND"),
        two("RVO1", "4.7k", R0402, 53.0, 7.0, "5V_LCD", "LCD_VO"),
        two("RVO2", "560R", R0402, 55.0, 7.0, "LCD_VO", "GND"),
        c("Q3", "DMN2050L-7", SOT23, 58.0, 9.0, {"1": "BL_PWM", "2": "GND", "3": "LCD_BL_K"}),
        two("RBL1", "68R", R0603, 62.0, 6.0, "5V_LCD", "LCD_BL_A"),
        c("J3", "61301611121", "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical", 21.45, 2.2, {
            "1": "GND", "2": "5V_LCD", "3": "LCD_VO", "4": "LCD_RS", "5": "GND", "6": "LCD_E",
            "7": "GND", "8": "GND", "9": "GND", "10": "GND", "11": "LCD_D4", "12": "LCD_D5",
            "13": "LCD_D6", "14": "LCD_D7", "15": "LCD_BL_A", "16": "LCD_BL_K",
        }, 90),
        c("SW1", "TL1014BF160QG", "PocketLocator:SW_TL1014B", 78.25, 10.0,
          {"1": "LOCATE_RAW", "2": "GND", "3": "LOCATE_RAW", "4": "GND"}, 270),
        c("SW2", "TL1014BF160QG", "PocketLocator:SW_TL1014B", 78.25, 27.0,
          {"1": "OFF_N", "2": "GND", "3": "OFF_N", "4": "GND"}, 270),
        two("RLOC1", "100k", R0402, 73.0, 10.0, "3V3", "LOCATE_N"),
        two("ROFF1", "100k", R0402, 52.0, 33.0, "3V3", "OFF_N"),
    ]

    for index, (net, (x, y)) in enumerate(TEST_POINTS, 1):
        parts.append(c(f"TP{index}", net, "TestPoint:TestPoint_Pad_D1.5mm", x, y, {"1": net}))

    for index, (x, y) in enumerate(((3, 3), (78, 3), (3, 34), (78, 34)), 1):
        parts.append(c(f"H{index}", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5", x, y, {}))
    return parts


def load_footprint(component: Component):
    base = LOCAL_LIB if component.library == "PocketLocator" else GLOBAL_LIB / f"{component.library}.pretty"
    footprint = pcbnew.FootprintLoad(str(base), component.footprint)
    if footprint is None:
        raise RuntimeError(f"cannot load {component.library}:{component.footprint}")
    footprint.SetFPID(pcbnew.LIB_ID(component.library, component.footprint))
    footprint.SetReference(component.ref)
    footprint.SetValue(component.value)
    footprint.SetPosition(pcbnew.VECTOR2I_MM(component.x, component.y))
    footprint.SetOrientationDegrees(component.angle)
    is_test_point = component.ref.startswith("TP")
    footprint.Reference().SetVisible(is_test_point)
    if is_test_point:
        index = int(component.ref[2:])
        offset = -1.5 if index <= 7 else 2.0
        footprint.Reference().SetPosition(pcbnew.VECTOR2I_MM(component.x, component.y + offset))
        footprint.Reference().SetLayer(pcbnew.B_SilkS)
        footprint.Reference().SetTextSize(pcbnew.VECTOR2I_MM(0.8, 0.8))
        footprint.Reference().SetTextThickness(pcbnew.FromMM(0.12))
    footprint.Value().SetVisible(False)
    return footprint


def add_edge(board, x1: float, y1: float, x2: float, y2: float) -> None:
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetStart(pcbnew.VECTOR2I_MM(x1, y1))
    edge.SetEnd(pcbnew.VECTOR2I_MM(x2, y2))
    edge.SetWidth(pcbnew.FromMM(0.1))
    board.Add(edge)


def add_text(board, value: str, x: float, y: float, layer: int, angle: float = 0,
             size: float = 0.9) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    item.SetLayer(layer)
    item.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    item.SetTextThickness(pcbnew.FromMM(max(0.10, size * 0.15)))
    item.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    board.Add(item)


def generate_board() -> None:
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    default_class = board.GetDesignSettings().m_NetSettings.m_DefaultNetClass
    default_class.SetClearance(pcbnew.FromMM(0.10))
    default_class.SetTrackWidth(pcbnew.FromMM(0.15))
    default_class.SetViaDiameter(pcbnew.FromMM(0.50))
    default_class.SetViaDrill(pcbnew.FromMM(0.20))
    board.GetDesignSettings().m_MinThroughDrill = pcbnew.FromMM(0.20)
    nets = {}
    for name in NET_NAMES:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net

    classes = {
        "Power": (0.50, 0.15, ["VBUS_RAW", "VBUS", "BAT", "SYS_RAW", "3V3", "3V3_GNSS", "5V_LCD"]),
        "USB_90R": (0.22, 0.15, ["USB_DP_CONN", "USB_DM_CONN", "USB_DP", "USB_DM"]),
        "RF_50R": (0.45, 0.20, ["GNSS_RF_50R"]),
    }
    for class_name, (width, clearance, members) in classes.items():
        net_class = pcbnew.NETCLASS(class_name)
        net_class.SetTrackWidth(pcbnew.FromMM(width))
        net_class.SetClearance(pcbnew.FromMM(clearance))
        net_class.SetViaDiameter(pcbnew.FromMM(0.60))
        net_class.SetViaDrill(pcbnew.FromMM(0.30))
        if class_name == "USB_90R":
            net_class.SetDiffPairWidth(pcbnew.FromMM(width))
            net_class.SetDiffPairGap(pcbnew.FromMM(0.15))
        board.GetDesignSettings().m_NetSettings.m_NetClasses[class_name] = net_class
        for name in members:
            nets[name].SetNetClass(net_class)

    for spec in components():
        footprint = load_footprint(spec)
        known = {pad.GetNumber() for pad in footprint.Pads()}
        unknown = sorted(set(spec.pads) - known)
        if unknown:
            raise ValueError(f"{spec.ref}: footprint lacks pads {unknown}; has {sorted(known)}")
        for pad in footprint.Pads():
            net_name = spec.pads.get(pad.GetNumber())
            if net_name:
                pad.SetNet(nets[net_name])
        board.Add(footprint)

    add_edge(board, 0, 0, 81, 0)
    add_edge(board, 81, 0, 81, 37)
    add_edge(board, 81, 37, 0, 37)
    add_edge(board, 0, 37, 0, 0)
    add_text(board, "MAIDENHEAD POCKET LOCATOR REV A", 40.5, 35.7, pcbnew.B_SilkS)
    add_text(board, "LOCATE", 75.0, 10.0, pcbnew.F_SilkS, 90)
    add_text(board, "OFF", 75.0, 27.0, pcbnew.F_SilkS, 90)
    for layer, plane_net in ((pcbnew.F_Cu, "GND"), (pcbnew.In1_Cu, "GND"),
                             (pcbnew.In2_Cu, "3V3"), (pcbnew.B_Cu, "GND")):
        zone = pcbnew.ZONE(board)
        zone.SetNet(nets[plane_net])
        zone.SetLayerSet(pcbnew.LSET(layer))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        outline = zone.Outline()
        outline.NewOutline()
        for x, y in ((0.25, 0.25), (80.75, 0.25), (80.75, 36.75), (0.25, 36.75)):
            outline.Append(pcbnew.VECTOR2I_MM(x, y))
        board.Add(zone)
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Generated {BOARD_PATH.relative_to(ROOT.parent.parent)} with {len(board.GetFootprints())} footprints")


def _legacy_field(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', "'")


def generate_schematic() -> None:
    """Write an exact, machine-checkable legacy Eeschema netlist schematic.

    Every physical pad is represented by its actual footprint pad number. Pins
    not assigned in the board contract are explicitly marked no-connect. The
    generated cache library keeps the source portable across KiCad installs.
    """
    specs = [spec for spec in components() if not spec.ref.startswith("H")]
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    footprints_by_ref = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    library = ["EESchema-LIBRARY Version 2.4", "#encoding utf-8"]
    schematic = [
        "EESchema Schematic File Version 4",
        "LIBS:maidenhead-pocket-locator-cache",
        "EELAYER 29 0",
        "EELAYER END",
        "$Descr A0 46811 33110",
        'Sheet 1 1',
        'Title "Maidenhead Pocket Locator — exact Revision A netlist"',
        'Date "2026-08-21"',
        'Rev "A electrical"',
        'Comp "Open hardware — CERN-OHL-S-2.0"',
        'Comment1 "Generated from the same component/pad contract as the PCB"',
        "$EndDescr",
        "Text Notes 700 500 0 100 ~ 20",
        "EXACT PAD-NUMBER NETLIST — all unassigned physical pads are explicit no-connects",
    ]
    placed = []
    for index, spec in enumerate(specs):
        footprint = footprints_by_ref.get(spec.ref)
        if footprint is None:
            raise RuntimeError(f"authoritative PCB lacks footprint {spec.ref}")
        pad_numbers = sorted({pad.GetNumber() for pad in footprint.Pads() if pad.GetNumber()},
                             key=lambda number: (not number.isdigit(), int(number) if number.isdigit() else number))
        symbol = f"PL_{spec.ref}"
        prefix = next((character for character in spec.ref if character.isalpha()), "U")
        height = max(150, 25 * max(1, len(pad_numbers)))
        library += [
            "#", f"# {symbol}", "#",
            f"DEF {symbol} {prefix} 0 40 Y Y 1 F N",
            f'F0 "{prefix}" 0 {-height - 100} 50 H V C CNN',
            f'F1 "{symbol}" 0 {height + 100} 50 H V C CNN',
            "DRAW", f"S -300 {height} 300 {-height} 0 1 10 f",
        ]
        for pin_index, pad_number in enumerate(pad_numbers):
            pin_y = (len(pad_numbers) - 1 - 2 * pin_index) * 25
            net_name = spec.pads.get(pad_number)
            pin_name = net_name or "NC"
            pin_type = "B" if net_name else "N"
            library.append(f"X {pin_name} {pad_number} -500 {pin_y} 200 R 35 35 1 1 {pin_type}")
        library += ["ENDDRAW", "ENDDEF"]

        # A wide A0 grid keeps every pin stub isolated, including the RP2040's
        # 57-pin symbol. Overlapping generated symbols can silently merge nets
        # when KiCad converts this portable legacy source to the modern format.
        x = 2500 + (index % 12) * 3800
        y = 2400 + (index // 12) * 3200
        timestamp = f"A{index + 1:07X}"
        schematic += [
            "$Comp", f"L {symbol} {spec.ref}", f"U 1 1 {timestamp}", f"P {x} {y}",
            f'F 0 "{spec.ref}" H {x + 450} {y - 100} 50  0000 L CNN',
            f'F 1 "{_legacy_field(spec.value)}" H {x + 450} {y} 50  0000 L CNN',
            f'F 2 "{spec.library}:{spec.footprint}" H {x} {y} 50  0001 C CNN',
            f"\t1    {x} {y}", "\t1 0 0 -1", "$EndComp",
        ]
        for pin_index, pad_number in enumerate(pad_numbers):
            # The component transform mirrors library Y into sheet Y.
            pin_y = y - (len(pad_numbers) - 1 - 2 * pin_index) * 25
            net_name = spec.pads.get(pad_number)
            if net_name:
                schematic += [
                    "Wire Wire Line", f"\t{x - 500} {pin_y} {x - 800} {pin_y}",
                    f"Text Label {x - 800} {pin_y} 2    35   ~ 0", net_name,
                ]
            else:
                schematic.append(f"NoConn ~ {x - 500} {pin_y}")
        placed.append((spec.ref, pad_numbers))
    library += ["#", "#End Library"]
    schematic += [
        "Text Notes 700 32500 0 55 ~ 11",
        "BQ24074 OUT is the sole SYS_RAW source. J1 VBUS_RAW passes through F1 to VBUS.",
        "$EndSCHEMATC",
    ]
    CACHE_LIB_PATH.write_text("\n".join(library) + "\n", encoding="utf-8")
    SCHEMATIC_PATH.write_text("\n".join(schematic) + "\n", encoding="utf-8")
    print(f"Generated exact schematic contract for {len(placed)} electrical footprints")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force-placement",
        action="store_true",
        help="replace the authoritative PCB with the generated unrouted placement",
    )
    args = parser.parse_args()
    if args.force_placement:
        generate_board()
    else:
        print(f"Preserved authoritative PCB: {BOARD_PATH.relative_to(ROOT.parent.parent)}")
    generate_schematic()
