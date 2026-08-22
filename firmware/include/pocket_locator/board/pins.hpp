// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>

namespace pocket_locator::board {

// Board revision A pin assignment.  All MCU-facing LCD signals are 3V3 and
// must feed the 3.3 V A-side of the SN74LVC8T245PWR; the LCD module and
// translator B-side are supplied from 5V_LCD.
// Override individual values with POCKET_LOCATOR_PIN_* CMake definitions for
// a bring-up board without changing application code.
struct PinMap {
    std::uint8_t locate_button{2};
    std::uint8_t off_button{3};
    std::uint8_t power_hold{4};
    std::uint8_t lcd_boost_enable{5};
    std::uint8_t lcd_rs{6};
    std::uint8_t lcd_enable{7};
    std::uint8_t lcd_d4{8};
    std::uint8_t lcd_d5{9};
    std::uint8_t lcd_d6{10};
    std::uint8_t lcd_d7{11};
    std::uint8_t lcd_backlight_pwm{12};
    std::uint8_t gnss_uart_tx{16};
    std::uint8_t gnss_uart_rx{17};
    std::uint8_t gnss_enable{18};
    std::uint8_t battery_adc{26};  // ADC0, after a high-value divider.
    std::uint8_t vbus_sense{19};
    std::uint8_t charger_active{20};
    std::uint8_t battery_sense_enable{21};
};

inline constexpr PinMap kDefaultPins{};

}  // namespace pocket_locator::board
