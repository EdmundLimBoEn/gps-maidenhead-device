# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = 1
DATE_FORMATS = {"DD/MM", "MM/DD", "DDMMM", "YYYY-MM-DD"}
GNSS_MODES = {"single_fix", "tracking"}


class ConfigError(ValueError):
    """A stable, user-presentable configuration error."""


@dataclass(slots=True)
class DisplayBlock:
    kind: Literal["battery", "time", "date", "text", "space", "separator"]
    value: str = ""


@dataclass(slots=True)
class DeviceConfig:
    schema_version: int = SCHEMA_VERSION
    top_template: str = "GRID: {grid6}"
    bottom_blocks: list[DisplayBlock] = field(
        default_factory=lambda: [
            DisplayBlock("battery"),
            DisplayBlock("space", " "),
            DisplayBlock("time"),
            DisplayBlock("space", " "),
            DisplayBlock("date"),
        ]
    )
    timezone: str = "Asia/Singapore"
    clock_24h: bool = True
    show_seconds: bool = False
    date_format: str = "DD/MM"
    gnss_mode: str = "single_fix"
    tracking_interval_seconds: int = 5
    acquisition_timeout_seconds: int = 120
    dim_deadline_seconds: int = 60
    shutdown_deadline_seconds: int = 120
    normal_brightness_percent: int = 100
    dim_brightness_percent: int = 20

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DeviceConfig:
        allowed = set(cls.__dataclass_fields__)
        unknown = set(value) - allowed
        if unknown:
            raise ConfigError(f"unknown fields: {', '.join(sorted(unknown))}")
        data = dict(value)
        blocks = data.get("bottom_blocks")
        if blocks is not None:
            try:
                data["bottom_blocks"] = [DisplayBlock(**block) for block in blocks]
            except (TypeError, KeyError) as exc:
                raise ConfigError("invalid bottom_blocks") from exc
        try:
            config = cls(**data)
        except TypeError as exc:
            raise ConfigError(str(exc)) from exc
        config.validate()
        return config

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ConfigError("unsupported schema_version")
        if self.top_template != "GRID: {grid6}":
            raise ConfigError("top_template must be 'GRID: {grid6}' in V1")
        if self.gnss_mode not in GNSS_MODES:
            raise ConfigError("invalid gnss_mode")
        if self.date_format not in DATE_FORMATS:
            raise ConfigError("invalid date_format")
        if not self.timezone or len(self.timezone) > 64:
            raise ConfigError("invalid timezone")
        if self.tracking_interval_seconds < 5:
            raise ConfigError("tracking interval must be at least 5 seconds")
        if self.acquisition_timeout_seconds < 1:
            raise ConfigError("acquisition timeout must be positive")
        if self.dim_deadline_seconds < 0:
            raise ConfigError("dim deadline cannot be negative")
        if self.shutdown_deadline_seconds < self.dim_deadline_seconds:
            raise ConfigError("shutdown deadline cannot precede dim deadline")
        if self.acquisition_timeout_seconds > self.shutdown_deadline_seconds:
            raise ConfigError("acquisition timeout cannot exceed shutdown deadline")
        for name, value in (
            ("normal brightness", self.normal_brightness_percent),
            ("dim brightness", self.dim_brightness_percent),
        ):
            if not 0 <= value <= 100:
                raise ConfigError(f"{name} must be between 0 and 100")
        if self.dim_brightness_percent > self.normal_brightness_percent:
            raise ConfigError("dim brightness cannot exceed normal brightness")
        render_bottom(self, worst_case=True)


def _ascii_lcd(text: str) -> str:
    if any(ord(char) < 32 or ord(char) > 126 for char in text):
        raise ConfigError("display text must contain printable ASCII only")
    return text


def render_bottom(config: DeviceConfig, *, worst_case: bool = False) -> str:
    parts: list[str] = []
    for block in config.bottom_blocks:
        if block.kind == "battery":
            text = "#"
        elif block.kind == "time":
            if config.clock_24h:
                text = "23:59:59" if config.show_seconds else "23:59"
            else:
                text = "12:59:59 PM" if config.show_seconds else "12:59 PM"
        elif block.kind == "date":
            text = {
                "DD/MM": "31/12",
                "MM/DD": "12/31",
                "DDMMM": "31DEC",
                "YYYY-MM-DD": "2099-12-31",
            }[config.date_format]
        elif block.kind == "space":
            text = block.value or " "
            if set(text) != {" "}:
                raise ConfigError("space blocks may contain only spaces")
        elif block.kind == "separator":
            text = block.value
            if text not in {" ", "|", "/", "-", ":", "."}:
                raise ConfigError("unsupported separator")
        elif block.kind == "text":
            text = _ascii_lcd(block.value)
        else:
            raise ConfigError(f"unsupported display block: {block.kind}")
        parts.append(text)
    rendered = "".join(parts)
    if len(rendered) > 16:
        qualifier = "worst-case " if worst_case else ""
        raise ConfigError(f"{qualifier}bottom row is {len(rendered)} characters; maximum is 16")
    return rendered


def factory_config() -> DeviceConfig:
    config = DeviceConfig()
    config.validate()
    return config
