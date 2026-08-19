# SPDX-License-Identifier: GPL-3.0-or-later
import struct

import pytest

from maidenhead_configurator.uf2 import (
    RP2040_FAMILY_ID,
    UF2_FLAG_FAMILY_ID_PRESENT,
    UF2_MAGIC_END,
    UF2_MAGIC_START0,
    UF2_MAGIC_START1,
    inspect_uf2,
)


def make_block(family: int = RP2040_FAMILY_ID) -> bytes:
    block = bytearray(512)
    struct.pack_into(
        "<IIIIIIII",
        block,
        0,
        UF2_MAGIC_START0,
        UF2_MAGIC_START1,
        UF2_FLAG_FAMILY_ID_PRESENT,
        0x10000000,
        256,
        0,
        1,
        family,
    )
    struct.pack_into("<I", block, 508, UF2_MAGIC_END)
    return bytes(block)


def test_valid_rp2040_uf2(tmp_path) -> None:
    path = tmp_path / "firmware.uf2"
    path.write_bytes(make_block())
    info = inspect_uf2(path)
    assert info.block_count == 1
    assert info.payload_bytes == 256


def test_wrong_family_is_rejected(tmp_path) -> None:
    path = tmp_path / "wrong.uf2"
    path.write_bytes(make_block(0x12345678))
    with pytest.raises(ValueError, match="not marked for RP2040"):
        inspect_uf2(path)


def test_truncated_file_is_rejected(tmp_path) -> None:
    path = tmp_path / "truncated.uf2"
    path.write_bytes(make_block()[:-1])
    with pytest.raises(ValueError, match="complete"):
        inspect_uf2(path)
