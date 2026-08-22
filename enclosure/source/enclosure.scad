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

module rounded_prism_2d(size, height, radius) {
    linear_extrude(height = height)
        offset(r = radius)
            square([size[0] - 2 * radius, size[1] - 2 * radius], center = true);
}

module gasket_groove(z) {
    difference() {
        translate([gasket_inset, gasket_inset, z])
            rounded_box([outer_width - 2 * gasket_inset,
                         outer_height - 2 * gasket_inset,
                         gasket_depth + 0.2], corner_radius - gasket_inset);
        translate([gasket_inset + gasket_width, gasket_inset + gasket_width, z - 0.1])
            rounded_box([outer_width - 2 * (gasket_inset + gasket_width),
                         outer_height - 2 * (gasket_inset + gasket_width),
                         gasket_depth + 0.4],
                        corner_radius - gasket_inset - gasket_width);
    }
}

module mating_flange(z) {
    difference() {
        translate([0, 0, z])
            rounded_box([outer_width, outer_height, mating_flange_thickness], corner_radius);
        translate([mating_flange_inset, mating_flange_inset, z - 0.1])
            rounded_box([outer_width - 2 * mating_flange_inset,
                         outer_height - 2 * mating_flange_inset,
                         mating_flange_thickness + 0.2],
                        corner_radius - mating_flange_inset / 2);
    }
}

module screw_bosses(z, height, bore) {
    for (x = [screw_inset, outer_width - screw_inset])
        for (y = [screw_inset, outer_height - screw_inset])
            translate([x, y, z - 0.2]) difference() {
                cylinder(h = height + 0.2, d = 7.2);
                translate([0, 0, -0.1]) cylinder(h = height + 0.4, d = bore);
            }
}

module base() {
    difference() {
        rounded_box([outer_width, outer_height, base_depth], corner_radius);
        translate([wall, wall, floor_thickness])
            rounded_box([outer_width - 2 * wall, outer_height - 2 * wall,
                         base_depth], corner_radius - wall / 2);
        // Side-button apertures aligned to PCB actuator-tip Y coordinates +3.5 mm.
        for (y = [button_1_center, button_2_center])
            translate([outer_width - wall - 0.2, y, interface_center_z])
                rotate([0, 90, 0]) cylinder(h = wall + 0.5, d = button_diameter);
        // Outside counterbores protect and locate the bonded boot flanges.
        for (y = [button_1_center, button_2_center])
            translate([outer_width - button_recess, y, interface_center_z])
                rotate([0, 90, 0])
                    cylinder(h = button_recess + 0.2, d = button_diameter + 4.4);
        // USB-C opening aligned to the PCB connector mating face at x=0, y=14.
        translate([-0.2, usb_center - usb_width / 2 - usb_clearance,
                   interface_center_z - usb_height / 2 - usb_clearance])
            cube([wall + 0.5, usb_width + 2 * usb_clearance,
                  usb_height + 2 * usb_clearance]);
    }
    mating_flange(base_depth - mating_flange_thickness);
    screw_bosses(floor_thickness, base_depth - floor_thickness - 1.5, insert_diameter);
    // Battery rails; no compression against the pouch.
    battery_x = (outer_width - battery_width) / 2;
    battery_y = (outer_height - battery_height) / 2;
    for (x = [battery_x - battery_clearance - 1.5,
              battery_x + battery_width + battery_clearance])
        translate([x, battery_y, floor_thickness]) cube([1.5, battery_height, 2.5]);
    // Antenna shelf beneath the top wall, clear of battery and PCB copper.
    // Overlap the frame into the right wall so it is printable, not a floating body.
    antenna_x = outer_width - antenna_width - wall - 1.5;
    antenna_y = wall + 3;
    antenna_z = base_depth - antenna_depth - 2;
    translate([antenna_x, antenna_y,
               base_depth - antenna_depth - 2])
        difference() {
            cube([antenna_width + 2, antenna_height + 2, 1.2]);
            translate([1, 1, -0.1]) cube([antenna_width, antenna_height, 1.4]);
        }
    // Four integrated posts make the antenna frame a printable, retained body.
    for (x = [antenna_x, antenna_x + antenna_width])
        for (y = [antenna_y, antenna_y + antenna_height])
            translate([x, y, floor_thickness - 0.2])
                cube([2, 2, antenna_z - floor_thickness + 0.4]);
}

module lid() {
    difference() {
        union() {
            difference() {
                rounded_box([outer_width, outer_height, lid_depth], corner_radius);
                translate([wall, wall, lid_thickness])
                    rounded_box([outer_width - 2 * wall, outer_height - 2 * wall,
                                 lid_depth], corner_radius - wall / 2);
                // Flush exterior pocket for the 1 mm polycarbonate window.
                translate([outer_width / 2, outer_height / 2, -0.1])
                    rounded_prism_2d([lcd_window_width, lcd_window_height],
                                     lcd_window_recess_depth + 0.1,
                                     lcd_window_corner_radius);
                // Smaller through-aperture leaves the continuous window seal land.
                translate([(outer_width - lcd_visible_width) / 2,
                           (outer_height - lcd_visible_height) / 2,
                           lcd_window_recess_depth - 0.05])
                    cube([lcd_visible_width, lcd_visible_height,
                          lid_thickness - lcd_window_recess_depth + 0.3]);
            }
            mating_flange(lid_depth - mating_flange_thickness);
            // Reinforced hard-stop lands around the four through screws.
            for (x = [screw_inset, outer_width - screw_inset])
                for (y = [screw_inset, outer_height - screw_inset])
                    translate([x, y, lid_depth - 1.4])
                        cylinder(h = 1.4, d = 7.2);
        }
        gasket_groove(lid_depth - gasket_depth);
        for (x = [screw_inset, outer_width - screw_inset])
            for (y = [screw_inset, outer_height - screw_inset])
                translate([x, y, -0.1]) cylinder(h = lid_depth + 0.2, d = screw_clearance);
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
        translate([0, 0, 1.4])
            cube([usb_width - 2 * usb_clearance,
                  usb_height - 2 * usb_clearance, 4.0]);
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
    // Exploded view: flip the lid so its open mating face points toward the base.
    translate([0, outer_height, base_depth + lid_depth + 2])
        rotate([180, 0, 0]) color("SteelBlue", 0.7) lid();
}
