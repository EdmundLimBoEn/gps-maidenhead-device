#!/usr/bin/env python3
"""Block manufacturing until connectivity, KiCad DRC and source gates pass.

SPDX-License-Identifier: CERN-OHL-S-2.0
"""
from __future__ import annotations

import collections
import argparse
import csv
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "kicad" / "maidenhead-pocket-locator.kicad_pcb"
SCH = ROOT / "kicad" / "maidenhead-pocket-locator.sch"
BOM = ROOT / "bom" / "BOM_REV_A_ENGINEERING.csv"
REQUIRED_NETS = {
    "VBUS", "BAT", "SYS_RAW", "PWR_EN", "3V3", "5V_LCD", "GND",
    "POWER_HOLD", "LCD_POWER_EN", "GNSS_EN", "BAT_SENSE_EN",
    "GNSS_RF_50R", "USB_DP", "USB_DM",
}
REQUIRED_REFS = {
    "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "J1", "J2",
    "J3", "J4", "Q1", "Q2", "Q3", "Q4", "Q5", "SW1", "SW2",
}


def drc_report() -> tuple[int, collections.Counter[str], str]:
    system_python = Path("/usr/bin/python3")
    if not system_python.is_file():
        raise RuntimeError("/usr/bin/python3 is required for the KiCad pcbnew DRC binding")
    with tempfile.TemporaryDirectory(prefix="maidenhead-drc-") as temp:
        report = Path(temp) / "drc.rpt"
        program = (
            "import pcbnew,sys; "
            "b=pcbnew.LoadBoard(sys.argv[1]); "
            "ok=pcbnew.WriteDRCReport(b,sys.argv[2],pcbnew.EDA_UNITS_MILLIMETRES,True); "
            "raise SystemExit(0 if ok else 2)"
        )
        subprocess.run([str(system_python), "-c", program, str(PCB), str(report)], check=True)
        text = report.read_text(encoding="utf-8")
    match = re.search(r"Found (\d+) DRC violations", text)
    total = int(match.group(1)) if match else 0
    categories = collections.Counter(re.findall(r"^\[([^]]+)\]", text, re.MULTILINE))
    return total, categories, text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="validate source/net/BOM/outline but report DRC and vendor-footprint gates as pending",
    )
    args = parser.parse_args()
    failures: list[str] = []
    for path in (PCB, SCH, BOM, ROOT / "PIN_AND_CONNECTOR_MAP.md", ROOT / "RF_AND_LAYOUT.md"):
        if not path.is_file():
            failures.append(f"required source missing: {path.relative_to(ROOT.parent)}")

    if failures:
        for failure in failures: print(f"FAIL: {failure}")
        raise SystemExit(1)

    pcb = PCB.read_text(encoding="utf-8")
    sch = SCH.read_text(encoding="utf-8")
    missing_nets = sorted(net for net in REQUIRED_NETS if net not in pcb or net not in sch)
    if missing_nets:
        failures.append("critical nets not present in both PCB and schematic: " + ", ".join(missing_nets))

    if "(end 81 37)" not in pcb:
        failures.append("PCB outline is not the required 81 x 37 mm")

    pad_counts: collections.Counter[int] = collections.Counter(
        int(value) for value in re.findall(r'\(pad\s+"[^"]+"[^\n]+\(net\s+(\d+)\s+"[^"]+"\)', pcb)
    )
    routed = {int(value) for value in re.findall(r'\(segment[^\n]+\(net\s+(\d+)\)\)', pcb)}
    zoned = {int(value) for value in re.findall(r'\(zone\s+\(net\s+(\d+)\)', pcb)}
    net_names = {int(number): name for number, name in re.findall(r'^\s*\(net\s+(\d+)\s+"([^"]+)"\)', pcb, re.MULTILINE)}
    missing_copper = sorted(net_names[number] for number, count in pad_counts.items() if count > 1 and number not in routed | zoned)
    if missing_copper:
        failures.append("multi-pad nets with no copper connection: " + ", ".join(missing_copper))

    with BOM.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    refs = {ref.strip() for row in rows for ref in row["Designator"].split(",")}
    missing_refs = sorted(REQUIRED_REFS - refs)
    if missing_refs:
        failures.append("BOM lacks key designators: " + ", ".join(missing_refs))
    unresolved = [row["Designator"] for row in rows if not row["Manufacturer part number"].strip()]
    if unresolved:
        failures.append("BOM rows without MPN: " + ", ".join(unresolved))

    try:
        total, categories, _ = drc_report()
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        message = f"KiCad DRC could not run: {error}"
        if args.source_only:
            print(f"PENDING: {message}")
        else:
            failures.append(message)
    else:
        summary = ", ".join(f"{name}={count}" for name, count in categories.most_common())
        print(f"INFO: KiCad DRC total={total}; {summary}")
        if total and args.source_only:
            print(f"PENDING: KiCad DRC has {total} violations; manufacturing remains blocked")
        elif total:
            failures.append(f"KiCad DRC is not clean ({total} violations); zero unreviewed violations are required")
        if categories.get("unconnected_items", 0) and args.source_only:
            print(f"PENDING: routing has {categories['unconnected_items']} unconnected-item violations")
        elif categories.get("unconnected_items", 0):
            failures.append(f"routing is incomplete ({categories['unconnected_items']} unconnected-item violations)")

    provisional = sorted(set(re.findall(r'(?i)(GP-02|TPS22916)[^\n]{0,80}provisional', pcb + "\n" + sch)))
    if provisional and args.source_only:
        print("PENDING: provisional vendor land patterns remain")
    elif provisional:
        failures.append("provisional vendor land patterns remain; exact ordered-part footprints are required")

    if failures:
        for failure in failures: print(f"FAIL: {failure}")
        print("BLOCKED: engineering routing draft is not a manufacturing package.")
        raise SystemExit(1)

    if args.source_only:
        print("PASS: source/net/BOM/outline checks passed; manufacturing gates remain pending.")
    else:
        print("PASS: connected source, BOM, zero-unreviewed-error DRC and footprint gates passed.")
    if not shutil.which("kicad-cli"):
        print("WARN: kicad-cli absent; run export.sh in the pinned KiCad environment.")


if __name__ == "__main__":
    main()
