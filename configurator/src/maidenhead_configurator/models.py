# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

SCHEMA_VERSION = 1
DATE_FORMATS = {"DD/MM", "MM/DD", "DDMMM", "YYYY-MM-DD"}
GNSS_MODES = {"single_fix", "tracking"}
MAX_TIMEZONE_TRANSITIONS = 48
MAX_TIMEZONE_ABBREVIATION_BYTES = 8


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
    # This is device state rather than profile state. The host regenerates it
    # immediately before writes so a saved profile never fossilizes old DST data.
    timezone_table: dict[str, Any] | None = field(default=None, repr=False, compare=False)

    def to_dict(self, *, include_timezone_table: bool = False) -> dict[str, Any]:
        value = asdict(self)
        if not include_timezone_table or value["timezone_table"] is None:
            value.pop("timezone_table")
        return value

    def to_device_dict(self, *, generated_at: datetime | None = None) -> dict[str, Any]:
        """Return a write payload with a fresh 15-year named-zone table."""
        # Imported here to keep the base schema usable without zoneinfo data.
        from .timezone_table import generate_timezone_table

        generated_at = generated_at or datetime.now(UTC)
        value = self.to_dict()
        # A configuration read from a device can carry an older table for a
        # different zone while a caller is editing the zone. Validate settings
        # without that derived state, then replace it below.
        DeviceConfig.from_dict(value).validate()
        value["timezone_table"] = generate_timezone_table(
            self.timezone, generated_at=generated_at
        ).to_dict()
        DeviceConfig.from_dict(value).validate_device_payload()
        return value

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
        if not isinstance(self.bottom_blocks, list):
            raise ConfigError("bottom_blocks must be a list")
        render_bottom(self, worst_case=True)
        if self.timezone_table is not None:
            self._validate_timezone_table(self.timezone_table)

    def validate_device_payload(self) -> None:
        self.validate()
        if self.timezone_table is None:
            raise ConfigError("timezone_table is required when writing a device configuration")

    def _validate_timezone_table(self, table: dict[str, Any]) -> None:
        if not isinstance(table, dict):
            raise ConfigError("timezone_table must be an object")
        expected = {
            "zone_name",
            "generated_at",
            "expires_at",
            "expiry_year",
            "initial_offset_seconds",
            "initial_abbreviation",
            "transitions",
        }
        unknown = set(table) - expected
        missing = expected - set(table)
        if unknown or missing:
            details = [*([f"unknown fields: {', '.join(sorted(unknown))}"] if unknown else []), *([f"missing fields: {', '.join(sorted(missing))}"] if missing else [])]
            raise ConfigError("invalid timezone_table (" + "; ".join(details) + ")")
        if table["zone_name"] != self.timezone:
            raise ConfigError("timezone_table zone does not match timezone")
        try:
            generated = datetime.fromisoformat(str(table["generated_at"]))
            expires = datetime.fromisoformat(str(table["expires_at"]))
        except ValueError as exc:
            raise ConfigError("timezone_table generation or expiry timestamp is invalid") from exc
        if generated.tzinfo is None or expires.tzinfo is None:
            raise ConfigError("timezone_table timestamps must include an offset")
        generated_utc = generated.astimezone(UTC)
        expires_utc = expires.astimezone(UTC)
        try:
            required_expiry = generated_utc.replace(year=generated_utc.year + 15)
        except ValueError:
            required_expiry = generated_utc.replace(month=2, day=28, year=generated_utc.year + 15)
        if expires_utc < required_expiry:
            raise ConfigError("timezone_table must cover at least 15 years")
        expiry = table["expiry_year"]
        if not isinstance(expiry, int) or expiry != expires_utc.year:
            raise ConfigError("timezone_table expiry_year does not match expires_at")
        self._validate_timezone_state(table["initial_offset_seconds"], table["initial_abbreviation"])
        transitions = table["transitions"]
        if not isinstance(transitions, list):
            raise ConfigError("timezone_table transitions must be a list")
        if len(transitions) > MAX_TIMEZONE_TRANSITIONS:
            raise ConfigError(f"timezone_table has more than {MAX_TIMEZONE_TRANSITIONS} transitions")
        previous_epoch: int | None = None
        for transition in transitions:
            if not isinstance(transition, dict) or set(transition) != {
                "utc_epoch", "offset_seconds", "abbreviation"
            }:
                raise ConfigError("invalid timezone transition")
            epoch = transition["utc_epoch"]
            if not isinstance(epoch, int) or (previous_epoch is not None and epoch <= previous_epoch):
                raise ConfigError("timezone transitions must have increasing UTC epochs")
            self._validate_timezone_state(transition["offset_seconds"], transition["abbreviation"])
            previous_epoch = epoch

    @staticmethod
    def _validate_timezone_state(offset: Any, abbreviation: Any) -> None:
        if not isinstance(offset, int) or not -12 * 3600 <= offset <= 14 * 3600:
            raise ConfigError("timezone offset is out of range")
        if not isinstance(abbreviation, str) or not abbreviation:
            raise ConfigError("timezone abbreviation is invalid")
        try:
            encoded = abbreviation.encode("ascii", "strict")
        except UnicodeEncodeError as exc:
            raise ConfigError("timezone abbreviation is invalid") from exc
        if len(encoded) > MAX_TIMEZONE_ABBREVIATION_BYTES:
            raise ConfigError("timezone abbreviation is invalid")


def _ascii_lcd(text: str) -> str:
    if not isinstance(text, str):
        raise ConfigError("display text must be a string")
    if any(ord(char) < 32 or ord(char) > 126 for char in text):
        raise ConfigError("display text must contain printable ASCII only")
    return text


def render_bottom(config: DeviceConfig, *, worst_case: bool = False) -> str:
    parts: list[str] = []
    for block in config.bottom_blocks:
        if not isinstance(block, DisplayBlock):
            raise ConfigError("bottom_blocks contains an invalid block")
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


def reorder_blocks(blocks: list[DisplayBlock], source_index: int, target_index: int) -> int:
    """Move one display block and return its new selected index.

    Kept independent of Tk so both buttons and in-window drag-and-drop share
    the same boundary-checked behavior.
    """
    if not 0 <= source_index < len(blocks) or not 0 <= target_index < len(blocks):
        raise IndexError("display block index is out of range")
    if source_index == target_index:
        return source_index
    block = blocks.pop(source_index)
    blocks.insert(target_index, block)
    return target_index


def factory_config() -> DeviceConfig:
    config = DeviceConfig()
    config.validate()
    return config
