EESchema Schematic File Version 4
LIBS:power
LIBS:Device
LIBS:Connector_Generic
EELAYER 29 0
EELAYER END
$Descr A3 16535 11693
Sheet 1 1
Title "Maidenhead Pocket Locator — connected Revision A"
Date "2026-08-19"
Rev "A electrical"
Comp "Open hardware — CERN-OHL-S-2.0"
Comment1 "Do not fabricate until exact GP-02/LCD/cell footprints and physical validation pass"
$EndDescr
Text Notes 700 650 0 110 ~ 22
USB-C / BQ24074 POWER PATH
Text Notes 4200 650 0 110 ~ 22
TPS63802 ENABLE LATCH / 3V3
Text Notes 7900 650 0 110 ~ 22
RP2040 / FLASH / USB
Text Notes 12200 650 0 110 ~ 22
GNSS / LCD
$Comp
L Connector_Generic:Conn_01x06 J1
U 1 1 J1
P 1200 1800
F 0 "J1" H 1450 1900 50  0000 C CNN
F 1 "USB-C: VBUS,CC1,CC2,D+,D-,GND" H 1550 1700 50  0000 C CNN
	1    1200 1800
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x14 U3
U 1 1 U3
P 2600 2100
F 0 "U3" H 2850 2200 50  0000 C CNN
F 1 "BQ24074: IN,BAT,TS,EN2,EN1,TMR,CE,CHG,OUT,ILIM,ISET,PGOOD,ITERM,GND" H 2950 2000 50  0000 C CNN
	1    2600 2100
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x03 J2
U 1 1 J2
P 1100 4300
F 0 "J2" H 1350 4400 50  0000 C CNN
F 1 "BAT+,NTC,GND" H 1450 4200 50  0000 C CNN
	1    1100 4300
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x03 Q1
U 1 1 Q1
P 4700 1600
F 0 "Q1" H 4950 1700 50  0000 C CNN
F 1 "DMP3098L signal PMOS" H 5050 1500 50  0000 C CNN
	1    4700 1600
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x03 Q2
U 1 1 Q2
P 4700 2500
F 0 "Q2" H 4950 2600 50  0000 C CNN
F 1 "DMN2050L hold NMOS" H 5050 2400 50  0000 C CNN
	1    4700 2500
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x09 U4
U 1 1 U4
P 6100 2100
F 0 "U4" H 6350 2200 50  0000 C CNN
F 1 "TPS63802: VIN,L1,L2,VOUT,FB,EN,MODE,PG,GND" H 6450 2000 50  0000 C CNN
	1    6100 2100
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_02x20_Odd_Even U1
U 1 1 U1
P 9000 2600
F 0 "U1" H 9250 2700 50  0000 C CNN
F 1 "RP2040 QFN56 — see pin map" H 9350 2500 50  0000 C CNN
	1    9000 2600
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x08 U2
U 1 1 U2
P 10600 1900
F 0 "U2" H 10850 2000 50  0000 C CNN
F 1 "W25Q16: CS,DO,WP,GND,DI,CLK,HOLD,VCC" H 10950 1800 50  0000 C CNN
	1    10600 1900
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x06 U8
U 1 1 U8
P 12500 1600
F 0 "U8" H 12750 1700 50  0000 C CNN
F 1 "TPS22916 GNSS load switch" H 12850 1500 50  0000 C CNN
	1    12500 1600
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x06 U7
U 1 1 U7
P 14000 1700
F 0 "U7" H 14250 1800 50  0000 C CNN
F 1 "GP-02: VCC,GND,TX,RX,PPS,RF" H 14350 1600 50  0000 C CNN
	1    14000 1700
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x06 U5
U 1 1 U5
P 12400 4500
F 0 "U5" H 12650 4600 50  0000 C CNN
F 1 "TPS61023: FB,EN,VIN,GND,SW,VOUT" H 12750 4400 50  0000 C CNN
	1    12400 4500
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_02x12_Odd_Even U6
U 1 1 U6
P 14000 4800
F 0 "U6" H 14250 4900 50  0000 C CNN
F 1 "SN74LVC8T245: VCCA/A0-A5/DIR/OE/B0-B5/VCCB/GND" H 14350 4700 50  0000 C CNN
	1    14000 4800
	1 0 0 -1
