#!/usr/bin/env bash
# SPDX-License-Identifier: CERN-OHL-S-2.0
# Generate non-authoritative review artifacts. This script never marks a
# release as approved; the manual checklist and physical gates still apply.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
hardware_dir=$(cd -- "$script_dir/.." && pwd)
board="$hardware_dir/kicad/maidenhead-pocket-locator.kicad_pcb"
output="$script_dir/review-output"

command -v kicad-cli >/dev/null || { echo "kicad-cli is required" >&2; exit 127; }
python3 "$script_dir/preflight.py"
mkdir -p "$output/gerbers"

# Exporting forces pcbnew to parse the source. Explicit layers prevent an
# accidental omission when local plot settings differ between machines.
kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,B.SilkS,Edge.Cuts \
  --output "$output/board.svg" "$board"
kicad-cli pcb export gerbers --output "$output/gerbers" "$board"
kicad-cli pcb export drill --output "$output/" "$board"
kicad-cli pcb export pos --format csv --output "$output/placement.csv" "$board" || true

echo "Review exports written to $output"
echo "KiCad 7.0 CLI has no ERC/DRC subcommand. Run Inspect > Electrical Rules"
echo "Checker and Inspect > Design Rules Checker in the pinned KiCad GUI before release."
