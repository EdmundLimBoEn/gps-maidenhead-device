// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <array>
#include <cstdint>
#include <string_view>

#include "pocket_locator/board/pins.hpp"

namespace pocket_locator::display {

class Hd44780 {
public:
    explicit Hd44780(board::PinMap pins = board::kDefaultPins) : pins_(pins) {}
    void init();
    void set_enabled(bool enabled);
    void set_backlight_percent(std::uint8_t percent);
    void clear();
    void write_rows(std::string_view first, std::string_view second);
    void show_acquiring();
    void show_no_gps();
    void show_grid(std::string_view grid, std::string_view bottom_row);

private:
    void command(std::uint8_t value);
    void data(std::uint8_t value);
    void write_byte(std::uint8_t value, bool is_data);
    void define_glyph(std::uint8_t slot, const std::array<std::uint8_t, 8>& bitmap);
    void initialize_controller();
    board::PinMap pins_;
    bool enabled_{false};
};

}  // namespace pocket_locator::display