$EndComp

$Comp
L Connector_Generic:Conn_01x16 J3
U 1 1 J3
P 15300 5000
F 0 "J3" H 15550 5100 50  0000 C CNN
F 1 "LCD: GND,5V,VO,RS,RW,E,D0-D7,BL+,BL-" H 15650 4900 50  0000 C CNN
	1    15300 5000
	1 0 0 -1
$EndComp

Wire Wire Line
	1100 1550 850 1550
Text Label 850 1550 2    45   ~ 0
VBUS
Wire Wire Line
	1100 1650 850 1650
Text Label 850 1650 2    45   ~ 0
CC1
Wire Wire Line
	1100 1750 850 1750
Text Label 850 1750 2    45   ~ 0
CC2
Wire Wire Line
	1100 1850 850 1850
Text Label 850 1850 2    45   ~ 0
USB_DP_CONN
Wire Wire Line
	1100 1950 850 1950
Text Label 850 1950 2    45   ~ 0
USB_DM_CONN
Wire Wire Line
	1100 2050 850 2050
Text Label 850 2050 2    45   ~ 0
GND
Wire Wire Line
	2500 1450 2250 1450
Text Label 2250 1450 2    45   ~ 0
VBUS
Wire Wire Line
	2500 1550 2250 1550
Text Label 2250 1550 2    45   ~ 0
BAT
Wire Wire Line
	2500 1650 2250 1650
Text Label 2250 1650 2    45   ~ 0
CHG_TS
Wire Wire Line
	2500 1750 2250 1750
Text Label 2250 1750 2    45   ~ 0
GND
Wire Wire Line
	2500 1850 2250 1850
Text Label 2250 1850 2    45   ~ 0
VBUS
Wire Wire Line
	2500 1950 2250 1950
Text Label 2250 1950 2    45   ~ 0
CHG_TMR
Wire Wire Line
	2500 2050 2250 2050
Text Label 2250 2050 2    45   ~ 0
GND
Wire Wire Line
	2500 2150 2250 2150
Text Label 2250 2150 2    45   ~ 0
CHG_N
Wire Wire Line
	2500 2250 2250 2250
Text Label 2250 2250 2    45   ~ 0
SYS_RAW
Wire Wire Line
	2500 2350 2250 2350
Text Label 2250 2350 2    45   ~ 0
CHG_ILIM
Wire Wire Line
	2500 2450 2250 2450
Text Label 2250 2450 2    45   ~ 0
CHG_ISET
Wire Wire Line
	2500 2550 2250 2550
Text Label 2250 2550 2    45   ~ 0
VBUS_PRESENT
Wire Wire Line
	2500 2650 2250 2650
Text Label 2250 2650 2    45   ~ 0
CHG_ITERM
Wire Wire Line
	2500 2750 2250 2750
Text Label 2250 2750 2    45   ~ 0
GND
Wire Wire Line
	1000 4200 750 4200
Text Label 750 4200 2    45   ~ 0
BAT
Wire Wire Line
	1000 4300 750 4300
Text Label 750 4300 2    45   ~ 0
CHG_TS
Wire Wire Line
	1000 4400 750 4400
Text Label 750 4400 2    45   ~ 0
GND
Wire Wire Line
	4600 1500 4350 1500
Text Label 4350 1500 2    45   ~ 0
PWR_START_GATE
Wire Wire Line
	4600 1600 4350 1600
Text Label 4350 1600 2    45   ~ 0
PWR_START_OUT
Wire Wire Line
	4600 1700 4350 1700
