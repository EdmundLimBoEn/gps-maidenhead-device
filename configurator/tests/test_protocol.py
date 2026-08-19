# SPDX-License-Identifier: GPL-3.0-or-later
import json
from datetime import UTC, datetime

import pytest

from maidenhead_configurator.models import factory_config
from maidenhead_configurator.protocol import Client, ProtocolError
from maidenhead_configurator.simulator import SimulatedTransport


def test_transactional_config_round_trip() -> None:
    client = Client(SimulatedTransport())
    config = factory_config()
    config.gnss_mode = "tracking"
    payload = config.to_device_dict()
    client.request("validate_config", config=payload)
    saved = client.request("set_config", config=payload)
    assert saved == client.request("get_config")
    assert saved["gnss_mode"] == "tracking"
    assert saved["timezone_table"]["zone_name"] == "Asia/Singapore"


def test_invalid_config_does_not_replace_current() -> None:
    transport = SimulatedTransport()
    client = Client(transport)
    invalid = factory_config().to_device_dict()
    invalid["shutdown_deadline_seconds"] = 1
    with pytest.raises(ProtocolError) as error:
        client.request("set_config", config=invalid)
    assert error.value.code == "invalid_config"
    assert client.request("get_config")["shutdown_deadline_seconds"] == 120


def test_factory_reset_restores_defaults() -> None:
    client = Client(SimulatedTransport())
    config = factory_config()
    config.gnss_mode = "tracking"
    client.request("set_config", config=config.to_device_dict())
    assert client.request("factory_reset") == factory_config().to_dict()


def test_device_rejects_a_profile_payload_without_generated_transitions() -> None:
    with pytest.raises(ProtocolError) as error:
        Client(SimulatedTransport()).request("set_config", config=factory_config().to_dict())
    assert error.value.code == "invalid_config"


def test_worst_common_zone_write_stays_under_protocol_limit() -> None:
    config = factory_config()
    config.timezone = "America/New_York"
    payload = config.to_device_dict(generated_at=datetime(2026, 8, 19, tzinfo=UTC))
    request = {"protocol_version": 1, "request_id": "1", "command": "set_config", "config": payload}
    assert len(json.dumps(request, separators=(",", ":")).encode()) < 4096


def test_client_rejects_unknown_command() -> None:
    with pytest.raises(ProtocolError) as error:
        Client(SimulatedTransport()).request("erase_everything")
    assert error.value.code == "unknown_command"
