# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from maidenhead_configurator.models import (
    ConfigError,
    DeviceConfig,
    DisplayBlock,
    factory_config,
    render_bottom,
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
