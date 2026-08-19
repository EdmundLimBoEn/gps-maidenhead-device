# SPDX-License-Identifier: GPL-3.0-or-later
"""CDC serial discovery and newline-delimited JSON transport for real devices."""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Self

from .protocol import MAX_MESSAGE_BYTES, ProtocolError, Transport

try:  # Keep the simulator usable if pyserial was not installed yet.
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - exercised by installations without optional runtime dep
    serial = None
    list_ports = None


RP2040_VID = 0x2E8A
KNOWN_PRODUCT_IDS = {0x000A, 0x000C}


@dataclass(frozen=True, slots=True)
class SerialDevice:
    port: str
    label: str
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None


def discover_devices(
    ports: Iterable[Any] | None = None, *, include_unknown: bool = False
) -> list[SerialDevice]:
    """Return likely Pocket Locator CDC devices, deterministically sorted by port."""
    if ports is None:
        if list_ports is None:
            raise ProtocolError("pyserial_missing", "pyserial is required to discover USB devices")
        ports = list_ports.comports()
    found: list[SerialDevice] = []
    for item in ports:
        vid, pid = getattr(item, "vid", None), getattr(item, "pid", None)
        text = " ".join(
            str(value or "")
            for value in (
                getattr(item, "description", ""),
                getattr(item, "manufacturer", ""),
                getattr(item, "product", ""),
            )
        ).lower()
        likely = vid == RP2040_VID or "maidenhead" in text or "pocket locator" in text
        if not likely and not include_unknown:
            continue
        port = str(item.device)
        identity = (
            getattr(item, "description", None)
            or getattr(item, "product", None)
            or "USB serial device"
        )
        found.append(
            SerialDevice(
                port, f"{port} — {identity}", vid, pid, getattr(item, "serial_number", None)
            )
        )
    return sorted(found, key=lambda device: device.port)


class NdjsonSerialTransport(Transport):
    """One request / one response serial transport; unsolicited lines are ignored."""

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 115200,
        timeout: float = 2.0,
        serial_factory: Callable[..., Any] | None = None,
    ) -> None:
        if serial_factory is None:
            if serial is None:
                raise ProtocolError("pyserial_missing", "pyserial is required for USB configuration")
            serial_factory = serial.Serial
        try:
            self._serial = serial_factory(port=port, baudrate=baudrate, timeout=timeout, write_timeout=timeout)
        except Exception as exc:
            raise ProtocolError("port_open_failed", f"could not open {port}: {exc}") from exc
        self.port = port
        self.timeout = timeout

    def close(self) -> None:
        close = getattr(self._serial, "close", None)
        if close:
            close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def transact(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            line = json.dumps(request, separators=(",", ":")).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as exc:
            raise ProtocolError("encode_failed", str(exc)) from exc
        if len(line) > MAX_MESSAGE_BYTES:
            raise ProtocolError("message_too_large", "request exceeds protocol limit")
        try:
            self._serial.write(line)
            self._serial.flush()
            while True:
                received = self._serial.readline(MAX_MESSAGE_BYTES + 1)
                if not received:
                    raise ProtocolError("timeout", f"no response from {self.port}")
                if len(received) > MAX_MESSAGE_BYTES or not received.endswith(b"\n"):
                    raise ProtocolError("invalid_response", "device response is too large or not newline terminated")
                try:
                    decoded = json.loads(received.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ProtocolError("invalid_response", "device returned invalid JSON") from exc
                if not isinstance(decoded, dict):
                    raise ProtocolError("invalid_response", "device response must be an object")
                # Firmware may emit status events, but only the matching response ends this transaction.
                if decoded.get("request_id") == request.get("request_id"):
                    return decoded
        except ProtocolError:
            raise
        except Exception as exc:
            raise ProtocolError("serial_io", f"USB serial communication failed: {exc}") from exc
