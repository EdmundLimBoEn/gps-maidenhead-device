# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096
COMMANDS = {
    "hello",
    "get_info",
    "get_config",
    "validate_config",
    "set_config",
    "get_diagnostics",
    "factory_reset",
    "reboot_to_bootloader",
}


class ProtocolError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class Transport(Protocol):
    def transact(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(slots=True)
class Client:
    transport: Transport
    next_request_id: int = 1

    def request(self, command: str, **payload: Any) -> Any:
        if command not in COMMANDS:
            raise ProtocolError("unknown_command", command)
        request_id = str(self.next_request_id)
        self.next_request_id += 1
        request = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
            "command": command,
            **payload,
        }
        encoded = json.dumps(request, separators=(",", ":")).encode()
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise ProtocolError("message_too_large", "request exceeds protocol limit")
        response = self.transport.transact(request)
        if response.get("request_id") != request_id:
            raise ProtocolError("request_id_mismatch", "response does not match request")
        if response.get("ok") is not True:
            error = response.get("error", {})
            raise ProtocolError(error.get("code", "device_error"), error.get("message", "error"))
        return response.get("data")
