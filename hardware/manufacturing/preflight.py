#!/usr/bin/env python3
"""Block manufacturing until connectivity, KiCad DRC and source gates pass.

SPDX-License-Identifier: CERN-OHL-S-2.0
"""
from __future__ import annotations

import argparse
import collections
import csv
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "kicad" / "maidenhead-pocket-locator.kicad_pcb"
SCH = ROOT / "kicad" / "maidenhead-pocket-locator.sch"
MODERN_SCH = ROOT / "kicad" / "maidenhead-pocket-locator.kicad_sch"
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


def drc_report(report_copy: Path | None = None) -> tuple[int, collections.Counter[str], str]:
    system_python = Path("/usr/bin/python3")
    if not system_python.is_file():
        raise RuntimeError("/usr/bin/python3 is required for the KiCad pcbnew DRC binding")
    with tempfile.TemporaryDirectory(prefix="maidenhead-drc-") as temp:
        report = Path(temp) / "drc.rpt"
        program = (
            "import os,pcbnew,sys; "
            "pcbnew.GetSettingsManager().LoadProject(os.path.abspath(sys.argv[3])); "
            "b=pcbnew.LoadBoard(sys.argv[1]); "
            "ok=pcbnew.WriteDRCReport(b,sys.argv[2],pcbnew.EDA_UNITS_MILLIMETRES,True); "
            "raise SystemExit(0 if ok else 2)"
        )
        project = ROOT / "kicad" / "maidenhead-pocket-locator.kicad_pro"
        subprocess.run([str(system_python), "-c", program, str(PCB), str(report), str(project)], check=True)
        text = report.read_text(encoding="utf-8")
        if report_copy is not None:
            report_copy.parent.mkdir(parents=True, exist_ok=True)
            report_copy.write_text(text, encoding="utf-8")
    match = re.search(r"Found (\d+) DRC violations", text)
    total = int(match.group(1)) if match else 0
    categories = collections.Counter(re.findall(r"^\[([^]]+)\]", text, re.MULTILINE))
    return total, categories, text


def filled_zones() -> set[tuple[str, str]]:
    program = (
        "import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); "
        "[(print(z.GetNetname()+'|'+pcbnew.LayerName(z.GetLayer()))) "
        "for z in b.Zones() if z.IsFilled() and z.HasFilledPolysForLayer(z.GetLayer())]"
    )
    result = subprocess.run(
        ["/usr/bin/python3", "-c", program, str(PCB)],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        tuple(line.split("|", 1))
        for line in result.stdout.splitlines()
        if "|" in line
    }


