# SPDX-License-Identifier: GPL-3.0-or-later
import os
from types import SimpleNamespace

import pytest

try:
    import tkinter  # noqa: F401
except ModuleNotFoundError:
    HAS_TK = False
else:
    HAS_TK = True


@pytest.mark.skipif(
    not os.environ.get("DISPLAY") or not HAS_TK,
    reason="requires a Tk-enabled Python and an X display; run under xvfb",
)
def test_every_configurator_screen_instantiates_with_simulator() -> None:
    from tkinter import ttk

    from maidenhead_configurator.app import ConfiguratorApp

    app = ConfiguratorApp()
    try:
        app.update_idletasks()
        assert app.blocks.size() == 5
        assert app.status.get() == "Connected to simulated device"
        tabs = next(child for child in app.winfo_children() if isinstance(child, ttk.Notebook))
        tabs.select(1)
        app.update()
        app._begin_block_drag(SimpleNamespace(y=5))
        app._continue_block_drag(SimpleNamespace(y=1000))
        app._end_block_drag(SimpleNamespace(y=1000))
        assert [block.kind for block in app.config_model.bottom_blocks] == [
            "space",
            "time",
            "space",
            "date",
            "battery",
        ]
        assert app._selected_block_index() == 4
    finally:
        app.destroy()
