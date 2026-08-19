# Enclosure source

The parametric OpenSCAD design preserves the 85 × 41 mm LCD-like front profile
and a 34.5 mm assembled depth. It includes a gasket groove with compression
stops, separate LCD-window seal land, recessed side-button apertures, USB-C plug,
battery rails, antenna shelf, and four heat-set-insert bosses.

Print structural parts in PETG or ASA, not PLA. Print button boots and the USB
plug in a UV-resistant flexible material. Use a 1 mm clear polycarbonate window
cut to 71 × 25 mm and continuously seal it to the recessed land.

```sh
openscad -D 'part="base"' -o exports/base.stl source/enclosure.scad
openscad -D 'part="lid"' -o exports/lid.stl source/enclosure.scad
openscad -D 'part="button"' -o exports/button-boot.stl source/enclosure.scad
openscad -D 'part="usb_plug"' -o exports/usb-plug.stl source/enclosure.scad
```

Before releasing a print, confirm the selected LCD, cell, PCB, coax bend radius,
window, gasket cord, tactile switches, and USB connector against physical samples.

