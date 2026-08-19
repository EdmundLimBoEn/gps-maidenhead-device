# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import UTC, datetime

import pytest

from maidenhead_configurator.models import (
    ConfigError,
    DeviceConfig,
    DisplayBlock,
    factory_config,
    render_bottom,
    reorder_blocks,
)


def test_factory_defaults_fit_lcd() -> None:
    config = factory_config()
    assert config.timezone == "Asia/Singapore"
    assert render_bottom(config) == "# 23:59 31/12"
    assert len(render_bottom(config)) == 13


def test_worst_case_12_hour_seconds_is_rejected() -> None:
    config = factory_config()
    config.clock_24h = False
    config.show_seconds = True
    with pytest.raises(ConfigError, match="maximum is 16"):
        config.validate()


def test_shutdown_cannot_precede_dim() -> None:
    config = factory_config()
    config.shutdown_deadline_seconds = 59
    with pytest.raises(ConfigError, match="cannot precede"):
        config.validate()


def test_acquisition_timeout_cannot_exceed_shutdown() -> None:
    config = factory_config()
    config.acquisition_timeout_seconds = 121
    with pytest.raises(ConfigError, match="cannot exceed"):
        config.validate()


def test_unicode_static_text_is_rejected() -> None:
    config = factory_config()
    config.bottom_blocks = [DisplayBlock("text", "CQ ☃")]
    with pytest.raises(ConfigError, match="printable ASCII"):
        config.validate()


def test_unknown_config_fields_are_rejected() -> None:
    value = factory_config().to_dict()
    value["future_setting"] = True
    with pytest.raises(ConfigError, match="unknown fields"):
        DeviceConfig.from_dict(value)


def test_device_payload_regenerates_a_fifteen_year_timezone_table() -> None:
    payload = factory_config().to_device_dict(generated_at=datetime(2026, 8, 19, tzinfo=UTC))
    table = payload["timezone_table"]
    assert table["zone_name"] == "Asia/Singapore"
    assert table["expiry_year"] == 2041
    assert table["expires_at"] == "2041-08-19T00:00:00+00:00"
    assert table["transitions"] == []
    DeviceConfig.from_dict(payload).validate_device_payload()


def test_device_payload_rejects_missing_timezone_table() -> None:
    with pytest.raises(ConfigError, match="timezone_table is required"):
        factory_config().validate_device_payload()


def test_device_payload_replaces_a_stale_table_after_zone_edit() -> None:
    config = factory_config()
    config.timezone = "America/New_York"
    config = DeviceConfig.from_dict(config.to_device_dict(generated_at=datetime(2026, 8, 19, tzinfo=UTC)))
    config.timezone = "Asia/Singapore"
    assert config.to_device_dict(generated_at=datetime(2026, 8, 19, tzinfo=UTC))["timezone_table"][
        "zone_name"
    ] == "Asia/Singapore"


def test_reorder_blocks_moves_item_and_keeps_new_selection() -> None:
    blocks = [DisplayBlock("text", "A"), DisplayBlock("text", "B"), DisplayBlock("text", "C")]
    assert reorder_blocks(blocks, 0, 2) == 2
    assert [block.value for block in blocks] == ["B", "C", "A"]


def test_reorder_blocks_rejects_indices_outside_the_list() -> None:
    with pytest.raises(IndexError, match="out of range"):
        reorder_blocks([DisplayBlock("text", "A")], 0, 1)


def test_timezone_table_abbreviation_must_not_be_empty() -> None:
    payload = factory_config().to_device_dict(generated_at=datetime(2026, 8, 19, tzinfo=UTC))
    payload["timezone_table"]["initial_abbreviation"] = ""
    with pytest.raises(ConfigError, match="abbreviation"):
        DeviceConfig.from_dict(payload).validate_device_payload()
