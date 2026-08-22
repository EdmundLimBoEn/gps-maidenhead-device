# SPDX-License-Identifier: GPL-3.0-or-later
"""Safe UF2 update/recovery helpers independent from the Tk user interface."""

from __future__ import annotations

import shutil
import string
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .profiles import Profile, save_profile
from .protocol import Client, ProtocolError
from .serial_transport import SerialDevice, discover_devices
from .uf2 import Uf2Info, inspect_uf2


@dataclass(frozen=True, slots=True)
class UpdateResult:
    backup_path: Path
    uf2: Uf2Info
    volume: Path
    destination: Path


def is_rp2040_volume(path: Path) -> bool:
    """Recognize ROM BOOTSEL volumes, including Windows drive roots."""
    if not path.is_dir():
        return False
    if path.name.upper() == "RPI-RP2":
        return True
    try:
        info = (path / "INFO_UF2.TXT").read_text(encoding="ascii", errors="ignore")[:1024]
    except OSError:
        return False
    upper = info.upper()
    return "BOARD-ID:" in upper and ("RP2" in upper or "RPI-RP2" in upper)


def find_rp2040_volumes(mounts: list[Path] | None = None) -> list[Path]:
    """Find mounted RP2040 ROM bootloader disks by their immutable RPI-RP2 name."""
    if mounts is None:
        candidates = [Path("/media"), Path("/run/media"), Path("/Volumes"), Path("/mnt")]
        mounts = []
        if sys.platform == "win32":
            mounts.extend(Path(f"{letter}:\\") for letter in string.ascii_uppercase)
        for root in candidates:
            if root.exists():
                mounts.extend(path for path in root.rglob("*") if is_rp2040_volume(path))
    return sorted({Path(path) for path in mounts if is_rp2040_volume(Path(path))})


class FirmwareUpdater:
    def __init__(
        self,
        client: Client,
        *,
        volume_finder: Callable[[], list[Path]] = find_rp2040_volumes,
        device_finder: Callable[[], list[SerialDevice]] = discover_devices,
        copier: Callable[[str | Path, str | Path], str] = shutil.copyfile,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.client = client
        self._volume_finder = volume_finder
        self._device_finder = device_finder
        self._copier = copier
        self._sleeper = sleeper

    def backup_profile(
        self, path: str | Path, *, notes: str = "Automatic pre-update backup"
    ) -> Path:
        destination = Path(path)
        config = self.client.request("get_config")
        from .models import DeviceConfig

        save_profile(Profile(DeviceConfig.from_dict(config), notes=notes), destination)
        return destination

    def enter_bootloader(self) -> None:
        self.client.request("reboot_to_bootloader")

    def snapshot_boot_volumes(self) -> frozenset[Path]:
        return frozenset(self._volume_finder())

    def snapshot_devices(self) -> tuple[SerialDevice, ...]:
        return tuple(self._device_finder())

    def wait_for_boot_volume(
        self,
        *,
        attempts: int = 20,
        interval_seconds: float = 0.5,
        exclude: frozenset[Path] = frozenset(),
    ) -> Path:
        for _ in range(attempts):
            volumes = [volume for volume in self._volume_finder() if volume not in exclude]
            if len(volumes) == 1:
                return volumes[0]
            if len(volumes) > 1:
                raise ProtocolError(
                    "multiple_boot_volumes", "more than one RPI-RP2 volume is connected"
                )
            self._sleeper(interval_seconds)
        raise ProtocolError(
            "boot_volume_not_found", "RPI-RP2 was not found; hold BOOTSEL while plugging in USB"
        )

    def install(
        self, uf2_path: str | Path, backup_path: str | Path, *, volume: Path | None = None
    ) -> UpdateResult:
        source = Path(uf2_path)
        info = inspect_uf2(source)
        backup = self.backup_profile(backup_path)
        if volume is None:
            existing = self.snapshot_boot_volumes()
            self.enter_bootloader()
            volume = self.wait_for_boot_volume(exclude=existing)
        destination = self.copy_uf2(source, volume)
        return UpdateResult(backup, info, volume, destination)

    def copy_uf2(self, uf2_path: str | Path, volume: Path) -> Path:
        """Copy a pre-validated file to an explicitly selected RPI-RP2 volume."""
        source = Path(uf2_path)
        if not is_rp2040_volume(volume):
            raise ProtocolError(
                "invalid_boot_volume", "select the mounted RPI-RP2 bootloader volume"
            )
        destination = volume / source.name
        try:
            self._copier(source, destination)
        except OSError as exc:
            raise ProtocolError(
                "uf2_copy_failed", f"could not copy firmware to {volume}: {exc}"
            ) from exc
        return destination

    def wait_for_reconnect(
        self,
        *,
        attempts: int = 20,
        interval_seconds: float = 0.5,
        expected_device: SerialDevice | None = None,
        preexisting_devices: tuple[SerialDevice, ...] | None = None,
        boot_volume: Path | None = None,
    ) -> SerialDevice:
        if expected_device is None and preexisting_devices is None:
            raise ProtocolError(
                "identity_not_provided",
                "cannot prove which serial device rebooted; select the target explicitly",
            )
        if expected_device is not None and not expected_device.serial_number:
            raise ProtocolError(
                "identity_unverifiable",
                "firmware was copied, but this device has no stable USB serial identity; reconnect and select it explicitly",
            )
        baseline = {(item.port, item.serial_number) for item in (preexisting_devices or ())}
        for _ in range(attempts):
            if boot_volume is not None and boot_volume in self._volume_finder():
                self._sleeper(interval_seconds)
                continue
            devices = self._device_finder()
            if expected_device is not None:
                matches = [
                    item for item in devices if item.serial_number == expected_device.serial_number
                ]
                if len(matches) == 1:
                    return matches[0]
                if len(matches) > 1:
                    raise ProtocolError(
                        "ambiguous_identity", "multiple serial devices match the target identity"
                    )
            else:
                matches = [
                    item for item in devices if (item.port, item.serial_number) not in baseline
                ]
                if len(matches) == 1:
                    return matches[0]
                if len(matches) <= 1:
                    self._sleeper(interval_seconds)
                    continue
                raise ProtocolError(
                    "ambiguous_identity",
                    "multiple new serial devices appeared; select the target explicitly",
                )
            self._sleeper(interval_seconds)
        if expected_device is not None:
            raise ProtocolError(
                "identity_not_reestablished",
                "firmware copied, but the selected device identity did not reconnect",
            )
        raise ProtocolError(
            "reconnect_timeout", "firmware copied, but no provably new USB device reconnected"
        )
