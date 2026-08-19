#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / "enclosure/source/parameters.scad"
EXPORTS = ROOT / "enclosure/exports"


def parameters() -> dict[str, float]:
    values: dict[str, float] = {}
    expressions: dict[str, str] = {}
    for line in PARAMETERS.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-z_]+)\s*=\s*([^;]+);", line.strip())
        if match:
            expressions[match.group(1)] = match.group(2)
    pending = dict(expressions)
    while pending:
        progressed = False
        for name, expression in list(pending.items()):
            if not re.fullmatch(r"[0-9a-z_+.\-*/ ]+", expression):
                continue
            try:
                value = eval(expression, {"__builtins__": {}}, values)  # noqa: S307
            except NameError:
                continue
            values[name] = float(value)
            pending.pop(name)
            progressed = True
        if not progressed:
            break
    return values


def stl_bounds(path: Path) -> tuple[float, float, float]:
    points: list[tuple[float, float, float]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        if line.lstrip().startswith("vertex "):
            _, x, y, z = line.split()
            points.append((float(x), float(y), float(z)))
    if not points:
        raise ValueError(f"no vertices in {path}")
    return tuple(max(point[index] for point in points) - min(point[index] for point in points) for index in range(3))


def close(actual: float, expected: float, tolerance: float = 0.02) -> bool:
    return abs(actual - expected) <= tolerance


def main() -> int:
    values = parameters()
    required = {"outer_width", "outer_height", "base_depth", "lid_depth", "assembled_depth"}
    missing = required - values.keys()
    if missing:
        raise ValueError(f"unresolved enclosure parameters: {', '.join(sorted(missing))}")
    if values["assembled_depth"] > 35.0:
        raise ValueError("assembled enclosure exceeds 35 mm depth")
    if not close(values["base_depth"] + values["lid_depth"], values["assembled_depth"]):
        raise ValueError("base and lid depth do not match assembled depth")
    for name, depth in (("base", values["base_depth"]), ("lid", values["lid_depth"])):
        bounds = stl_bounds(EXPORTS / f"{name}.stl")
        expected = (values["outer_width"], values["outer_height"], depth)
        if not all(close(actual, target) for actual, target in zip(bounds, expected, strict=True)):
            raise ValueError(f"{name}.stl bounds {bounds} do not match {expected}")
        print(f"{name}: {bounds[0]:.2f} x {bounds[1]:.2f} x {bounds[2]:.2f} mm")
    print(f"assembled depth: {values['assembled_depth']:.2f} mm (limit 35.00 mm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