def pin_contracts() -> tuple[set[tuple[str, str, str]], set[tuple[str, str, str]], str]:
    board_program = (
        "import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); "
        "[(print(f.GetReference()+'|'+p.GetNumber()+'|'+p.GetNetname())) "
        "for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()]"
    )
    board_result = subprocess.run(
        ["/usr/bin/python3", "-c", board_program, str(PCB)],
        check=True,
        capture_output=True,
        text=True,
    )
    board_contract = {
        tuple(line.split("|", 2)) for line in board_result.stdout.splitlines() if "|" in line
    }
    with tempfile.TemporaryDirectory(prefix="maidenhead-netlist-") as temp:
        netlist = Path(temp) / "design.net"
        result = subprocess.run(
            ["kicad-cli", "sch", "export", "netlist", "--output", str(netlist), str(MODERN_SCH)],
            check=True,
            capture_output=True,
            text=True,
        )
        text = netlist.read_text(encoding="utf-8")
    schematic_contract: set[tuple[str, str, str]] = set()
    for match in re.finditer(
        r'^    \(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)(?=^    \(net |^  \)\s*$)',
        text,
        re.MULTILINE | re.DOTALL,
    ):
        net_name = match.group(1).removeprefix("/")
        if net_name.startswith("unconnected-"):
            continue
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', match.group(2)):
            schematic_contract.add((ref, pin, net_name))
    return board_contract, schematic_contract, result.stderr + result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="validate source/net/BOM/outline but report DRC and vendor-footprint gates as pending",
    )
    parser.add_argument("--drc-report", type=Path, help="archive the complete KiCad DRC report")
    args = parser.parse_args()
    failures: list[str] = []
    for path in (
        PCB,
        SCH,
        MODERN_SCH,
        BOM,
        ROOT / "PIN_AND_CONNECTOR_MAP.md",
        ROOT / "RF_AND_LAYOUT.md",
    ):
        if not path.is_file():
            failures.append(f"required source missing: {path.relative_to(ROOT.parent)}")

    if failures:
        for failure in failures: print(f"FAIL: {failure}")
        raise SystemExit(1)

    pcb = PCB.read_text(encoding="utf-8")
    sch = SCH.read_text(encoding="utf-8")
    modern_sch = MODERN_SCH.read_text(encoding="utf-8")
    missing_nets = sorted(
        net
        for net in REQUIRED_NETS
        if net not in pcb or net not in sch or net not in modern_sch
    )
    if missing_nets:
        failures.append(
            "critical nets not present in PCB and both schematic sources: "
            + ", ".join(missing_nets)
        )

    if "(end 81 37)" not in pcb:
        failures.append("PCB outline is not the required 81 x 37 mm")

    copper_layers = re.findall(r'^\s*\(\d+ "([FBI][^\"]*\.Cu)" signal\)', pcb, re.MULTILINE)
    if copper_layers != ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]:
        failures.append(f"PCB is not the required four-layer stack: {copper_layers}")

    net_names = {
        int(number): name
        for number, name in re.findall(
            r'^\s*\(net\s+(\d+)\s+"([^"]+)"\)', pcb, re.MULTILINE
        )
    }
    in2_signal_limits = {
        "LCD_RS_3V3": 7.0,
        "LOCATE_N": 4.0,
        "QSPI_SD2": 6.0,
        "QSPI_SCLK": 6.0,
    }
    in2_lengths: collections.Counter[str] = collections.Counter()
    for line in (line for line in pcb.splitlines() if "(segment " in line):
        layer_match = re.search(r'\(layer "(In1\.Cu|In2\.Cu)"\)', line)
        if not layer_match:
            continue
        net_match = re.search(r'\(net\s+(\d+)\)', line)
        net_name = net_names.get(int(net_match.group(1)), "<unknown>") if net_match else "<unknown>"
        layer = layer_match.group(1)
        if layer == "In2.Cu" and net_name == "3V3":
            continue
        if layer == "In1.Cu" or net_name not in in2_signal_limits:
            failures.append(f"disallowed inner-layer signal: {net_name} on {layer}")
            continue
        points = re.findall(r'\((?:start|end)\s+([\d.]+)\s+([\d.]+)\)', line)
        if len(points) == 2:
            start, end = (tuple(map(float, point)) for point in points)
            in2_lengths[net_name] += math.dist(start, end)
    too_long = {
        net: length
        for net, length in in2_lengths.items()
        if length > in2_signal_limits[net]
    }
    if too_long:
        failures.append(
            "allowlisted In2 crossover exceeds its length limit: "
            + ", ".join(
                f"{net}={length:.3f} mm (limit {in2_signal_limits[net]:.1f} mm)"
                for net, length in sorted(too_long.items())
            )
        )

    required_planes = {("GND", "In1.Cu"), ("3V3", "In2.Cu")}
    plane_headers = {
        (name, layer)
        for name, layer in re.findall(
            r'\(zone\s+\(net\s+\d+\)\s+\(net_name "([^"]+)"\)\s+\(layer "([^"]+)"\)',
            pcb,
        )
    }
    missing_planes = sorted(required_planes - plane_headers)
    if missing_planes:
        failures.append(f"required internal planes are missing: {missing_planes}")
    try:
        missing_fills = required_planes - filled_zones()
    except (OSError, subprocess.CalledProcessError) as error:
        failures.append(f"filled-zone verification could not run: {error}")
    else:
        if missing_fills:
            failures.append(f"required internal planes are not filled: {sorted(missing_fills)}")

    if shutil.which("kicad-cli"):
        try:
            board_contract, schematic_contract, schematic_messages = pin_contracts()
        except (OSError, subprocess.CalledProcessError) as error:
            failures.append(f"schematic/PCB pin-contract verification could not run: {error}")
        else:
            if "annotation errors" in schematic_messages.lower():
                failures.append("modern schematic has annotation errors")
            missing_from_schematic = sorted(board_contract - schematic_contract)
            missing_from_board = sorted(schematic_contract - board_contract)
            if missing_from_schematic or missing_from_board:
                failures.append(
                    "modern schematic and PCB pin/net contracts differ: "
                    f"PCB-only={missing_from_schematic[:8]}, schematic-only={missing_from_board[:8]}"
                )

    pad_counts: collections.Counter[int] = collections.Counter(
        int(value) for value in re.findall(r'\(pad\s+"[^"]+"[^\n]+\(net\s+(\d+)\s+"[^"]+"\)', pcb)
    )
    routed = {int(value) for value in re.findall(r'\(segment[^\n]+\(net\s+(\d+)\)\)', pcb)}
    zoned = {int(value) for value in re.findall(r'\(zone\s+\(net\s+(\d+)\)', pcb)}
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
        total, categories, _ = drc_report(args.drc_report)
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

    provisional = [
        row["Designator"]
        for row in rows
        if re.search(r"(?i)\b(provisional|representative)\b", row["Status / verification required"])
    ]
    if provisional:
        print(
            "PENDING: exact ordered-part/physical overlay validation remains for "
            + ", ".join(provisional)
        )

    if failures:
        for failure in failures: print(f"FAIL: {failure}")
        print("BLOCKED: engineering routing draft is not a manufacturing package.")
        raise SystemExit(1)

    if args.source_only:
        print("PASS: source/net/BOM/outline checks passed; manufacturing gates remain pending.")
    else:
        print("PASS: automated connectivity, BOM presence, zone-fill and zero-error DRC checks passed.")
    if not shutil.which("kicad-cli"):
        print("WARN: kicad-cli absent; run export.sh in the pinned KiCad environment.")


if __name__ == "__main__":
    main()
