# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FLAG_FAMILY_ID_PRESENT = 0x00002000
RP2040_FAMILY_ID = 0xE48BFF56
BLOCK_SIZE = 512


@dataclass(frozen=True, slots=True)
class Uf2Info:
    block_count: int
    family_id: int | None
    payload_bytes: int


def inspect_uf2(path: str | Path) -> Uf2Info:
    content = Path(path).read_bytes()
    if not content or len(content) % BLOCK_SIZE:
        raise ValueError("UF2 file must contain complete 512-byte blocks")
    expected_blocks = len(content) // BLOCK_SIZE
    family_id: int | None = None
    payload_total = 0
    seen: set[int] = set()
    for offset in range(0, len(content), BLOCK_SIZE):
        block = content[offset : offset + BLOCK_SIZE]
        start0, start1, flags, _address, payload_size, number, total, family = struct.unpack_from(
            "<IIIIIIII", block
        )
        end_magic = struct.unpack_from("<I", block, 508)[0]
        if (start0, start1, end_magic) != (UF2_MAGIC_START0, UF2_MAGIC_START1, UF2_MAGIC_END):
            raise ValueError("invalid UF2 magic")
        if total != expected_blocks or number >= total or number in seen:
            raise ValueError("invalid UF2 block numbering")
        if payload_size > 476:
            raise ValueError("UF2 payload is too large")
        seen.add(number)
        payload_total += payload_size
        if flags & UF2_FLAG_FAMILY_ID_PRESENT:
            if family_id is not None and family_id != family:
                raise ValueError("UF2 contains inconsistent family IDs")
            family_id = family
    if family_id != RP2040_FAMILY_ID:
        raise ValueError("UF2 is not marked for RP2040")
    return Uf2Info(expected_blocks, family_id, payload_total)