Text Label 4350 1700 2    45   ~ 0
SYS_RAW
Wire Wire Line
	4600 2400 4350 2400
Text Label 4350 2400 2    45   ~ 0
POWER_HOLD
Wire Wire Line
	4600 2500 4350 2500
Text Label 4350 2500 2    45   ~ 0
GND
Wire Wire Line
	4600 2600 4350 2600
Text Label 4350 2600 2    45   ~ 0
PWR_START_GATE
Wire Wire Line
	6000 1700 5750 1700
Text Label 5750 1700 2    45   ~ 0
SYS_RAW
Wire Wire Line
	6000 1800 5750 1800
Text Label 5750 1800 2    45   ~ 0
BB_SW1
Wire Wire Line
	6000 1900 5750 1900
Text Label 5750 1900 2    45   ~ 0
BB_SW2
Wire Wire Line
	6000 2000 5750 2000
Text Label 5750 2000 2    45   ~ 0
3V3
Wire Wire Line
	6000 2100 5750 2100
Text Label 5750 2100 2    45   ~ 0
BB_FB
Wire Wire Line
	6000 2200 5750 2200
Text Label 5750 2200 2    45   ~ 0
PWR_EN
Wire Wire Line
	6000 2300 5750 2300
Text Label 5750 2300 2    45   ~ 0
GND
Wire Wire Line
	6000 2400 5750 2400
Text Label 5750 2400 2    45   ~ 0
3V3
Wire Wire Line
	6000 2500 5750 2500
Text Label 5750 2500 2    45   ~ 0
GND
Wire Wire Line
	10500 1550 10250 1550
Text Label 10250 1550 2    45   ~ 0
QSPI_CSN
Wire Wire Line
	10500 1650 10250 1650
Text Label 10250 1650 2    45   ~ 0
QSPI_SD1
Wire Wire Line
	10500 1750 10250 1750
Text Label 10250 1750 2    45   ~ 0
QSPI_SD2
Wire Wire Line
	10500 1850 10250 1850
Text Label 10250 1850 2    45   ~ 0
GND
Wire Wire Line
	10500 1950 10250 1950
Text Label 10250 1950 2    45   ~ 0
QSPI_SD0
Wire Wire Line
	10500 2050 10250 2050
Text Label 10250 2050 2    45   ~ 0
QSPI_SCLK
Wire Wire Line
	10500 2150 10250 2150
Text Label 10250 2150 2    45   ~ 0
QSPI_SD3
Wire Wire Line
	10500 2250 10250 2250
Text Label 10250 2250 2    45   ~ 0
3V3
Wire Wire Line
	12400 1350 12150 1350
Text Label 12150 1350 2    45   ~ 0
3V3
Wire Wire Line
	12400 1450 12150 1450
Text Label 12150 1450 2    45   ~ 0
GND
Wire Wire Line
	12400 1550 12150 1550
Text Label 12150 1550 2    45   ~ 0
GNSS_EN
Wire Wire Line
	12400 1650 12150 1650
Text Label 12150 1650 2    45   ~ 0
3V3_GNSS
Wire Wire Line
	12400 1750 12150 1750
Text Label 12150 1750 2    45   ~ 0
3V3_GNSS
Wire Wire Line
	12400 1850 12150 1850
Text Label 12150 1850 2    45   ~ 0
GND
Wire Wire Line
	13900 1450 13650 1450
Text Label 13650 1450 2    45   ~ 0
3V3_GNSS
Wire Wire Line
	13900 1550 13650 1550
Text Label 13650 1550 2    45   ~ 0
GND
Wire Wire Line
	13900 1650 13650 1650
Text Label 13650 1650 2    45   ~ 0
GNSS_TX
Wire Wire Line
	13900 1750 13650 1750
Text Label 13650 1750 2    45   ~ 0
GNSS_RX
Wire Wire Line
	13900 1850 13650 1850
Text Label 13650 1850 2    45   ~ 0
GNSS_PPS
Wire Wire Line
	13900 1950 13650 1950
