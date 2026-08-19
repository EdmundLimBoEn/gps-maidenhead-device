# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from .models import DeviceConfig, render_bottom
from .protocol import Client, ProtocolError
from .simulator import SimulatedTransport


class ConfiguratorApp(tk.Tk):
    def __init__(self, client: Client | None = None) -> None:
        super().__init__()
        self.title("Maidenhead Pocket Locator")
        self.minsize(720, 460)
        self.client = client or Client(SimulatedTransport())
        self.config_model = DeviceConfig.from_dict(self.client.request("get_config"))
        self.status = tk.StringVar(value="Connected to simulated device")
        self.preview = tk.StringVar()
        self._build()
        self._refresh_preview()

    def _build(self) -> None:
        ttk.Label(self, textvariable=self.status, padding=8).pack(fill="x")
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        for name in ("Device", "Display builder", "Behavior", "Time", "Profiles", "Firmware", "Factory reset"):
            frame = ttk.Frame(tabs, padding=16)
            tabs.add(frame, text=name)
            getattr(self, f"_build_{name.lower().replace(' ', '_')}")(frame)

    def _build_device(self, frame: ttk.Frame) -> None:
        info = self.client.request("get_info")
        diagnostics = self.client.request("get_diagnostics")
        ttk.Label(frame, text=json.dumps({**info, **diagnostics}, indent=2), justify="left").pack(anchor="w")

    def _build_display_builder(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Exact 16-character preview").pack(anchor="w")
        ttk.Label(frame, text="GRID: OJ11XH", font=("TkFixedFont", 18)).pack(anchor="w", pady=(12, 0))
        ttk.Label(frame, textvariable=self.preview, font=("TkFixedFont", 18)).pack(anchor="w")
        ttk.Label(frame, text="Profile JSON supports battery, time, date, text, spaces, and separators.").pack(anchor="w", pady=12)

    def _build_behavior(self, frame: ttk.Frame) -> None:
        mode = tk.StringVar(value=self.config_model.gnss_mode)
        ttk.Label(frame, text="GNSS behavior").pack(anchor="w")
        for value, label in (("single_fix", "Single fix"), ("tracking", "Tracking")):
            ttk.Radiobutton(frame, text=label, variable=mode, value=value, command=lambda: self._set_mode(mode.get())).pack(anchor="w")

    def _set_mode(self, value: str) -> None:
        self.config_model.gnss_mode = value
        self._apply()

    def _build_time(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text=f"Named zone: {self.config_model.timezone}").pack(anchor="w")
        ttk.Label(frame, text="Zones are configured by name; location does not select a zone.").pack(anchor="w", pady=8)

    def _build_profiles(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Profiles are versioned JSON and exclude coordinates and diagnostics.").pack(anchor="w")

    def _build_firmware(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="UF2 files are checked for RP2040 structure before copy.").pack(anchor="w")
        ttk.Label(frame, text="Back up the current profile before installing any custom firmware.").pack(anchor="w", pady=8)

    def _build_factory_reset(self, frame: ttk.Frame) -> None:
        ttk.Button(frame, text="Restore factory settings…", command=self._factory_reset).pack(anchor="w")

    def _refresh_preview(self) -> None:
        self.preview.set(render_bottom(self.config_model).ljust(16))

    def _apply(self) -> None:
        try:
            self.client.request("validate_config", config=self.config_model.to_dict())
            saved = self.client.request("set_config", config=self.config_model.to_dict())
            self.config_model = DeviceConfig.from_dict(saved)
            self.status.set("Settings validated, saved, and read back")
            self._refresh_preview()
        except (ValueError, ProtocolError) as exc:
            messagebox.showerror("Configuration error", str(exc))

    def _factory_reset(self) -> None:
        if not messagebox.askyesno("Factory reset", "Restore factory settings on the device?"):
            return
        self.config_model = DeviceConfig.from_dict(self.client.request("factory_reset"))
        self.status.set("Factory reset verified")
        self._refresh_preview()


def main() -> None:
    ConfiguratorApp().mainloop()


if __name__ == "__main__":
    main()
