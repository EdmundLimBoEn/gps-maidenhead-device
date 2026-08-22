# Maidenhead Pocket Locator

Open hardware and software for a compact GNSS-powered six-character Maidenhead
locator. The product requirements and validation gates live in [PLAN.md](PLAN.md).

## Current status

The development source tree covers RP2040 firmware and host tests, a
Tk/serial configurator with profiles and UF2 recovery, KiCad engineering sources
and manufacturing workflow, a parametric enclosure with printable exports, and
assembly/validation documentation.

This is **not yet a physically validated product release**. Ordering and public
distribution remain gated on the frozen BOM/quote, reviewed manufacturing exports,
prototype bring-up, and measured acceptance evidence listed in
[the release checklist](docs/manufacturing/RELEASE_CHECKLIST.md) and
[evidence index](docs/testing/TEST_EVIDENCE.md). No claim is made here that the
weather, battery, GNSS, off-current, thermal, or cost gates have passed.

## Development

```sh
cmake -S firmware -B .build/firmware
cmake --build .build/firmware
ctest --test-dir .build/firmware --output-on-failure

python -m venv .venv
. .venv/bin/activate
python -m pip install -e './configurator[dev]'
pytest configurator/tests
python -m ruff check configurator tools
python -m ruff format --check configurator tools
python -m maidenhead_configurator

bash firmware/tests/pico_stub_compile.sh
python3 hardware/manufacturing/preflight.py
python3 tools/export_enclosure.py
python3 tools/validate_enclosure.py --require-openscad
python3 tools/check_docs.py
python3 tools/release_preflight.py
```

To build an RP2040 UF2, install the Pico SDK and set its location:

```sh
PICO_SDK_PATH=/path/to/pico-sdk \
  cmake -S firmware -B .build/firmware-pico -DPOCKET_LOCATOR_BUILD_RP2040=ON
cmake --build .build/firmware-pico
```

The GUI starts against a simulator by default. A physical device uses
newline-delimited JSON over USB CDC; each configuration write includes a fresh
15-year named-zone transition table. Profiles remain location-free and portable.

## Manufacturing and safety

Do not order or distribute from an arbitrary working tree. Generate artifacts from
a tagged revision, complete [the five-unit order package](docs/manufacturing/ORDER_PACKAGE.md),
and follow the [assembly](docs/assembly/ASSEMBLY.md) and
[test procedures](docs/testing/TEST_PROCEDURES.md).

The [mechanical interface contract](enclosure/INTERFACES.md) and
[cost research snapshot](docs/manufacturing/COST_RESEARCH.md) make the remaining
fit and landed-cost unknowns explicit. Neither is a manufacturing sign-off.

Use only the released protected LiPo and charger configuration. The device is not
an emergency locator, navigation instrument, tracker, or immersion-rated product.
Do not charge it while wet or leave it charging in a hot vehicle.

## Licensing

Firmware and configurator code are GPL-3.0-or-later. Hardware and mechanical
sources are CERN-OHL-S-2.0. Documentation is CC-BY-SA-4.0. See [LICENSES](LICENSES/README.md).
