# User guide

**Draft for the future validated V1 hardware.** Timing, charging, sealing, thermal
cutoff, and recovery statements below are required behavior, not measured claims
about the current engineering sources.

Hold **LOCATE** for one second. The screen shows `ACQUIRING GPS` until it receives
a current valid GNSS fix; it never substitutes a cached position. For best results,
hold the unit face-up outdoors with a clear view of the sky. The factory session
dims after 60 seconds and ends after 120 seconds from the first button-down edge.

Hold **OFF** for one second to end early. While USB is connected, OFF returns the
device to a dark configuration-ready state. Hold both buttons for five seconds and
follow the countdown to restore factory settings.

The locator is intended for desks, portable amateur-radio outings, and occupied
vehicles. It is not a navigation device, emergency beacon, tracking device, or
substitute for checking conditions around a vehicle. Do not leave or charge it in
a hot parked vehicle.

## Charging and USB

Use a standards-compliant 5 V USB source and a data-capable USB-C cable. The red
indicator is lit while charging. Charging is inhibited when the cell sensor is
outside its permitted temperature range. Unplug and inspect the device if it
becomes unusually hot, smells unusual, or the enclosure/cell changes shape.

The enclosure target is resistance to drizzle, dust, and incidental sand with its USB cap
installed. It has no certified IP rating. Do not immerse it or charge it while wet.

## Configuration and recovery

Install Python 3.11+, Tkinter, and the configurator as described in the
[configurator guide](../../configurator/README.md). Profiles contain display and behavior settings but never
location history. Custom RP2040 UF2 firmware is allowed; back up the current profile
before every update.

If application firmware will not start, remove the rear cover, hold the labelled
internal **BOOTSEL** switch, attach USB, and release the switch when `RPI-RP2`
appears. Keep the cell and metal tools away from exposed electronics.
