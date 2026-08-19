# Firmware release artifacts

`pocket_locator_rp2040.uf2` is built from the repository firmware source with
the Raspberry Pi Pico SDK. Rebuild it with the commands in `firmware/README.md`
and verify its RP2040 family identifier before distribution.

Verify the tracked artifact with `sha256sum -c firmware/releases/SHA256SUMS`
from the repository root.