Text Label 13650 1950 2    45   ~ 0
GNSS_RF_50R
Wire Wire Line
	12300 4250 12050 4250
Text Label 12050 4250 2    45   ~ 0
LCD_FB
Wire Wire Line
	12300 4350 12050 4350
Text Label 12050 4350 2    45   ~ 0
LCD_POWER_EN
Wire Wire Line
	12300 4450 12050 4450
Text Label 12050 4450 2    45   ~ 0
SYS_RAW
Wire Wire Line
	12300 4550 12050 4550
Text Label 12050 4550 2    45   ~ 0
GND
Wire Wire Line
	12300 4650 12050 4650
Text Label 12050 4650 2    45   ~ 0
LCD_SW
Wire Wire Line
	12300 4750 12050 4750
Text Label 12050 4750 2    45   ~ 0
5V_LCD
Wire Wire Line
	15200 4250 14950 4250
Text Label 14950 4250 2    45   ~ 0
GND
Wire Wire Line
	15200 4350 14950 4350
Text Label 14950 4350 2    45   ~ 0
5V_LCD
Wire Wire Line
	15200 4450 14950 4450
Text Label 14950 4450 2    45   ~ 0
LCD_VO
Wire Wire Line
	15200 4550 14950 4550
Text Label 14950 4550 2    45   ~ 0
LCD_RS
Wire Wire Line
	15200 4650 14950 4650
Text Label 14950 4650 2    45   ~ 0
GND
Wire Wire Line
	15200 4750 14950 4750
Text Label 14950 4750 2    45   ~ 0
LCD_E
Wire Wire Line
	15200 4850 14950 4850
Text Label 14950 4850 2    45   ~ 0
GND
Wire Wire Line
	15200 4950 14950 4950
Text Label 14950 4950 2    45   ~ 0
GND
Wire Wire Line
	15200 5050 14950 5050
Text Label 14950 5050 2    45   ~ 0
GND
Wire Wire Line
	15200 5150 14950 5150
Text Label 14950 5150 2    45   ~ 0
GND
Wire Wire Line
	15200 5250 14950 5250
Text Label 14950 5250 2    45   ~ 0
LCD_D4
Wire Wire Line
	15200 5350 14950 5350
Text Label 14950 5350 2    45   ~ 0
LCD_D5
Wire Wire Line
	15200 5450 14950 5450
Text Label 14950 5450 2    45   ~ 0
LCD_D6
Wire Wire Line
	15200 5550 14950 5550
Text Label 14950 5550 2    45   ~ 0
LCD_D7
Wire Wire Line
	15200 5650 14950 5650
Text Label 14950 5650 2    45   ~ 0
LCD_BL_A
Wire Wire Line
	15200 5750 14950 5750
Text Label 14950 5750 2    45   ~ 0
LCD_BL_K
Text Label 7900 1300 0    45   ~ 0
3V3
Wire Wire Line
	7900 1300 8150 1300
Text Label 7900 1480 0    45   ~ 0
1V1
Wire Wire Line
	7900 1480 8150 1480
Text Label 7900 1660 0    45   ~ 0
LOCATE_N
Wire Wire Line
	7900 1660 8150 1660
Text Label 7900 1840 0    45   ~ 0
OFF_N
Wire Wire Line
	7900 1840 8150 1840
Text Label 7900 2020 0    45   ~ 0
POWER_HOLD
Wire Wire Line
	7900 2020 8150 2020
Text Label 7900 2200 0    45   ~ 0
LCD_POWER_EN
Wire Wire Line
	7900 2200 8150 2200
Text Label 7900 2380 0    45   ~ 0
LCD_RS_3V3
Wire Wire Line
	7900 2380 8150 2380
Text Label 7900 2560 0    45   ~ 0
LCD_E_3V3
Wire Wire Line
	7900 2560 8150 2560
