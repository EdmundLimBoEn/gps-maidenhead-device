# SPDX-License-Identifier: GPL-3.0-or-later
import json

import pytest

from maidenhead_configurator.protocol import Client, ProtocolError
from maidenhead_configurator.serial_transport import NdjsonSerialTransport, discover_devices


class Port:
    def __init__(self, device, description="Maidenhead Pocket Locator", vid=0x2E8A, pid=0x000A):
        self.device = device
        self.description = description
        self.vid = vid
        self.pid = pid
        self.manufacturer = "Raspberry Pi"
        self.product = "RP2040"
        self.serial_number = "unit-1"


class FakeSerial:
    def __init__(self, responses):
        self.responses = list(responses)
        self.writes = []
        self.closed = False

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def flush(self):
        pass

    def readline(self, _limit):
        return self.responses.pop(0) if self.responses else b""

    def close(self):
        self.closed = True


def test_discovery_filters_unrelated_ports_and_sorts() -> None:
    devices = discover_devices(
        [Port("/dev/ttyB"), Port("/dev/ttyA"), Port("/dev/ttyUSB0", "Arduino", 0x2341, 1)]
    )
    assert [item.port for item in devices] == ["/dev/ttyA", "/dev/ttyB"]
    assert (
        discover_devices([Port("/dev/ttyUSB0", "Arduino", 0x2341, 1)], include_unknown=True)[0].port
        == "/dev/ttyUSB0"
    )


def test_ndjson_transport_round_trip_ignores_unsolicited_events() -> None:
    fake = FakeSerial(
        [b'{"event":"gnss"}\n', b'{"request_id":"1","ok":true,"data":{"device":"ok"}}\n']
    )
    transport = NdjsonSerialTransport("fake", serial_factory=lambda **_kwargs: fake)
    assert Client(transport).request("hello") == {"device": "ok"}
    assert json.loads(fake.writes[0]) == {
        "protocol_version": 1,
        "request_id": "1",
        "command": "hello",
    }
    transport.close()
    assert fake.closed


@pytest.mark.parametrize("response, code", [(b"not-json\n", "invalid_response"), (b"", "timeout")])
def test_ndjson_transport_reports_safe_errors(response, code) -> None:
    fake = FakeSerial([response])
    transport = NdjsonSerialTransport("fake", serial_factory=lambda **_kwargs: fake)
    with pytest.raises(ProtocolError) as error:
        Client(transport).request("hello")
    assert error.value.code == code


def test_ndjson_transport_rejects_unterminated_response() -> None:
    transport = NdjsonSerialTransport("fake", serial_factory=lambda **_kwargs: FakeSerial([b"{}"]))
    with pytest.raises(ProtocolError, match="newline"):
        Client(transport).request("hello")
