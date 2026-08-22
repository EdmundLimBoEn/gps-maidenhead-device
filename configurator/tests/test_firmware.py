# SPDX-License-Identifier: GPL-3.0-or-later
import struct

import pytest

from maidenhead_configurator.firmware import FirmwareUpdater, find_rp2040_volumes
from maidenhead_configurator.protocol import Client, ProtocolError
from maidenhead_configurator.serial_transport import SerialDevice
from maidenhead_configurator.simulator import SimulatedTransport
from maidenhead_configurator.uf2 import (
    RP2040_FAMILY_ID,
    UF2_FLAG_FAMILY_ID_PRESENT,
    UF2_MAGIC_END,
    UF2_MAGIC_START0,
    UF2_MAGIC_START1,
)


def uf2_block() -> bytes:
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
        RP2040_FAMILY_ID,
    )
    struct.pack_into("<I", block, 508, UF2_MAGIC_END)
    return bytes(block)


def test_firmware_update_backs_up_before_copy(tmp_path) -> None:
    firmware = tmp_path / "firmware.uf2"
    firmware.write_bytes(uf2_block())
    volume = tmp_path / "RPI-RP2"
    volume.mkdir()
    copied = []
    updater = FirmwareUpdater(
        Client(SimulatedTransport()),
        volume_finder=lambda: [volume],
        copier=lambda src, dst: copied.append((src, dst)) or str(dst),
        sleeper=lambda _seconds: None,
    )
    result = updater.install(firmware, tmp_path / "backup.json", volume=volume)
    assert result.backup_path.exists()
    assert copied == [(firmware, volume / "firmware.uf2")]


def test_wait_for_volume_requests_recovery_instructions() -> None:
    updater = FirmwareUpdater(
        Client(SimulatedTransport()), volume_finder=list, sleeper=lambda _seconds: None
    )
    with pytest.raises(ProtocolError) as error:
        updater.wait_for_boot_volume(attempts=2)
    assert error.value.code == "boot_volume_not_found"


def test_multiple_boot_volumes_is_not_ambiguous(tmp_path) -> None:
    one, two = tmp_path / "RPI-RP2", tmp_path / "other" / "RPI-RP2"
    one.mkdir()
    two.mkdir(parents=True)
    updater = FirmwareUpdater(Client(SimulatedTransport()), volume_finder=lambda: [one, two])
    with pytest.raises(ProtocolError) as error:
        updater.wait_for_boot_volume(attempts=1)
    assert error.value.code == "multiple_boot_volumes"


def test_boot_volume_wait_excludes_drives_present_before_target_reboot(tmp_path) -> None:
    unrelated = tmp_path / "unrelated" / "RPI-RP2"
    target = tmp_path / "target" / "RPI-RP2"
    unrelated.mkdir(parents=True)
    target.mkdir(parents=True)
    updater = FirmwareUpdater(
        Client(SimulatedTransport()), volume_finder=lambda: [unrelated, target]
    )
    assert updater.wait_for_boot_volume(exclude=frozenset({unrelated}), attempts=1) == target


def test_find_rp2040_volumes_uses_immutable_label(tmp_path) -> None:
    valid, invalid = tmp_path / "RPI-RP2", tmp_path / "PICO"
    valid.mkdir()
    invalid.mkdir()
    assert find_rp2040_volumes([valid, invalid]) == [valid]


def test_find_rp2040_volume_accepts_windows_style_root_marker(tmp_path) -> None:
    volume = tmp_path / "drive-root"
    volume.mkdir()
    (volume / "INFO_UF2.TXT").write_text(
        "UF2 Bootloader v3.0\nBoard-ID: RPI-RP2\n", encoding="ascii"
    )
    assert find_rp2040_volumes([volume]) == [volume]


def test_manual_copy_requires_the_bootloader_volume(tmp_path) -> None:
    source = tmp_path / "firmware.uf2"
    source.write_bytes(uf2_block())
    updater = FirmwareUpdater(Client(SimulatedTransport()))
    with pytest.raises(ProtocolError) as error:
        updater.copy_uf2(source, tmp_path)
    assert error.value.code == "invalid_boot_volume"


def test_reconnect_rejects_ambiguous_devices() -> None:
    updater = FirmwareUpdater(
        Client(SimulatedTransport()),
        device_finder=lambda: [
            SerialDevice("COM1", "one"),
            SerialDevice("COM2", "two"),
        ],
    )
    with pytest.raises(ProtocolError) as error:
        updater.wait_for_reconnect(attempts=1, preexisting_devices=())
    assert error.value.code == "ambiguous_identity"


def test_reconnect_requires_identity_evidence() -> None:
    updater = FirmwareUpdater(Client(SimulatedTransport()), device_finder=list)
    with pytest.raises(ProtocolError) as error:
        updater.wait_for_reconnect(attempts=1)
    assert error.value.code == "identity_not_provided"


def test_reconnect_binds_to_expected_serial_and_ignores_other_devices() -> None:
    target = SerialDevice("COM7", "target", serial_number="target-serial")
    updater = FirmwareUpdater(
        Client(SimulatedTransport()),
        device_finder=lambda: [
            SerialDevice("COM1", "other", serial_number="other-serial"),
            target,
        ],
    )
    assert updater.wait_for_reconnect(expected_device=target, attempts=1) == target


def test_reconnect_does_not_trust_reused_port_without_usb_serial() -> None:
    selected = SerialDevice("COM7", "selected")
    replacement = SerialDevice("COM7", "different device")
    updater = FirmwareUpdater(Client(SimulatedTransport()), device_finder=lambda: [replacement])
    with pytest.raises(ProtocolError) as error:
        updater.wait_for_reconnect(expected_device=selected, attempts=1)
    assert error.value.code == "identity_unverifiable"


def test_recovery_reconnect_accepts_only_one_new_device() -> None:
    old = SerialDevice("COM1", "old", serial_number="old-serial")
    target = SerialDevice("COM7", "target", serial_number="target-serial")
    updater = FirmwareUpdater(Client(SimulatedTransport()), device_finder=lambda: [old, target])
    assert updater.wait_for_reconnect(preexisting_devices=(old,), attempts=1) == target
