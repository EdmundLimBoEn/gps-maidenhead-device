# Configurator

Requires Python 3.11 or newer, Tkinter, and a data-capable USB cable. Install the
project and start the simulated-device prototype with:

```sh
python -m pip install -e .
python -m maidenhead_configurator
```

Some Linux distributions package Tkinter separately (commonly `python3-tk`). The
Windows install automatically includes the `tzdata` package used by `zoneinfo`.
The configurator never derives a time zone from device coordinates; it sends
transitions for the IANA zone selected by the user.

Profiles are versioned JSON. They intentionally omit coordinates, transient GNSS
diagnostics, and the generated time-zone table. Applying a profile or pressing
**Validate and apply** regenerates and sends a compact 15-year transition table
from the host's current IANA database. The supplied
`profiles/factory-default.json` is a portable starting profile.

For a physical device, click **Refresh USB**, select the RP2040 CDC port, and
click **Connect**. The Device screen reports firmware, hardware, configuration
health, and non-persistent diagnostics. If discovery finds nothing, verify that
the cable carries data and that local serial-port permissions allow access.

Normal firmware installation validates the RP2040 UF2, requires a profile
backup, enters ROM BOOTSEL, copies without unsupported filesystem metadata, and
waits for the boot volume to disappear before reconnecting. If application
firmware cannot start, use **Install using BOOTSEL recovery…** after attaching
the device with its internal BOOTSEL control held. ROM volumes are recognized
by their `RPI-RP2` name or `INFO_UF2.TXT`, including Windows drive roots.
