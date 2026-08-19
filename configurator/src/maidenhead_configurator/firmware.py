# SPDX-License-Identifier: GPL-3.0-or-later
"""Safe UF2 update/recovery helpers independent from the Tk user interface."""
from __future__ import annotations

import shutil
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


def find_rp2040_volumes(mounts: list[Path] | None = None) -> list[Path]:
    """Find mounted RP2040 ROM bootloader disks by their immutable RPI-RP2 name."""
    if mounts is None:
        candidates = [Path("/media"), Path("/run/media"), Path("/Volumes"), Path("/mnt")]
        mounts = []
        for root in candidates:
            if root.exists():
                mounts.extend(
                    path for path in root.rglob("*") if path.is_dir() and path.name.upper() == "RPI-RP2"
                )
    return sorted({Path(path) for path in mounts if Path(path).name.upper() == "RPI-RP2"})


class FirmwareUpdater:
    def __init__(
        self,
        client: Client,
        *,
        volume_finder: Callable[[], list[Path]] = find_rp2040_volumes,
        device_finder: Callable[[], list[SerialDevice]] = discover_devices,
        copier: Callable[[str | Path, str | Path], str] = shutil.copy2,
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

    def wait_for_boot_volume(self, *, attempts: int = 20, interval_seconds: float = 0.5) -> Path:
        for _ in range(attempts):
            volumes = self._volume_finder()
            if len(volumes) == 1:
                return volumes[0]
            if len(volumes) > 1:
                raise ProtocolError("multiple_boot_volumes", "more than one RPI-RP2 volume is connected")
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
            self.enter_bootloader()
            volume = self.wait_for_boot_volume()
        destination = self.copy_uf2(source, volume)
        return UpdateResult(backup, info, volume, destination)

    def copy_uf2(self, uf2_path: str | Path, volume: Path) -> Path:
        """Copy a pre-validated file to an explicitly selected RPI-RP2 volume."""
        source = Path(uf2_path)
        if volume.name.upper() != "RPI-RP2" or not volume.is_dir():
            raise ProtocolError("invalid_boot_volume", "select the mounted RPI-RP2 bootloader volume")
        destination = volume / source.name
        try:
            self._copier(source, destination)
        except OSError as exc:
            raise ProtocolError(
                "uf2_copy_failed", f"could not copy firmware to {volume}: {exc}"
            ) from exc
        return destination

    def wait_for_reconnect(
        self, *, attempts: int = 20, interval_seconds: float = 0.5
    ) -> SerialDevice:
        for _ in range(attempts):
            devices = self._device_finder()
            if devices:
                return devices[0]
            self._sleeper(interval_seconds)
        raise ProtocolError("reconnect_timeout", "firmware copied, but the USB configurator did not reconnect")
