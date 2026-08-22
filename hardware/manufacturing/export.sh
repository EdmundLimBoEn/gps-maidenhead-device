#!/usr/bin/env bash
# SPDX-License-Identifier: CERN-OHL-S-2.0
# Generate non-authoritative review artifacts. This script never marks a
# release as approved; the manual checklist and physical gates still apply.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
hardware_dir=$(cd -- "$script_dir/.." && pwd)
board="$hardware_dir/kicad/maidenhead-pocket-locator.kicad_pcb"
schematic="$hardware_dir/kicad/maidenhead-pocket-locator.kicad_sch"
output="$script_dir/review-output"
staging=$(mktemp -d "$script_dir/.review-output.XXXXXX")
trap 'rm -rf -- "$staging"' EXIT

command -v kicad-cli >/dev/null || { echo "kicad-cli is required" >&2; exit 127; }
mkdir -p "$staging/gerbers"
python3 "$script_dir/preflight.py" --drc-report "$staging/drc.rpt"

# Exporting forces pcbnew to parse the source. Explicit layers prevent an
# accidental omission when local plot settings differ between machines.
kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,B.SilkS,Edge.Cuts \
  --output "$staging/board.svg" "$board"
kicad-cli pcb export pdf --layers F.Fab,F.Silkscreen,Edge.Cuts \
  --output "$staging/assembly-top.pdf" "$board"
kicad-cli pcb export gerbers \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --output "$staging/gerbers" "$board"
kicad-cli pcb export drill --output "$staging/" "$board"
kicad-cli pcb export pos --format csv --units mm --smd-only \
  --output "$staging/.placement-all-smd.csv" "$board"
/usr/bin/python3 -c 'import pcbnew,sys; board=pcbnew.LoadBoard(sys.argv[1]); pcbnew.IPC356D_WRITER(board).Write(sys.argv[2])' \
  "$board" "$staging/ipc-d-356.net"
if [[ ! -f "$schematic" ]]; then
  echo "Modern schematic missing: open the legacy .sch in KiCad and save it once" >&2
  exit 1
fi
kicad-cli sch export pdf --output "$staging/schematic.pdf" "$schematic"
kicad-cli sch export netlist --output "$staging/design.net" "$schematic"
cp "$hardware_dir/bom/BOM_REV_A_ENGINEERING.csv" "$staging/bom.csv"
cp "$hardware_dir/bom/PASSIVES_REV_A_ENGINEERING.csv" "$staging/passives.csv"
python3 "$hardware_dir/../tools/generate_assembly_files.py" \
  "$staging/bom.csv" "$staging/passives.csv" "$staging/.placement-all-smd.csv" \
  "$staging/assembly-bom.csv" "$staging/placement.csv"
unlink "$staging/.placement-all-smd.csv"
python3 "$hardware_dir/../tools/generate_ibom.py" \
  "$staging/assembly-bom.csv" "$staging/placement.csv" "$staging/interactive-bom.html"

required_artifacts=(
  board.svg assembly-top.pdf drc.rpt maidenhead-pocket-locator.drl placement.csv
  ipc-d-356.net schematic.pdf design.net bom.csv passives.csv assembly-bom.csv
  interactive-bom.html
  gerbers/maidenhead-pocket-locator-F_Cu.gtl
  gerbers/maidenhead-pocket-locator-In1_Cu.g2
  gerbers/maidenhead-pocket-locator-In2_Cu.g3
  gerbers/maidenhead-pocket-locator-B_Cu.gbl
  gerbers/maidenhead-pocket-locator-F_Paste.gtp
  gerbers/maidenhead-pocket-locator-B_Paste.gbp
  gerbers/maidenhead-pocket-locator-F_Silkscreen.gto
  gerbers/maidenhead-pocket-locator-B_Silkscreen.gbo
  gerbers/maidenhead-pocket-locator-F_Mask.gts
  gerbers/maidenhead-pocket-locator-B_Mask.gbs
  gerbers/maidenhead-pocket-locator-Edge_Cuts.gm1
  gerbers/maidenhead-pocket-locator-job.gbrjob
)
for artifact in "${required_artifacts[@]}"; do
  if [[ ! -s "$staging/$artifact" ]]; then
    echo "Missing or empty review artifact: $artifact" >&2
    exit 1
  fi
done
gerber_count=$(find "$staging/gerbers" -maxdepth 1 -type f | wc -l)
if [[ "$gerber_count" -ne 12 ]]; then
  echo "Expected 11 fabrication Gerbers plus one job file, found $gerber_count files" >&2
  exit 1
fi

rm -rf -- "$output"
mv "$staging" "$output"
trap - EXIT

echo "Review exports written to $output"
echo "KiCad 7.0 CLI has no ERC subcommand. Archive a GUI ERC report before release."
