# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True, slots=True)
class Transition:
    utc_epoch: int
    offset_seconds: int
    abbreviation: str


@dataclass(frozen=True, slots=True)
class TimezoneTable:
    zone_name: str
    generated_at: str
    expires_at: str
    expiry_year: int
    initial_offset_seconds: int
    initial_abbreviation: str
    transitions: tuple[Transition, ...]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["transitions"] = [asdict(item) for item in self.transitions]
        return value


def _state(at: datetime, zone: ZoneInfo) -> tuple[int, str]:
    local = at.astimezone(zone)
    offset = local.utcoffset()
    if offset is None:
        raise ValueError("time zone returned no UTC offset")
    return int(offset.total_seconds()), local.tzname() or ""


def _locate_transition(low: datetime, high: datetime, zone: ZoneInfo) -> datetime:
    old_state = _state(low, zone)
    while high - low > timedelta(seconds=1):
        midpoint = low + (high - low) / 2
        midpoint = midpoint.replace(microsecond=0)
        if _state(midpoint, zone) == old_state:
            low = midpoint
        else:
            high = midpoint
    return high.replace(microsecond=0)


def generate_timezone_table(
    zone_name: str, *, generated_at: datetime | None = None, years: int = 15
) -> TimezoneTable:
    if years < 15:
        raise ValueError("transition tables must cover at least 15 years")
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown IANA time zone: {zone_name}") from exc
    start = (generated_at or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    try:
        end = start.replace(year=start.year + years)
    except ValueError:
        end = start.replace(month=2, day=28, year=start.year + years)
    initial_offset, initial_abbreviation = _state(start, zone)
    transitions: list[Transition] = []
    cursor = start
    cursor_state = _state(cursor, zone)
    step = timedelta(hours=6)
    while cursor < end:
        sample = min(cursor + step, end)
        sample_state = _state(sample, zone)
        if sample_state != cursor_state:
            instant = _locate_transition(cursor, sample, zone)
            offset, abbreviation = _state(instant, zone)
            transitions.append(Transition(int(instant.timestamp()), offset, abbreviation))
            cursor_state = (offset, abbreviation)
        cursor = sample
    return TimezoneTable(
        zone_name,
        start.isoformat(),
        end.isoformat(),
        end.year,
        initial_offset,
        initial_abbreviation,
        tuple(transitions),
    )
