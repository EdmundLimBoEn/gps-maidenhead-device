# Maidenhead Pocket Locator

Open hardware and software for a compact GNSS-powered six-character Maidenhead
locator. The product requirements and validation gates live in [PLAN.md](PLAN.md).

## Current status

Phase 0 is implemented: the deterministic firmware core builds and runs as native
C++ tests, and the Python configurator includes validated profiles, time-zone
transition generation, UF2 inspection, a simulated device transport, and a
Tkinter prototype. Hardware acceptance criteria remain gated on schematic, quote,
prototype, and physical test evidence.

## Development

```sh
cmake -S firmware -B .build/firmware
cmake --build .build/firmware
ctest --test-dir .build/firmware --output-on-failure

python -m venv .venv
. .venv/bin/activate
python -m pip install -e './configurator[dev]'
pytest configurator/tests
python -m maidenhead_configurator
```

The GUI starts against a simulated device by default. Production serial discovery
will use newline-delimited JSON over USB CDC.

## Licensing

Firmware and configurator code are GPL-3.0-or-later. Hardware and mechanical
sources are CERN-OHL-S-2.0. Documentation is CC-BY-SA-4.0. See [LICENSES](LICENSES/README.md).
