# Enclosure engineering source

The parametric OpenSCAD design has an 88 × 44 mm front profile and a calculated
34.5 mm assembled depth. Automated checks confirm those source/export dimensions;
they do not prove component fit, sealing, print tolerance, or RF performance.

The 1.5 mm shell provides 2 mm nominal edge clearance around the current
81 × 37 mm engineering PCB. A 3 mm mating flange provides a real 1 × 0.7 mm
continuous seal groove for nominal 1 mm silicone cord (30% calculated compression)
while retaining 0.5 mm PCB insertion clearance per side.
The lid has a 71 × 25 × 1.1 mm window recess and a
66 × 16 mm through-aperture, leaving a 2.5/4.5 mm continuous seal land. The source also
contains reinforced hard-stop lands, recessed boot apertures, USB plug,
battery rails, antenna frame, and heat-set-insert bosses.

Connector, button, LCD mounting, board retention, antenna orientation, and cable
interfaces remain release-blocking until the exact purchased parts and a shared
datum model pass [the interface contract](INTERFACES.md). The generated shape is
an engineering fit-check, not a production-ready weather-resistant enclosure.

Print structural parts in PETG or ASA, not PLA. Print button boots and the USB
plug in a UV-resistant flexible material. Use a 1 mm clear polycarbonate window
cut to 71 × 25 mm and continuously seal it to the recessed land.

```sh
python3 ../tools/export_enclosure.py
python3 ../tools/validate_enclosure.py --require-openscad
(cd exports && sha256sum -c SHA256SUMS)
```

Before releasing a print, confirm the selected LCD, cell, PCB, coax bend radius,
window, gasket cord, tactile switches, and USB connector against physical samples.
The current battery rails locate a fit dummy but are not a released positive
retainer; that feature remains blocked on the exact cell and Z stack.
After any parameter/source change, regenerate all exports and their checksum file.
