# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import DeviceConfig

PROFILE_SCHEMA_VERSION = 1


@dataclass(slots=True)
class Profile:
    config: DeviceConfig
    notes: str = ""
    profile_schema_version: int = PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_schema_version": self.profile_schema_version,
            "config": self.config.to_dict(),
            "notes": self.notes,
        }


def load_profile(path: str | Path) -> Profile:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("profile root must be an object")
    version = raw.get("profile_schema_version")
    if version != PROFILE_SCHEMA_VERSION:
        raise ValueError(f"unsupported profile schema version: {version!r}")
    unknown = set(raw) - {"profile_schema_version", "config", "notes"}
    if unknown:
        raise ValueError(f"unknown profile fields: {', '.join(sorted(unknown))}")
    if "coordinates" in raw or "diagnostics" in raw:
        raise ValueError("profiles cannot contain transient location data")
    return Profile(DeviceConfig.from_dict(raw["config"]), str(raw.get("notes", "")))


def save_profile(profile: Profile, path: str | Path) -> None:
    profile.config.validate()
    Path(path).write_text(json.dumps(profile.to_dict(), indent=2) + "\n", encoding="utf-8")


def profile_diff(current: DeviceConfig, proposed: DeviceConfig) -> dict[str, tuple[Any, Any]]:
    before, after = current.to_dict(), proposed.to_dict()
    return {key: (before[key], after[key]) for key in before if before[key] != after[key]}
