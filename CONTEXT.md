# Domain Glossary

## Product terms

**Maidenhead Pocket Locator**  
The complete portable device described in `PLAN.md`.

**Locator**  
The six-character Maidenhead representation calculated from the current WGS-84 position, for example `OJ11XH`. Use “six-character,” not “six-digit,” because four positions are letters.

**Current fix**  
A receiver-declared valid GNSS position obtained during the present check session. A previously acquired position is never treated as current.

**Check session**  
The interval beginning at the initial `LOCATE` button-down edge of a subsequently accepted one-second hold, and ending when `OFF`, the shutdown deadline, or a failure releases the hardware power hold.

**Single-fix mode**  
A check session that stops active GNSS tracking after the first valid position is displayed.

**Tracking mode**  
A check session that continues processing GNSS fixes and considers a display update every five seconds.

**Grid stabilization**  
The rule requiring two consecutive valid fixes in the same new locator before the displayed locator changes.

**Acquisition timeout**  
Maximum duration from the initial button-down edge of an accepted `LOCATE` hold to a valid GNSS fix. Factory default: 120 seconds.

**Dim deadline**  
Time from the initial button-down edge of an accepted `LOCATE` hold at which the backlight changes to configured dim brightness. Factory default: 60 seconds.

**Shutdown deadline**  
Time from the initial button-down edge of an accepted `LOCATE` hold at which the hardware power hold is released. Factory default: 120 seconds, except for the three-second terminal `NO GPS` message.

**Factory settings**  
The safe configuration restored by a five-second two-button hold. The factory named time zone is `Asia/Singapore`.

## Hardware terms

**Power hold**  
The MCU signal that keeps the switched system rails enabled after the physical `LOCATE` press starts the device.

**Hard shutdown**  
The state in which switched rails for MCU, GNSS, LCD, and sensing are physically removed rather than relying only on MCU sleep.

**Power path**  
Charger behavior that independently powers the system and charges the cell, allowing normal operation while USB is connected without corrupting charge termination.

**Internal patch**  
The passive ceramic GNSS antenna mounted under the enclosure's top wall and connected to the GP-02 by short coax and u.FL/I-PEX.

**Front profile**  
The enclosure width and height seen from the LCD face, targeted at approximately 85 × 41 mm. Depth may grow to 35 mm.

**Weather goal**  
Survival of drizzle, dust, and incidental sand exposure. It is not an IP rating and does not include immersion.

## Software terms

**Display builder**  
The configurator screen where battery, time, date, separators, and static-text fields are arranged with a live 16-character preview.

**Configuration profile**  
A versioned, human-readable JSON representation of user settings that can be saved and applied to multiple devices. It never contains position history.

**Named zone**  
An IANA time-zone identifier such as `Asia/Singapore` or `America/New_York`. V1 receives its future offset transitions from the host configurator; it does not infer the zone from coordinates.

**Normal update**  
A GUI-driven firmware update that asks running firmware to enter RP2040 ROM BOOTSEL and then installs a selected UF2.

**Recovery update**  
A firmware update entered by opening the rear cover and holding the internal `BOOTSEL` control while connecting USB, independent of application firmware.

**V1**  
The first public hardware, firmware, enclosure, and configurator release that passes the acceptance criteria in `PLAN.md`.
