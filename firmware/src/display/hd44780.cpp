// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/display/hd44780.hpp"

#include <algorithm>
#include <array>
#include <string>

#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "pico/stdlib.h"

namespace pocket_locator::display {
namespace {
constexpr std::array<std::uint8_t, 8> kBatteryEmpty{0x0e, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f, 0x00};
constexpr std::array<std::uint8_t, 8> kBatteryLow{0x0e, 0x11, 0x11, 0x11, 0x11, 0x1f, 0x1f, 0x00};
constexpr std::array<std::uint8_t, 8> kBatteryMedium{0x0e, 0x11, 0x11, 0x11, 0x1f, 0x1f, 0x1f, 0x00};
constexpr std::array<std::uint8_t, 8> kBatteryFull{0x0e, 0x11, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x00};
constexpr std::array<std::uint8_t, 8> kBatteryCharging{0x0e, 0x15, 0x0a, 0x04, 0x0a, 0x15, 0x1f, 0x00};
}

void Hd44780::init() {
    for (const std::uint8_t pin : {pins_.lcd_rs, pins_.lcd_enable, pins_.lcd_d4, pins_.lcd_d5, pins_.lcd_d6, pins_.lcd_d7}) {
        gpio_init(pin);
        gpio_set_dir(pin, GPIO_OUT);
        gpio_put(pin, false);
    }
    gpio_set_function(pins_.lcd_backlight_pwm, GPIO_FUNC_PWM);
    // RP2040 has eight PWM slices. Masking also prevents GCC from retaining
    // the RP2350-only branch in the SDK helper's range analysis.
    const auto slice = pwm_gpio_to_slice_num(pins_.lcd_backlight_pwm) & 7U;
    pwm_config config = pwm_get_default_config();
    pwm_config_set_clkdiv(&config, 8.0F);
    pwm_config_set_wrap(&config, 255);
    pwm_init(slice, &config, true);
    set_backlight_percent(0);
    gpio_init(pins_.lcd_boost_enable);
    gpio_set_dir(pins_.lcd_boost_enable, GPIO_OUT);
    gpio_put(pins_.lcd_boost_enable, false);
}

void Hd44780::set_enabled(bool enabled) {
    if (enabled == enabled_) return;
    enabled_ = enabled;
    if (!enabled_) {
        set_backlight_percent(0);
        gpio_put(pins_.lcd_boost_enable, false);
        return;
    }
    gpio_put(pins_.lcd_boost_enable, true);
    sleep_ms(10);
    initialize_controller();
}

void Hd44780::initialize_controller() {
    sleep_ms(50);
    // 4-bit initialization sequence required before normal commands work.
    for (int i = 0; i < 3; ++i) {
        gpio_put(pins_.lcd_rs, false);
        gpio_put(pins_.lcd_d4, true);
        gpio_put(pins_.lcd_d5, true);
        gpio_put(pins_.lcd_d6, false);
        gpio_put(pins_.lcd_d7, false);
        gpio_put(pins_.lcd_enable, true);
        sleep_us(1);
        gpio_put(pins_.lcd_enable, false);
        sleep_ms(5);
    }
    gpio_put(pins_.lcd_d4, false);
    gpio_put(pins_.lcd_d5, true);
    gpio_put(pins_.lcd_d6, false);
    gpio_put(pins_.lcd_d7, false);
    gpio_put(pins_.lcd_enable, true);
    sleep_us(1);
    gpio_put(pins_.lcd_enable, false);
    sleep_us(150);
    command(0x28);  // 4-bit, two line.
    command(0x08);  // Display off while CGRAM is initialized.
    command(0x01);
    sleep_ms(2);
    command(0x06);
    define_glyph(0, kBatteryEmpty);
    define_glyph(1, kBatteryLow);
    define_glyph(2, kBatteryMedium);
    define_glyph(3, kBatteryFull);
    define_glyph(4, kBatteryCharging);
    command(0x0c);
}

void Hd44780::set_backlight_percent(std::uint8_t percent) {
    const auto level = static_cast<std::uint16_t>((static_cast<std::uint32_t>(std::min<std::uint8_t>(percent, 100U)) * 255U) / 100U);
    pwm_set_gpio_level(pins_.lcd_backlight_pwm, level);
}

void Hd44780::command(std::uint8_t value) { write_byte(value, false); }
void Hd44780::data(std::uint8_t value) { write_byte(value, true); }

void Hd44780::write_byte(std::uint8_t value, bool is_data) {
    gpio_put(pins_.lcd_rs, is_data);
    const std::array<std::uint8_t, 4> data_pins{pins_.lcd_d4, pins_.lcd_d5, pins_.lcd_d6, pins_.lcd_d7};
    for (const bool high : {true, false}) {
        const std::uint8_t nibble = high ? static_cast<std::uint8_t>(value >> 4U) : static_cast<std::uint8_t>(value & 0x0fU);
        for (unsigned bit = 0; bit < data_pins.size(); ++bit) {
            gpio_put(data_pins[bit], (nibble & (1U << bit)) != 0U);
        }
        gpio_put(pins_.lcd_enable, true);
        sleep_us(1);
        gpio_put(pins_.lcd_enable, false);
        sleep_us(50);  // R/W is grounded: fixed safe delays, no 5V reads.
    }
}

void Hd44780::define_glyph(std::uint8_t slot, const std::array<std::uint8_t, 8>& bitmap) {
    command(static_cast<std::uint8_t>(0x40U | ((slot & 0x7U) << 3U)));
    for (const auto row : bitmap) {
        data(row);
    }
}

void Hd44780::clear() {
    command(0x01);
    sleep_ms(2);
}

void Hd44780::write_rows(std::string_view first, std::string_view second) {
    command(0x80);
    for (std::size_t i = 0; i < 16; ++i) data(i < first.size() ? static_cast<std::uint8_t>(first[i]) : ' ');
    command(0xc0);
    for (std::size_t i = 0; i < 16; ++i) data(i < second.size() ? static_cast<std::uint8_t>(second[i]) : ' ');
}

void Hd44780::show_acquiring() { write_rows("ACQUIRING GPS", "PLEASE WAIT"); }
void Hd44780::show_no_gps() { write_rows("NO GPS", "TRY OPEN SKY"); }

void Hd44780::show_grid(std::string_view grid, std::string_view bottom_row) {
    write_rows(std::string("GRID: ").append(grid), bottom_row);
}

}  // namespace pocket_locator::display
