# Configurator

Requires Python 3.11 or newer, Tkinter, and a data-capable USB cable. Install the
project and start the simulated-device prototype with:

```sh
python -m pip install -e .
python -m maidenhead_configurator
```

Some Linux distributions package Tkinter separately (commonly `python3-tk`). If
`zoneinfo` reports that time-zone data is unavailable—most often on Windows—run
`python -m pip install tzdata`. The configurator never derives a time zone from
device coordinates; it sends transitions for the IANA zone selected by the user.

Profiles are versioned JSON. They intentionally omit coordinates and transient
GNSS diagnostics. Applying a profile regenerates its time-zone transition table
from the host database.
