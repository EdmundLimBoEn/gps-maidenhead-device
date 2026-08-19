// SPDX-License-Identifier: CERN-OHL-S-2.0
// Render `part` as "base", "lid", "button", "usb_plug", or "assembly".

include <parameters.scad>

part = "assembly";
$fn = 48;

module rounded_box(size, radius) {
    hull() {
        for (x = [radius, size[0] - radius])
            for (y = [radius, size[1] - radius])
                translate([x, y, 0]) cylinder(h = size[2], r = radius);
    }
}

module gasket_groove(z) {
    difference() {
        translate([gasket_inset, gasket_inset, z])
            rounded_box([outer_width - 2 * gasket_inset,
                         outer_height - 2 * gasket_inset,
                         gasket_depth + 0.2], corner_radius - 1);
        translate([gasket_inset + gasket_width, gasket_inset + gasket_width, z - 0.1])
            rounded_box([outer_width - 2 * (gasket_inset + gasket_width),
                         outer_height - 2 * (gasket_inset + gasket_width),
                         gasket_depth + 0.4], corner_radius - 1.5);
    }
}

module screw_bosses(z, height, bore) {
    for (x = [screw_inset, outer_width - screw_inset])
        for (y = [screw_inset, outer_height - screw_inset])
            translate([x, y, z]) difference() {
                cylinder(h = height, d = 7.0);
                translate([0, 0, -0.1]) cylinder(h = height + 0.2, d = bore);
            }
}

module base() {
    difference() {
        rounded_box([outer_width, outer_height, base_depth], corner_radius);
        translate([wall, wall, floor_thickness])
            rounded_box([outer_width - 2 * wall, outer_height - 2 * wall,
                         base_depth], corner_radius - wall / 2);
        // Two protected side-button apertures.
        for (x = [outer_width / 2 - button_spacing / 2,
                  outer_width / 2 + button_spacing / 2])
            translate([x, outer_height - wall - 0.2, base_depth / 2])
                rotate([-90, 0, 0]) cylinder(h = wall + 0.5, d = button_diameter);
        // Recessed USB-C opening on the opposite long wall.
        translate([outer_width / 2 - usb_width / 2, -0.2,
                   base_depth / 2 - usb_height / 2])
            cube([usb_width, wall + 0.5, usb_height]);
    }
    screw_bosses(floor_thickness, base_depth - floor_thickness - 1.5, insert_diameter);
    // Battery rails; no compression against the pouch.
    for (x = [wall + 2, wall + battery_width + 3])
        translate([x, wall + 3, floor_thickness]) cube([1.5, battery_height, 2.5]);
    // Antenna shelf beneath the top wall, clear of battery and PCB copper.
    translate([outer_width - antenna_width - wall - 3, wall + 3,
               base_depth - antenna_depth - 2])
        difference() {
            cube([antenna_width + 2, antenna_height + 2, 1.2]);
            translate([1, 1, -0.1]) cube([antenna_width, antenna_height, 1.4]);
        }
}

module lid() {
    difference() {
        rounded_box([outer_width, outer_height, lid_depth], corner_radius);
        translate([wall, wall, lid_thickness])
            rounded_box([outer_width - 2 * wall, outer_height - 2 * wall,
                         lid_depth], corner_radius - wall / 2);
        translate([(outer_width - lcd_window_width) / 2,
                   (outer_height - lcd_window_height) / 2, -0.1])
            cube([lcd_window_width, lcd_window_height, lid_thickness + 0.3]);
        gasket_groove(lid_depth - gasket_depth);
        for (x = [screw_inset, outer_width - screw_inset])
            for (y = [screw_inset, outer_height - screw_inset])
                translate([x, y, -0.1]) cylinder(h = lid_depth + 0.2, d = screw_clearance);
    }
    // Hard compression stops protect the perimeter gasket.
    for (x = [screw_inset, outer_width - screw_inset])
        for (y = [screw_inset, outer_height - screw_inset])
            translate([x, y, lid_depth - 1.4]) difference() {
                cylinder(h = 1.4, d = 6.0);
                translate([0, 0, -0.1]) cylinder(h = 1.6, d = screw_clearance);
            }
}

module button_boot() {
    difference() {
        union() {
            cylinder(h = 2.2, d = button_diameter + 4);
            translate([0, 0, 2.0]) cylinder(h = 3.0, d1 = button_diameter + 1, d2 = button_diameter - 1);
        }
        translate([0, 0, -0.1]) cylinder(h = 1.4, d = button_diameter - 2);
    }
}

module usb_plug() {
    union() {
        translate([-1.5, -1.5, 0]) cube([usb_width + 3, usb_height + 3, 1.5]);
        translate([0, 0, 1.4]) cube([usb_width, usb_height, 4.0]);
        translate([usb_width + 1.5, usb_height / 2 + 1.5, 0])
            rotate([90, 0, 0]) cylinder(h = 2.0, d = 2.0);
    }
}

if (part == "base") base();
else if (part == "lid") lid();
else if (part == "button") button_boot();
else if (part == "usb_plug") usb_plug();
else {
    color("DarkSlateGray") base();
    translate([0, 0, base_depth + 2]) color("SteelBlue", 0.7) lid();
}
