#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check committed release-facing source artifacts without inventing test evidence.

This intentionally does not claim a release is manufacturable. The physical gates
remain explicit in docs/manufacturing/RELEASE_CHECKLIST.md and TEST_EVIDENCE.md.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "PLAN.md",
    "README.md",
    "LICENSES/GPL-3.0-or-later.txt",
    "LICENSES/CERN-OHL-S-2.0.txt",
    "LICENSES/CC-BY-SA-4.0.txt",
    "firmware/README.md",
    "firmware/releases/README.md",
    "firmware/releases/SHA256SUMS",
    "firmware/releases/pocket_locator_rp2040.uf2",
    "configurator/README.md",
    "configurator/profiles/factory-default.json",
    "enclosure/source/enclosure.scad",
    "enclosure/source/parameters.scad",
    "enclosure/INTERFACES.md",
    "enclosure/exports/SHA256SUMS",
    "enclosure/exports/base.stl",
    "enclosure/exports/lid.stl",
    "enclosure/exports/button-boot.stl",
    "enclosure/exports/usb-plug.stl",
    "enclosure/exports/window-cut.svg",
    "hardware/kicad/maidenhead-pocket-locator.kicad_pro",
    "hardware/kicad/maidenhead-pocket-locator.kicad_pcb",
    "hardware/kicad/maidenhead-pocket-locator.kicad_sch",
    "hardware/kicad/maidenhead-pocket-locator.sch",
    "hardware/kicad/maidenhead-pocket-locator-cache.lib",
    "hardware/kicad/design.yaml",
    "hardware/kicad/generate_kicad.py",
    "hardware/kicad/fp-lib-table",
    "hardware/kicad/PocketLocator.pretty/GP-02.kicad_mod",
    "hardware/kicad/PocketLocator.pretty/SW_TL1014B.kicad_mod",
    "hardware/kicad/PocketLocator.pretty/Texas_DLA0010A.kicad_mod",
    "hardware/kicad/PocketLocator.pretty/Texas_DRT0003A.kicad_mod",
    "hardware/kicad/PocketLocator.pretty/Texas_RGT0016C.kicad_mod",
    "hardware/kicad/PocketLocator.pretty/Texas_YFP0004.kicad_mod",
    "hardware/kicad/PocketLocator.pretty/USB4105-GF-A.kicad_mod",
    "hardware/kicad/PocketLocator.pretty/Winbond_UX_8.kicad_mod",
    "hardware/bom/BOM_REV_A_ENGINEERING.csv",
    "hardware/bom/PASSIVES_REV_A_ENGINEERING.csv",
    "hardware/manufacturing/preflight.py",
    "hardware/manufacturing/export.sh",
    "tools/generate_assembly_files.py",
    "tools/generate_ibom.py",
    "docs/assembly/ASSEMBLY.md",
    "docs/assembly/USER_GUIDE.md",
    "docs/manufacturing/RELEASE_CHECKLIST.md",
    "docs/manufacturing/ORDER_PACKAGE.md",
    "docs/manufacturing/COST_RESEARCH.md",
    "docs/testing/TEST_EVIDENCE.md",
    "docs/testing/TEST_PROCEDURES.md",
    "docs/testing/cold-start-record.csv",
    "docs/testing/outing-record.csv",
    "docs/testing/power-record.csv",
    "docs/testing/environment-record.csv",
    "docs/testing/charging-record.csv",
    "docs/testing/controls-recovery-record.csv",
    "docs/testing/mechanical-fit-record.csv",
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

    verify_checksums(ROOT / "firmware/releases/SHA256SUMS", ROOT)
    verify_checksums(ROOT / "enclosure/exports/SHA256SUMS", ROOT / "enclosure/exports")
    validate_test_templates()

    subprocess.run(
        [sys.executable, str(ROOT / "tools/validate_enclosure.py")], check=True
    )
    subprocess.run([sys.executable, str(ROOT / "tools/check_docs.py")], check=True)
    print("PASS: release-facing source artifacts are present.")
    print(
        "PENDING: physical acceptance evidence and five-unit cost quote are required before ordering."
    )
    return 0


def verify_checksums(manifest: Path, base: Path) -> None:
    for line in manifest.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        expected, filename = line.split(maxsplit=1)
        path = base / filename.lstrip("* ")
        if not path.is_file():
            fail(f"checksum target missing: {path.relative_to(ROOT)}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            fail(f"checksum mismatch: {path.relative_to(ROOT)}")


def validate_test_templates() -> None:
    required_common = {
        "unit_serial",
        "pcb_revision",
        "firmware_revision",
        "pass",
        "notes",
    }
    for path in sorted((ROOT / "docs/testing").glob("*-record.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            fields = next(csv.reader(handle))
        if len(fields) != len(set(fields)):
            fail(f"duplicate CSV columns: {path.relative_to(ROOT)}")
        missing = required_common - set(fields)
        if missing:
            fail(
                f"test template lacks {', '.join(sorted(missing))}: {path.relative_to(ROOT)}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
