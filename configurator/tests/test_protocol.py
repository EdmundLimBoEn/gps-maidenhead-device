# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from maidenhead_configurator.models import factory_config
from maidenhead_configurator.protocol import Client, ProtocolError
from maidenhead_configurator.simulator import SimulatedTransport


def test_transactional_config_round_trip() -> None:
    client = Client(SimulatedTransport())
    config = factory_config()
    config.gnss_mode = "tracking"
    client.request("validate_config", config=config.to_dict())
    saved = client.request("set_config", config=config.to_dict())
    assert saved == client.request("get_config")
    assert saved["gnss_mode"] == "tracking"


def test_invalid_config_does_not_replace_current() -> None:
    transport = SimulatedTransport()
    client = Client(transport)
    invalid = factory_config().to_dict()
    invalid["shutdown_deadline_seconds"] = 1
    with pytest.raises(ProtocolError) as error:
        client.request("set_config", config=invalid)
    assert error.value.code == "invalid_config"
    assert client.request("get_config")["shutdown_deadline_seconds"] == 120


def test_factory_reset_restores_defaults() -> None:
    client = Client(SimulatedTransport())
    config = factory_config()
    config.gnss_mode = "tracking"
    client.request("set_config", config=config.to_dict())
    assert client.request("factory_reset") == factory_config().to_dict()


def test_client_rejects_unknown_command() -> None:
    with pytest.raises(ProtocolError) as error:
        Client(SimulatedTransport()).request("erase_everything")
    assert error.value.code == "unknown_command"
