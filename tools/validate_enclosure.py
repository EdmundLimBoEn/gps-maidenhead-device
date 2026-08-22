#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate enclosure parameters, exported meshes, and source/export agreement."""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import operator
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / "enclosure/source/parameters.scad"
SOURCE = ROOT / "enclosure/source/enclosure.scad"
EXPORTS = ROOT / "enclosure/exports"
PCB = ROOT / "hardware/kicad/maidenhead-pocket-locator.kicad_pcb"

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(expression: str, values: dict[str, float]) -> float:
    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](visit(node.operand))
        raise ValueError(f"unsupported parameter expression: {expression}")

    return visit(ast.parse(expression, mode="eval"))


def parameters() -> dict[str, float]:
    values: dict[str, float] = {}
    expressions: dict[str, str] = {}
    for line in PARAMETERS.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-z_][a-z0-9_]*)\s*=\s*([^;]+);", line.strip())
        if match:
            expressions[match.group(1)] = match.group(2)
    pending = dict(expressions)
    while pending:
        progressed = False
        for name, expression in list(pending.items()):
            try:
                values[name] = _evaluate(expression, values)
            except (ValueError, NameError):
                continue
            pending.pop(name)
            progressed = True
        if not progressed:
            raise ValueError(
                "unresolved enclosure parameters: " + ", ".join(sorted(pending))
            )
    return values


