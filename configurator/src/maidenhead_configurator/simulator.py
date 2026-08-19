# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import ConfigError, DeviceConfig, factory_config
from .protocol import COMMANDS, PROTOCOL_VERSION


class SimulatedTransport:
    """In-memory implementation of the device protocol for GUI development."""

    def __init__(self) -> None:
        self.config = factory_config()
        self.bootloader_requested = False

    def transact(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("request_id")
        if request.get("protocol_version") != PROTOCOL_VERSION:
            return self._error(request_id, "unsupported_protocol", "protocol version is unsupported")
        command = request.get("command")
        if command not in COMMANDS:
            return self._error(request_id, "unknown_command", "command is not supported")
        try:
            data = self._execute(command, request)
        except (ConfigError, TypeError, KeyError) as exc:
            return self._error(request_id, "invalid_config", str(exc))
        return {"request_id": request_id, "ok": True, "data": data}

    @staticmethod
    def _error(request_id: Any, code: str, message: str) -> dict[str, Any]:
        return {"request_id": request_id, "ok": False, "error": {"code": code, "message": message}}

    def _execute(self, command: str, request: dict[str, Any]) -> Any:
        if command == "hello":
            return {"protocol_version": PROTOCOL_VERSION, "device": "simulator"}
        if command == "get_info":
            return {"firmware_version": "0.1.0-sim", "hardware_revision": "sim"}
        if command == "get_config":
            return deepcopy(self.config.to_dict(include_timezone_table=True))
        if command == "validate_config":
            DeviceConfig.from_dict(request["config"]).validate_device_payload()
            return {"valid": True}
        if command == "set_config":
            candidate = DeviceConfig.from_dict(request["config"])
            candidate.validate_device_payload()
            self.config = candidate
            return deepcopy(self.config.to_dict(include_timezone_table=True))
        if command == "get_diagnostics":
            return {
                "config_crc_healthy": True,
                "battery_adc": 3072,
                "battery_level": 3,
                "usb_present": True,
                "gnss_state": "off",
                "timezone_refresh_required": False,
            }
        if command == "factory_reset":
            self.config = factory_config()
            return deepcopy(self.config.to_dict())
        if command == "reboot_to_bootloader":
            self.bootloader_requested = True
            return {"rebooting": True}
        raise AssertionError(command)