Text Label 7900 2740 0    45   ~ 0
LCD_D4_3V3
Wire Wire Line
	7900 2740 8150 2740
Text Label 7900 2920 0    45   ~ 0
LCD_D5_3V3
Wire Wire Line
	7900 2920 8150 2920
Text Label 7900 3100 0    45   ~ 0
LCD_D6_3V3
Wire Wire Line
	7900 3100 8150 3100
Text Label 7900 3280 0    45   ~ 0
LCD_D7_3V3
Wire Wire Line
	7900 3280 8150 3280
Text Label 7900 3460 0    45   ~ 0
BL_PWM
Wire Wire Line
	7900 3460 8150 3460
Text Label 7900 3640 0    45   ~ 0
GNSS_RX
Wire Wire Line
	7900 3640 8150 3640
Text Label 7900 3820 0    45   ~ 0
GNSS_TX
Wire Wire Line
	7900 3820 8150 3820
Text Label 7900 4000 0    45   ~ 0
GNSS_EN
Wire Wire Line
	7900 4000 8150 4000
Text Label 7900 4180 0    45   ~ 0
VBUS_PRESENT
Wire Wire Line
	7900 4180 8150 4180
Text Label 7900 4360 0    45   ~ 0
CHG_N
Wire Wire Line
	7900 4360 8150 4360
Text Label 7900 4540 0    45   ~ 0
BAT_SENSE_EN
Wire Wire Line
	7900 4540 8150 4540
Text Label 7900 4720 0    45   ~ 0
BAT_ADC
Wire Wire Line
	7900 4720 8150 4720
Text Label 10100 1300 0    45   ~ 0
RUN_N
Wire Wire Line
	10100 1300 9850 1300
Text Label 10100 1480 0    45   ~ 0
SWDIO
Wire Wire Line
	10100 1480 9850 1480
Text Label 10100 1660 0    45   ~ 0
SWCLK
Wire Wire Line
	10100 1660 9850 1660
Text Label 10100 1840 0    45   ~ 0
USB_DP
Wire Wire Line
	10100 1840 9850 1840
Text Label 10100 2020 0    45   ~ 0
USB_DM
Wire Wire Line
	10100 2020 9850 2020
Text Label 10100 2200 0    45   ~ 0
XIN
Wire Wire Line
	10100 2200 9850 2200
Text Label 10100 2380 0    45   ~ 0
XOUT
Wire Wire Line
	10100 2380 9850 2380
Text Label 10100 2560 0    45   ~ 0
QSPI_CSN
Wire Wire Line
	10100 2560 9850 2560
Text Label 10100 2740 0    45   ~ 0
QSPI_SCLK
Wire Wire Line
	10100 2740 9850 2740
Text Label 10100 2920 0    45   ~ 0
QSPI_SD0
Wire Wire Line
	10100 2920 9850 2920
Text Label 10100 3100 0    45   ~ 0
QSPI_SD1
Wire Wire Line
	10100 3100 9850 3100
Text Label 10100 3280 0    45   ~ 0
QSPI_SD2
Wire Wire Line
	10100 3280 9850 3280
Text Label 10100 3460 0    45   ~ 0
QSPI_SD3
Wire Wire Line
	10100 3460 9850 3460
Text Label 10100 3640 0    45   ~ 0
GND
Wire Wire Line
	10100 3640 9850 3640
Text Notes 900 10300 0 70 ~ 14
POWER FLOW: USB-C VBUS -> BQ24074 IN; cell -> BAT; BQ24074 OUT -> SYS_RAW only.
TPS63802 EN = diode-OR(VBUS, signal PMOS enabled by LOCATE or POWER_HOLD).
USB therefore sustains 3V3 while LCD_POWER_EN and GNSS_EN remain low.
Text Notes 900 10800 0 60 ~ 12
All reference passives, exact pin numbers, values, footprints and test points are captured in design.yaml, BOM and PCB.
This schematic is review source, not evidence of vendor/physical validation.
$EndSCHEMATC