def stl_triangles(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    data = path.read_bytes()
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    if data[:5].lower() == b"solid" and b"vertex" in data[:2048]:
        vertices: list[tuple[float, float, float]] = []
        for match in re.finditer(rb"\bvertex\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)", data):
            vertices.append(tuple(float(value) for value in match.groups()))
        if len(vertices) % 3:
            raise ValueError(f"incomplete ASCII STL triangles in {path}")
        triangles = [
            tuple(vertices[index : index + 3]) for index in range(0, len(vertices), 3)
        ]
    elif len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if len(data) != 84 + count * 50:
            raise ValueError(f"invalid binary STL size in {path}")
        for index in range(count):
            values = struct.unpack_from("<12fH", data, 84 + index * 50)
            triangles.append(
                tuple(tuple(values[offset : offset + 3]) for offset in (3, 6, 9))
            )
    if not triangles:
        raise ValueError(f"no triangles in {path}")
    return triangles


def mesh_signature(path: Path) -> tuple[tuple[float, float, float], str, int]:
    triangles = stl_triangles(path)
    points = [point for triangle in triangles for point in triangle]
    edge_triangles: dict[tuple[tuple[float, float, float], ...], list[int]] = (
        collections.defaultdict(list)
    )
    for triangle_index, triangle in enumerate(triangles):
        quantized = [tuple(round(value, 5) for value in point) for point in triangle]
        if len(set(quantized)) != 3:
            raise ValueError(f"degenerate triangle in {path}")
        for index in range(3):
            edge = tuple(sorted((quantized[index], quantized[(index + 1) % 3])))
            edge_triangles[edge].append(triangle_index)
    non_manifold = sum(len(owners) != 2 for owners in edge_triangles.values())
    if non_manifold:
        raise ValueError(
            f"{path} is not a closed 2-manifold ({non_manifold} unmatched edges)"
        )
    parents = list(range(len(triangles)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for owners in edge_triangles.values():
        first, second = (find(index) for index in owners)
        if first != second:
            parents[second] = first
    components = {find(index) for index in range(len(triangles))}
    if len(components) != 1:
        raise ValueError(
            f"{path} contains {len(components)} disconnected printable shells"
        )
    bounds = tuple(
        max(point[index] for point in points) - min(point[index] for point in points)
        for index in range(3)
    )
    # CGAL may choose a different diagonal for an otherwise identical coplanar
    # face between runs, so compare the quantized vertex set plus facet count.
    canonical = sorted({tuple(round(value, 5) for value in point) for point in points})
    digest = hashlib.sha256(repr(canonical).encode("ascii")).hexdigest()
    return bounds, digest, len(triangles)


def close(actual: float, expected: float, tolerance: float = 0.02) -> bool:
    return abs(actual - expected) <= tolerance


def validate_parameters(values: dict[str, float]) -> None:
    frozen = {
        "outer_width": 88.0,
        "outer_height": 44.0,
        "pcb_width": 81.0,
        "pcb_height": 37.0,
        "screw_inset": 6.5,
        "screw_clearance": 2.7,
        "button_1_center": 13.5,
        "button_2_center": 30.5,
        "usb_center": 17.5,
    }
    drifted = [
        name for name, expected in frozen.items() if not close(values[name], expected)
    ]
    if drifted:
        raise ValueError(
            "frozen PCB/enclosure XY contract drifted: " + ", ".join(drifted)
        )
    if not close(
        values["button_2_center"] - values["button_1_center"], values["button_spacing"]
    ):
        raise ValueError("button centers do not match the frozen 17 mm spacing")
    if values["assembled_depth"] > 35.0:
        raise ValueError("assembled enclosure exceeds 35 mm depth")
    if not close(values["base_depth"] + values["lid_depth"], values["assembled_depth"]):
        raise ValueError("base and lid depth do not match assembled depth")
    interior_width = values["outer_width"] - 2 * values["wall"]
    interior_height = values["outer_height"] - 2 * values["wall"]
    required_width = values["pcb_width"] + 2 * values["pcb_edge_clearance"]
    required_height = values["pcb_height"] + 2 * values["pcb_edge_clearance"]
    if interior_width < required_width or interior_height < required_height:
        raise ValueError(
            f"PCB needs {required_width:.2f} x {required_height:.2f} mm but shell provides "
            f"{interior_width:.2f} x {interior_height:.2f} mm"
        )
    translation_x = (values["outer_width"] - values["pcb_width"]) / 2
    translation_y = (values["outer_height"] - values["pcb_height"]) / 2
    if not close(translation_x, 3.5) or not close(translation_y, 3.5):
        raise ValueError(
            "PCB-to-enclosure XY translation is not the frozen (+3.5,+3.5) mm"
        )
    flange_opening_width = values["outer_width"] - 2 * values["mating_flange_inset"]
    flange_opening_height = values["outer_height"] - 2 * values["mating_flange_inset"]
    if (
        flange_opening_width < values["pcb_width"] + 1.0
        or flange_opening_height < values["pcb_height"] + 1.0
    ):
        raise ValueError(
            "mating flange leaves less than 0.5 mm PCB insertion clearance per side"
        )
    if values["gasket_inset"] + values["gasket_width"] >= values["mating_flange_inset"]:
        raise ValueError("gasket groove has no inner hard-stop land")
    gasket_compression = 1.0 - values["gasket_depth"] / values["gasket_diameter"]
    if not 0.20 <= gasket_compression <= 0.35:
        raise ValueError(
            "nominal gasket compression is outside the 20-35% engineering range"
        )
    if values["lcd_window_recess_depth"] < values["lcd_window_thickness"]:
        raise ValueError("window recess is shallower than the polycarbonate window")
    if values["lcd_window_recess_depth"] >= values["lid_thickness"]:
        raise ValueError("window recess removes the full lid thickness")
    seal_x = (values["lcd_window_width"] - values["lcd_visible_width"]) / 2
    seal_y = (values["lcd_window_height"] - values["lcd_visible_height"]) / 2
    if min(seal_x, seal_y) < 2.5:
        raise ValueError("LCD window has less than 2.5 mm continuous seal land")
    lcd_mount_x = (values["outer_width"] - values["lcd_mount_pitch_x"]) / 2
    lcd_mount_y = (values["outer_height"] - values["lcd_mount_pitch_y"]) / 2
    if not close(lcd_mount_x, values["screw_inset"]) or not close(
        lcd_mount_y, values["screw_inset"]
    ):
        raise ValueError(
            "LCD mounting pitch no longer aligns with the frozen enclosure holes"
        )
    if values["battery_width"] + 2 * values["battery_clearance"] > interior_width:
        raise ValueError("battery envelope does not fit shell width")
    if values["battery_height"] > interior_height:
        raise ValueError("battery envelope does not fit shell height")


def validate_export_bounds(values: dict[str, float]) -> dict[str, tuple[str, int]]:
    expected = {
        "base": (values["outer_width"], values["outer_height"], values["base_depth"]),
        "lid": (values["outer_width"], values["outer_height"], values["lid_depth"]),
        "button-boot": (values["button_diameter"] + 4.0,) * 2 + (5.0,),
        "usb-plug": (values["usb_width"] + 4.0, values["usb_height"] + 3.0, 6.4),
    }
    signatures: dict[str, tuple[str, int]] = {}
    for name, target in expected.items():
        bounds, digest, facets = mesh_signature(EXPORTS / f"{name}.stl")
        if not all(
            close(actual, wanted) for actual, wanted in zip(bounds, target, strict=True)
        ):
            raise ValueError(f"{name}.stl bounds {bounds} do not match {target}")
        signatures[name] = (digest, facets)
        print(
            f"{name}: {bounds[0]:.2f} x {bounds[1]:.2f} x {bounds[2]:.2f} mm; "
            f"{facets} facets; closed connected shell"
        )
    return signatures


def validate_svg(values: dict[str, float]) -> None:
    svg = (EXPORTS / "window-cut.svg").read_text(encoding="utf-8")
    expected = f'width="{values["lcd_window_width"]:g}mm" height="{values["lcd_window_height"]:g}mm"'
    if expected not in svg:
        raise ValueError("window-cut.svg dimensions do not match OpenSCAD parameters")


def validate_pcb_xy_contract() -> None:
    pcb = PCB.read_text(encoding="utf-8")
    rectangle = re.search(
        r"\(gr_rect\s+\(start\s+0(?:\.0+)?\s+0(?:\.0+)?\)\s+\(end\s+81(?:\.0+)?\s+37(?:\.0+)?\)",
        pcb,
    )
    edge_lines = {
        ((float(x1), float(y1)), (float(x2), float(y2)))
        for x1, y1, x2, y2 in re.findall(
            r"\(gr_line\s+\(start\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(end\s+([-0-9.]+)\s+([-0-9.]+)\).*?\(layer\s+\"Edge\.Cuts\"\)",
            pcb,
            re.DOTALL,
        )
    }
    required_edges = {
        ((0.0, 0.0), (81.0, 0.0)),
        ((81.0, 0.0), (81.0, 37.0)),
        ((81.0, 37.0), (0.0, 37.0)),
        ((0.0, 37.0), (0.0, 0.0)),
    }
    if not rectangle and edge_lines != required_edges:
        raise ValueError("PCB outline drifted from the frozen 81 x 37 mm contract")

    blocks = ["  (footprint" + block for block in pcb.split("\n  (footprint")[1:]]

    def placement(reference: str) -> tuple[float, float, float, str]:
        for block in blocks:
            if re.search(rf'\(fp_text\s+reference\s+"{re.escape(reference)}"', block):
                at = re.search(
                    r"^\s*\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)",
                    block,
                    re.MULTILINE,
                )
                value = re.search(r'\(fp_text\s+value\s+"([^"]+)"', block)
                if not at or not value:
                    break
                return (
                    float(at.group(1)),
                    float(at.group(2)),
                    float(at.group(3) or 0),
                    value.group(1),
                )
        raise ValueError(f"PCB interface footprint {reference} missing or malformed")

    j1 = placement("J1")
    if not (close(j1[0], 4.785) and close(j1[1], 14.0) and close(abs(j1[2]), 90.0)):
        raise ValueError(
            f"J1 placement {j1[:3]} drifted from the frozen left-edge USB datum"
        )
    for reference, y in (("SW1", 10.0), ("SW2", 27.0)):
        placed = placement(reference)
        if not (
            close(placed[0], 78.25)
            and close(placed[1], y)
            and "TL1014BF160QG" in placed[3]
        ):
            raise ValueError(
                f"{reference} placement/value drifted from the frozen side-button datum"
            )
    holes = {
        tuple(round(value, 2) for value in placement(f"H{index}")[:2])
        for index in range(1, 5)
    }
    expected_holes = {(3.0, 3.0), (78.0, 3.0), (3.0, 34.0), (78.0, 34.0)}
    if holes != expected_holes:
        raise ValueError(f"PCB mounting-hole centers drifted: {sorted(holes)}")
    for block in blocks:
        is_mount = any(
            re.search(rf'\(fp_text\s+reference\s+"H{index}"', block)
            for index in range(1, 5)
        )
        if is_mount and not re.search(r"\(drill\s+2\.7(?:0+)?\)", block):
            raise ValueError("PCB M2.5 mounting holes are not 2.7 mm NPTH")
    print("PCB/enclosure XY datum: match")


def validate_generated(
    signatures: dict[str, tuple[str, int]], require_openscad: bool
) -> None:
    executable = shutil.which("openscad")
    if not executable:
        if require_openscad:
            raise ValueError("OpenSCAD is required for source/export verification")
        print("SKIP: OpenSCAD unavailable; source/export mesh comparison not run")
        return
    with tempfile.TemporaryDirectory(prefix="pocket-locator-cad-") as temp:
        for name, expected_signature in signatures.items():
            source_name = {"button-boot": "button", "usb-plug": "usb_plug"}.get(
                name, name
            )
            rendered = Path(temp) / f"{name}.stl"
            subprocess.run(
                [
                    executable,
                    "-D",
                    f'part="{source_name}"',
                    "-o",
                    str(rendered),
                    str(SOURCE),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            _, digest, facets = mesh_signature(rendered)
            if (digest, facets) != expected_signature:
                raise ValueError(
                    f"{name}.stl is stale; regenerate it from enclosure.scad"
                )
    print("source/export mesh signatures: match")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-openscad", action="store_true")
    args = parser.parse_args()
    values = parameters()
    validate_parameters(values)
    signatures = validate_export_bounds(values)
    validate_svg(values)
    validate_pcb_xy_contract()
    validate_generated(signatures, args.require_openscad)
    print(f"assembled depth: {values['assembled_depth']:.2f} mm (limit 35.00 mm)")
    print("PASS: CAD source and exports satisfy the automated dimensional checks.")
    print(
        "PENDING: sample fit, stack-up, sealing, RF orientation, and environmental tests."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
