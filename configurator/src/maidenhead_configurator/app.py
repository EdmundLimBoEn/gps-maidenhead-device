# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json
import tkinter as tk
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from zoneinfo import ZoneInfo, available_timezones

from .firmware import FirmwareUpdater
from .models import (
    DATE_FORMATS,
    GNSS_MODES,
    ConfigError,
    DeviceConfig,
    DisplayBlock,
    render_bottom,
    reorder_blocks,
)
from .profiles import Profile, load_profile, profile_diff, save_profile
from .protocol import Client, ProtocolError
from .serial_transport import NdjsonSerialTransport, discover_devices
from .simulator import SimulatedTransport
from .timezone_table import generate_timezone_table
from .uf2 import inspect_uf2


class ConfiguratorApp(tk.Tk):
    """Desktop editor. Changes are never written until the user presses Apply."""

    def __init__(self, client: Client | None = None) -> None:
        super().__init__()
        self.title("Maidenhead Pocket Locator")
        self.minsize(760, 560)
        self.client = client or Client(SimulatedTransport())
        self._serial_transport: NdjsonSerialTransport | None = None
        self.config_model = DeviceConfig.from_dict(self.client.request("get_config"))
        self.status = tk.StringVar(value="Connected to simulated device")
        self.preview = tk.StringVar()
        self.connection_choice = tk.StringVar(value="Simulator")
        self._drag_block_index: int | None = None
        self._build()
        self._load_model_into_widgets()
        self._refresh_preview()

    def destroy(self) -> None:
        if self._serial_transport:
            self._serial_transport.close()
        super().destroy()

    def _build(self) -> None:
        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill="x")
        ttk.Label(header, text="Device:").pack(side="left")
        self.device_combo = ttk.Combobox(header, textvariable=self.connection_choice, state="readonly", width=44)
        self.device_combo.pack(side="left", padx=6)
        ttk.Button(header, text="Refresh USB", command=self._refresh_usb).pack(side="left")
        ttk.Button(header, text="Connect", command=self._connect).pack(side="left", padx=6)
        ttk.Label(self, textvariable=self.status, padding=(8, 4)).pack(fill="x")
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        for name in ("Device", "Display builder", "Behavior", "Time", "Profiles", "Firmware", "Factory reset"):
            frame = ttk.Frame(tabs, padding=16)
            tabs.add(frame, text=name)
            getattr(self, f"_build_{name.lower().replace(' ', '_')}")(frame)
        footer = ttk.Frame(self, padding=(8, 0, 8, 8))
        footer.pack(fill="x")
        ttk.Button(footer, text="Discard changes", command=self._reload).pack(side="left")
        ttk.Button(footer, text="Validate and apply", command=self._apply).pack(side="right")

    def _refresh_usb(self) -> None:
        try:
            devices = discover_devices()
            values = ["Simulator", *(device.label for device in devices)]
            self.device_combo["values"] = values
            if self.connection_choice.get() not in values:
                self.connection_choice.set(values[0])
            self.status.set(f"Found {len(devices)} compatible USB device(s)")
        except ProtocolError as exc:
            self._show_error("USB discovery", exc)

    def _connect(self) -> None:
        choice = self.connection_choice.get()
        try:
            if choice == "Simulator":
                transport = None
                client = Client(SimulatedTransport())
            else:
                port = choice.split(" — ", 1)[0]
                transport = NdjsonSerialTransport(port)
                client = Client(transport)
                hello = client.request("hello")
                if hello.get("protocol_version") != 1:
                    transport.close()
                    raise ProtocolError("unsupported_protocol", "device protocol is not compatible")
            model = DeviceConfig.from_dict(client.request("get_config"))
        except (ProtocolError, ConfigError) as exc:
            self._show_error("Connection failed", exc)
            return
        if self._serial_transport:
            self._serial_transport.close()
        self._serial_transport, self.client, self.config_model = transport, client, model
        self._load_model_into_widgets()
        self._refresh_preview()
        self.status.set(f"Connected to {choice}")

    def _build_device(self, frame: ttk.Frame) -> None:
        self.device_info = tk.StringVar(value="Select Refresh USB then Connect to use a physical device.")
        ttk.Label(frame, textvariable=self.device_info, justify="left", font=("TkFixedFont", 10)).pack(anchor="w")
        ttk.Button(frame, text="Refresh device information", command=self._refresh_device_info).pack(anchor="w", pady=12)

    def _refresh_device_info(self) -> None:
        try:
            info = self.client.request("get_info")
            diagnostics = self.client.request("get_diagnostics")
            self.device_info.set(json.dumps({"info": info, "diagnostics": diagnostics}, indent=2, sort_keys=True))
        except ProtocolError as exc:
            self._show_error("Device information", exc)

    def _build_display_builder(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Bottom row blocks (maximum 16 characters at their widest format)").grid(row=0, column=0, columnspan=4, sticky="w")
        self.blocks = tk.Listbox(frame, height=9, exportselection=False, width=44)
        self.blocks.grid(row=1, column=0, rowspan=6, sticky="nsew", pady=8)
        self.blocks.bind("<<ListboxSelect>>", lambda _event: self._select_block())
        # This is deliberately a Tk-only gesture; it never relies on the host
        # desktop's file drag-and-drop APIs.
        self.blocks.bind("<ButtonPress-1>", self._begin_block_drag)
        self.blocks.bind("<B1-Motion>", self._continue_block_drag)
        self.blocks.bind("<ButtonRelease-1>", self._end_block_drag)
        controls = ttk.Frame(frame)
        controls.grid(row=1, column=1, sticky="n", padx=8)
        for text, command in (("Add", self._add_block), ("Remove", self._remove_block), ("Move up", lambda: self._move_block(-1)), ("Move down", lambda: self._move_block(1))):
            ttk.Button(controls, text=text, command=command).pack(fill="x", pady=2)
        editor = ttk.LabelFrame(frame, text="Selected block", padding=8)
        editor.grid(row=1, column=2, rowspan=5, sticky="new", padx=8)
        self.block_kind = tk.StringVar(value="text")
        self.block_value = tk.StringVar()
        ttk.Label(editor, text="Kind").grid(row=0, column=0, sticky="w")
        ttk.Combobox(editor, textvariable=self.block_kind, state="readonly", values=("battery", "time", "date", "text", "space", "separator"), width=14).grid(row=1, column=0, sticky="ew")
        ttk.Label(editor, text="Text / separator value").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(editor, textvariable=self.block_value, width=18).grid(row=3, column=0, sticky="ew")
        ttk.Button(editor, text="Update block", command=self._update_block).grid(row=4, column=0, sticky="ew", pady=(8, 0))
        preview = ttk.LabelFrame(frame, text="Exact LCD preview", padding=8)
        preview.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Label(preview, text="GRID: OJ11XH", font=("TkFixedFont", 18)).pack(anchor="w")
        ttk.Label(preview, textvariable=self.preview, font=("TkFixedFont", 18)).pack(anchor="w")
        frame.columnconfigure(0, weight=1)

    def _block_label(self, block: DisplayBlock) -> str:
        value = repr(block.value) if block.value else ""
        return f"{block.kind}{': ' + value if value else ''}"

    def _render_blocks(self, selected: int | None = None) -> None:
        self.blocks.delete(0, "end")
        for block in self.config_model.bottom_blocks:
            self.blocks.insert("end", self._block_label(block))
        if selected is not None and 0 <= selected < len(self.config_model.bottom_blocks):
            self.blocks.selection_set(selected)
            self.blocks.activate(selected)
        self._refresh_preview()

    def _selected_block_index(self) -> int | None:
        selection = self.blocks.curselection()
        return int(selection[0]) if selection else None

    def _select_block(self) -> None:
        index = self._selected_block_index()
        if index is None:
            return
        block = self.config_model.bottom_blocks[index]
        self.block_kind.set(block.kind)
        self.block_value.set(block.value)

    def _add_block(self) -> None:
        self.config_model.bottom_blocks.append(DisplayBlock("text", ""))
        self._render_blocks(len(self.config_model.bottom_blocks) - 1)

    def _remove_block(self) -> None:
        index = self._selected_block_index()
        if index is not None:
            del self.config_model.bottom_blocks[index]
            self._render_blocks(max(0, index - 1))

    def _move_block(self, direction: int) -> None:
        index = self._selected_block_index()
        if index is None or not 0 <= index + direction < len(self.config_model.bottom_blocks):
            return
        self._render_blocks(reorder_blocks(self.config_model.bottom_blocks, index, index + direction))

    def _begin_block_drag(self, event: tk.Event[tk.Misc]) -> str | None:
        if self.blocks.size() == 0:
            self._drag_block_index = None
            return None
        index = self.blocks.nearest(event.y)
        self.blocks.selection_clear(0, "end")
        self.blocks.selection_set(index)
        self.blocks.activate(index)
        self._drag_block_index = index
        self._select_block()
        return "break"

    def _continue_block_drag(self, event: tk.Event[tk.Misc]) -> str | None:
        source = self._drag_block_index
        if source is None or self.blocks.size() == 0:
            return None
        target = self.blocks.nearest(event.y)
        if target != source:
            self._drag_block_index = reorder_blocks(self.config_model.bottom_blocks, source, target)
            self._render_blocks(self._drag_block_index)
            self._select_block()
        return "break"

    def _end_block_drag(self, _event: tk.Event[tk.Misc]) -> str | None:
        if self._drag_block_index is not None:
            self._render_blocks(self._drag_block_index)
            self._select_block()
        self._drag_block_index = None
        return "break"

    def _update_block(self) -> None:
        index = self._selected_block_index()
        if index is None:
            return
        self.config_model.bottom_blocks[index] = DisplayBlock(self.block_kind.get(), self.block_value.get())
        self._render_blocks(index)

    def _build_behavior(self, frame: ttk.Frame) -> None:
        self.behavior_vars = {
            "gnss_mode": tk.StringVar(), "tracking_interval_seconds": tk.StringVar(), "acquisition_timeout_seconds": tk.StringVar(),
            "dim_deadline_seconds": tk.StringVar(), "shutdown_deadline_seconds": tk.StringVar(), "normal_brightness_percent": tk.StringVar(), "dim_brightness_percent": tk.StringVar(),
        }
        ttk.Label(frame, text="GNSS behavior").grid(row=0, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=self.behavior_vars["gnss_mode"], state="readonly", values=sorted(GNSS_MODES)).grid(row=0, column=1, sticky="ew")
        rows = (("tracking_interval_seconds", "Tracking redraw interval (seconds)"), ("acquisition_timeout_seconds", "GPS acquisition timeout (seconds)"), ("dim_deadline_seconds", "Dim after LOCATE edge (seconds)"), ("shutdown_deadline_seconds", "Shutdown after LOCATE edge (seconds)"), ("normal_brightness_percent", "Normal brightness (%)"), ("dim_brightness_percent", "Dim brightness (%)"))
        for row, (field, label) in enumerate(rows, 1):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Spinbox(frame, from_=0, to=3600, textvariable=self.behavior_vars[field], width=12).grid(row=row, column=1, sticky="w", padx=10)
        ttk.Label(frame, text="All timers are measured from the initial LOCATE button-down edge.", wraplength=560).grid(row=8, column=0, columnspan=2, sticky="w", pady=12)

    def _build_time(self, frame: ttk.Frame) -> None:
        self.timezone_var = tk.StringVar()
        self.clock_24h_var = tk.BooleanVar()
        self.seconds_var = tk.BooleanVar()
        self.date_format_var = tk.StringVar()
        ttk.Label(frame, text="IANA time zone").grid(row=0, column=0, sticky="w")
        self.timezone_combo = ttk.Combobox(frame, textvariable=self.timezone_var, values=sorted(available_timezones()), width=38)
        self.timezone_combo.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Checkbutton(frame, text="24-hour clock", variable=self.clock_24h_var, command=self._refresh_preview).grid(row=1, column=0, columnspan=2, sticky="w", pady=8)
        ttk.Checkbutton(frame, text="Show seconds", variable=self.seconds_var, command=self._refresh_preview).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text="Date format").grid(row=3, column=0, sticky="w", pady=8)
        ttk.Combobox(frame, textvariable=self.date_format_var, state="readonly", values=sorted(DATE_FORMATS)).grid(row=3, column=1, sticky="w", padx=8)
        ttk.Label(frame, text="The device receives generated offset transitions; time zone is never inferred from coordinates.", wraplength=580).grid(row=4, column=0, columnspan=2, sticky="w", pady=12)
        frame.columnconfigure(1, weight=1)

    def _build_profiles(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Profiles contain settings only—never coordinates or live diagnostics.").pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="w", pady=12)
        ttk.Button(buttons, text="Save current settings…", command=self._save_profile).pack(side="left")
        ttk.Button(buttons, text="Open and compare…", command=self._open_profile).pack(side="left", padx=8)
        self.profile_diff_text = tk.Text(frame, width=76, height=16, state="disabled", wrap="word")
        self.profile_diff_text.pack(fill="both", expand=True)

    def _set_profile_diff(self, content: str) -> None:
        self.profile_diff_text.configure(state="normal")
        self.profile_diff_text.delete("1.0", "end")
        self.profile_diff_text.insert("1.0", content)
        self.profile_diff_text.configure(state="disabled")

    def _save_profile(self) -> None:
        try:
            candidate = self._candidate_from_widgets()
        except (ValueError, ConfigError) as exc:
            self._show_error("Cannot save profile", exc)
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Profile JSON", "*.json")])
        if path:
            notes = simpledialog.askstring("Profile notes", "Optional notes for this profile:", parent=self) or ""
            save_profile(Profile(candidate, notes), path)
            self.status.set(f"Profile saved to {Path(path).name}")

    def _open_profile(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Profile JSON", "*.json")])
        if not path:
            return
        try:
            profile = load_profile(path)
            diff = profile_diff(self.config_model, profile.config)
        except (OSError, ValueError, KeyError, ConfigError) as exc:
            self._show_error("Profile", exc)
            return
        lines = [f"Profile: {Path(path).name}", f"Notes: {profile.notes or '(none)'}", "", "Changed fields:"]
        lines.extend(f"• {field}: {old!r} → {new!r}" for field, (old, new) in diff.items())
        if not diff:
            lines.append("No settings differ.")
        self._set_profile_diff("\n".join(lines))
        if messagebox.askyesno("Apply profile", "Apply this profile to the editor? It will not be written until Validate and apply."):
            self.config_model = deepcopy(profile.config)
            self._load_model_into_widgets()
            self.status.set(f"Profile loaded: {Path(path).name}; pending apply")

    def _build_firmware(self, frame: ttk.Frame) -> None:
        self.uf2_path_var = tk.StringVar()
        ttk.Label(frame, text="UF2 firmware file").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.uf2_path_var, width=56).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(frame, text="Browse…", command=self._browse_uf2).grid(row=1, column=1, padx=8)
        ttk.Button(frame, text="Validate UF2", command=self._validate_uf2).grid(row=2, column=0, sticky="w", pady=8)
        ttk.Button(frame, text="Back up profile and install…", command=self._install_firmware).grid(row=3, column=0, sticky="w")
        ttk.Label(frame, text="Recovery: unplug the device, hold its BOOTSEL control, plug USB back in, then select the RPI-RP2 drive if automatic detection cannot find it.", wraplength=610).grid(row=4, column=0, columnspan=2, sticky="w", pady=16)
        frame.columnconfigure(0, weight=1)

    def _browse_uf2(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("RP2040 UF2", "*.uf2")])
        if path:
            self.uf2_path_var.set(path)

    def _validate_uf2(self) -> None:
        try:
            info = inspect_uf2(self.uf2_path_var.get())
            self.status.set(f"Valid RP2040 UF2: {info.block_count} blocks, {info.payload_bytes} payload bytes")
        except (OSError, ValueError) as exc:
            self._show_error("UF2 validation", exc)

    def _install_firmware(self) -> None:
        source = self.uf2_path_var.get()
        try:
            info = inspect_uf2(source)
        except (OSError, ValueError) as exc:
            self._show_error("UF2 validation", exc)
            return
        backup = filedialog.asksaveasfilename(
            title="Save automatic profile backup",
            defaultextension=".json",
            filetypes=[("Profile JSON", "*.json")],
        )
        if not backup:
            return
        if not messagebox.askyesno(
            "Install firmware",
            f"Install {Path(source).name} ({info.block_count} blocks)? "
            "The current settings will be backed up first.",
        ):
            return
        try:
            updater = FirmwareUpdater(self.client)
            backup_path = updater.backup_profile(backup)
            updater.enter_bootloader()
            try:
                volume = updater.wait_for_boot_volume()
            except ProtocolError as error:
                if error.code != "boot_volume_not_found":
                    raise
                selected = filedialog.askdirectory(title="Select the mounted RPI-RP2 bootloader drive")
                if not selected:
                    self.status.set("Firmware update paused; profile backup was saved")
                    return
                volume = Path(selected)
            destination = updater.copy_uf2(source, volume)
            self.status.set(f"Copied firmware to {destination.parent}. Waiting for USB reconnect…")
            device = updater.wait_for_reconnect()
            self.connection_choice.set(device.label)
            self._connect()
            self.status.set(f"Firmware installed; profile backup saved as {backup_path.name}")
        except ProtocolError as exc:
            self._show_error("Firmware update", exc)

    def _build_factory_reset(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="This restores defaults on the device. It does not erase firmware and does not retain coordinates.", wraplength=580).pack(anchor="w")
        ttk.Button(frame, text="Restore factory settings…", command=self._factory_reset).pack(anchor="w", pady=16)

    def _load_model_into_widgets(self) -> None:
        self._render_blocks()
        if hasattr(self, "behavior_vars"):
            for field, variable in self.behavior_vars.items():
                variable.set(str(getattr(self.config_model, field)))
            self.timezone_var.set(self.config_model.timezone)
            self.clock_24h_var.set(self.config_model.clock_24h)
            self.seconds_var.set(self.config_model.show_seconds)
            self.date_format_var.set(self.config_model.date_format)

    def _candidate_from_widgets(self) -> DeviceConfig:
        data = self.config_model.to_dict()
        if hasattr(self, "behavior_vars"):
            for field, variable in self.behavior_vars.items():
                value = variable.get().strip()
                data[field] = value if field == "gnss_mode" else int(value)
            data.update(timezone=self.timezone_var.get().strip(), clock_24h=self.clock_24h_var.get(), show_seconds=self.seconds_var.get(), date_format=self.date_format_var.get())
        candidate = DeviceConfig.from_dict(data)
        # Verify that a host zone can make a table now, before asking the device to store it.
        generate_timezone_table(candidate.timezone, generated_at=datetime.now(ZoneInfo("UTC")))
        return candidate

    def _refresh_preview(self) -> None:
        try:
            data = self.config_model.to_dict()
            if hasattr(self, "clock_24h_var"):
                data.update(clock_24h=self.clock_24h_var.get(), show_seconds=self.seconds_var.get(), date_format=self.date_format_var.get())
            self.preview.set(render_bottom(DeviceConfig.from_dict(data)).ljust(16))
        except (ConfigError, ValueError):
            self.preview.set("[layout invalid]")

    def _reload(self) -> None:
        try:
            self.config_model = DeviceConfig.from_dict(self.client.request("get_config"))
            self._load_model_into_widgets()
            self.status.set("Unsaved changes discarded")
        except (ProtocolError, ConfigError) as exc:
            self._show_error("Reload", exc)

    def _apply(self) -> None:
        try:
            candidate = self._candidate_from_widgets()
            payload = candidate.to_device_dict()
            self.client.request("validate_config", config=payload)
            saved = self.client.request("set_config", config=payload)
            self.config_model = DeviceConfig.from_dict(saved)
            self._load_model_into_widgets()
            self.status.set("Settings validated, saved, and read back")
        except (ValueError, ConfigError, ProtocolError) as exc:
            self._show_error("Configuration error", exc)

    def _factory_reset(self) -> None:
        if not messagebox.askyesno("Factory reset", "Restore factory settings on the connected device?"):
            return
        try:
            self.config_model = DeviceConfig.from_dict(self.client.request("factory_reset"))
            self._load_model_into_widgets()
            self.status.set("Factory reset verified")
        except (ProtocolError, ConfigError) as exc:
            self._show_error("Factory reset", exc)

    def _show_error(self, title: str, error: Exception) -> None:
        code = getattr(error, "code", None)
        messagebox.showerror(title, f"{code + ': ' if code else ''}{error}")
        self.status.set(f"{title}: {error}")


def main() -> None:
    ConfiguratorApp().mainloop()


if __name__ == "__main__":
    main()
