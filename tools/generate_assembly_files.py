#!/usr/bin/env python3
"""Build matched, one-reference-per-row SMD assembly BOM and placement files."""

# SPDX-License-Identifier: CC-BY-SA-4.0

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def expand_refs(value: str) -> list[str]:
    refs: list[str] = []
    for token in (part.strip() for part in value.split(",")):
        match = re.fullmatch(r"([A-Z]+)(\d+)-([A-Z]+)?(\d+)", token)
        if not match:
            refs.append(token)
            continue
        start_prefix, start, end_prefix, end = match.groups()
        if end_prefix and end_prefix != start_prefix:
            raise ValueError(f"mixed-prefix designator range: {token}")
        refs.extend(
            f"{start_prefix}{number}" for number in range(int(start), int(end) + 1)
        )
    return refs


def split_aligned(value: str, count: int) -> list[str]:
    parts = [part.strip() for part in value.split(" / ")]
    return parts if len(parts) == count else [value.strip()] * count


def part_number(value: str) -> str:
    return value.rsplit(maxsplit=1)[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engineering_bom", type=Path)
    parser.add_argument("passives_bom", type=Path)
    parser.add_argument("raw_placement", type=Path)
    parser.add_argument("assembly_bom", type=Path)
    parser.add_argument("assembly_placement", type=Path)
    args = parser.parse_args()

    with args.raw_placement.open(newline="", encoding="utf-8-sig") as handle:
        placement_reader = csv.DictReader(handle)
        placement = {row["Ref"]: row for row in placement_reader}

    parts: dict[str, dict[str, str]] = {}
    with args.engineering_bom.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["Population"] != "Fit" or row["Designator"] == "R/C network":
                continue
            for ref in expand_refs(row["Designator"]):
                if ref in placement:
                    parts[ref] = {
                        "Designator": ref,
                        "Quantity": "1",
                        "Value": placement[ref]["Val"],
                        "Manufacturer": row["Manufacturer"],
                        "Manufacturer part number": row["Manufacturer part number"],
                        "Footprint": placement[ref]["Package"],
                        "Population": "JLC SMD",
                    }

    with args.passives_bom.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            refs = expand_refs(row["Designator"])
            values = split_aligned(row["Value"], len(refs))
            mpns = split_aligned(row["Suggested MPN"], len(refs))
            manufacturer = row["Suggested MPN"].split(maxsplit=1)[0]
            for ref, value, mpn in zip(refs, values, mpns, strict=True):
                if ref not in placement:
                    continue
                if ref in parts:
                    raise ValueError(f"duplicate assembly mapping for {ref}")
                parts[ref] = {
                    "Designator": ref,
                    "Quantity": "1",
                    "Value": value,
                    "Manufacturer": manufacturer,
                    "Manufacturer part number": part_number(mpn),
                    "Footprint": placement[ref]["Package"],
                    "Population": "JLC SMD",
                }

    if not parts:
        raise ValueError("assembly BOM is empty")
    missing_positions = sorted(set(parts) - set(placement))
    if missing_positions:
        raise ValueError(
            f"assembly BOM references absent from placement: {missing_positions}"
        )

    bom_fields = [
        "Designator",
        "Quantity",
        "Value",
        "Manufacturer",
        "Manufacturer part number",
        "Footprint",
        "Population",
    ]
    ordered_refs = sorted(
        parts,
        key=lambda ref: (
            re.match(r"[A-Z]+", ref).group(),
            int(re.search(r"\d+$", ref).group()),
        ),
    )
    with args.assembly_bom.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=bom_fields)
        writer.writeheader()
        writer.writerows(parts[ref] for ref in ordered_refs)
    placement_fields = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    with args.assembly_placement.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=placement_fields)
        writer.writeheader()
        writer.writerows(
            {
                "Designator": ref,
                "Mid X": placement[ref]["PosX"],
                "Mid Y": placement[ref]["PosY"],
                "Layer": placement[ref]["Side"].title(),
                "Rotation": placement[ref]["Rot"],
            }
            for ref in ordered_refs
        )

    with (
        args.assembly_bom.open(newline="", encoding="utf-8") as bom_handle,
        args.assembly_placement.open(newline="", encoding="utf-8") as placement_handle,
    ):
        bom_refs = {row["Designator"] for row in csv.DictReader(bom_handle)}
        placement_refs = {row["Designator"] for row in csv.DictReader(placement_handle)}
    if bom_refs != placement_refs:
        raise ValueError("assembly BOM and placement reference sets differ")
    print(
        f"Generated matched assembly BOM/CPL for {len(bom_refs)} fitted SMD references"
    )


if __name__ == "__main__":
    main()
