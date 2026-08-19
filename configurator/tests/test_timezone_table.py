# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import UTC, datetime

import pytest

from maidenhead_configurator.timezone_table import generate_timezone_table

START = datetime(2026, 8, 19, tzinfo=UTC)


def test_singapore_has_no_transitions() -> None:
    table = generate_timezone_table("Asia/Singapore", generated_at=START)
    assert table.initial_offset_seconds == 8 * 3600
    assert table.transitions == ()
    assert table.expiry_year == 2041


def test_new_york_contains_forward_and_back_transitions() -> None:
    table = generate_timezone_table("America/New_York", generated_at=START)
    offsets = {item.offset_seconds for item in table.transitions}
    assert offsets == {-5 * 3600, -4 * 3600}
    assert len(table.transitions) >= 28


def test_quarter_hour_zone() -> None:
    table = generate_timezone_table("Asia/Kathmandu", generated_at=START)
    assert table.initial_offset_seconds == 5 * 3600 + 45 * 60


def test_less_than_fifteen_years_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 15"):
        generate_timezone_table("UTC", generated_at=START, years=14)
