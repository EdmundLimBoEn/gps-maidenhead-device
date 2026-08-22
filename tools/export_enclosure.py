#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regenerate the enclosure release exports from their authoritative sources."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from validate_enclosure import parameters

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "enclosure/source/enclosure.scad"
EXPORTS = ROOT / "enclosure/exports"
PARTS = {
    "base.stl": "base",
    "lid.stl": "lid",
    "button-boot.stl": "button",
    "usb-plug.stl": "usb_plug",
}


def main() -> int:
    openscad = shutil.which("openscad")
    if not openscad:
        raise SystemExit("OpenSCAD is required to regenerate enclosure exports")
    EXPORTS.mkdir(parents=True, exist_ok=True)
    for filename, part in PARTS.items():
        subprocess.run(
            [
                openscad,
                "-D",
                f'part="{part}"',
                "-o",
                str(EXPORTS / filename),
                str(SOURCE),
            ],
            check=True,
        )

    values = parameters()
    width = values["lcd_window_width"]
    height = values["lcd_window_height"]
    radius = values["lcd_window_corner_radius"]
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->
<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}mm" height="{height:g}mm" viewBox="0 0 {width:g} {height:g}">
  <title>Maidenhead Pocket Locator polycarbonate window cut profile</title>
  <rect x="0.1" y="0.1" width="{width - 0.2:g}" height="{height - 0.2:g}"
        rx="{radius:g}" ry="{radius:g}" fill="none" stroke="#000" stroke-width="0.2"/>
</svg>
'''
    (EXPORTS / "window-cut.svg").write_text(svg, encoding="utf-8")

    preview = [
        openscad,
        "-D",
        'part="assembly"',
        "--imgsize=1200,700",
        "--autocenter",
        "--viewall",
        "--projection=ortho",
        "--render",
        "-o",
        str(EXPORTS / "assembly.png"),
        str(SOURCE),
    ]
    xvfb_run = shutil.which("xvfb-run")
    if xvfb_run:
        preview = [xvfb_run, "-a", *preview]
    subprocess.run(preview, check=True)

    hashed = [*PARTS, "window-cut.svg", "assembly.png"]
    lines = []
    for filename in hashed:
        digest = hashlib.sha256((EXPORTS / filename).read_bytes()).hexdigest()
        lines.append(f"{digest}  {filename}\n")
    (EXPORTS / "SHA256SUMS").write_text("".join(lines), encoding="ascii")
    return 0


if __name__ == "__main__":
    sys.exit(main())
