#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check committed release-facing source artifacts without inventing test evidence.

This intentionally does not claim a release is manufacturable. The physical gates
remain explicit in docs/manufacturing/RELEASE_CHECKLIST.md and TEST_EVIDENCE.md.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "PLAN.md",
    "README.md",
    "firmware/README.md",
    "firmware/releases/README.md",
    "firmware/releases/SHA256SUMS",
    "firmware/releases/pocket_locator_rp2040.uf2",
    "configurator/README.md",
    "configurator/profiles/factory-default.json",
    "enclosure/source/enclosure.scad",
    "enclosure/source/parameters.scad",
    "enclosure/exports/base.stl",
    "enclosure/exports/lid.stl",
    "enclosure/exports/button-boot.stl",
    "enclosure/exports/usb-plug.stl",
    "enclosure/exports/window-cut.svg",
    "hardware/kicad/maidenhead-pocket-locator.kicad_pro",
    "hardware/kicad/maidenhead-pocket-locator.kicad_pcb",
    "hardware/kicad/maidenhead-pocket-locator.sch",
    "hardware/kicad/design.yaml",
    "hardware/bom/BOM_REV_A_ENGINEERING.csv",
    "hardware/bom/PASSIVES_REV_A_ENGINEERING.csv",
    "hardware/manufacturing/preflight.py",
    "hardware/manufacturing/export.sh",
    "docs/assembly/ASSEMBLY.md",
    "docs/assembly/USER_GUIDE.md",
    "docs/manufacturing/RELEASE_CHECKLIST.md",
    "docs/manufacturing/ORDER_PACKAGE.md",
    "docs/testing/TEST_EVIDENCE.md",
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        fail("required release-facing artifacts missing: " + ", ".join(missing))

    profile_path = ROOT / "configurator/profiles/factory-default.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if "timezone_table" in profile.get("config", {}):
        fail("profiles must not persist host-generated timezone tables")
    if "coordinates" in profile or "diagnostics" in profile:
        fail("profiles must not include location or transient diagnostics")

    checksum_file = ROOT / "firmware/releases/SHA256SUMS"
    subprocess.run(["sha256sum", "-c", str(checksum_file.relative_to(ROOT))], cwd=ROOT, check=True)

    subprocess.run([sys.executable, str(ROOT / "tools/validate_enclosure.py")], check=True)
    print("PASS: release-facing source artifacts are present.")
    print("PENDING: physical acceptance evidence and five-unit cost quote are required before ordering.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
