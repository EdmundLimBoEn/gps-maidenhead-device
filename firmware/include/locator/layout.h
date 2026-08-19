// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace locator {

enum class LayoutError {
    none,
    too_wide,
    unsupported_character,
};

struct LayoutResult {
    LayoutError error{LayoutError::none};
    std::string row{};
    std::size_t content_width{0};

    [[nodiscard]] bool valid() const { return error == LayoutError::none; }
};

// Produces an exact 16-cell HD44780 row. Printable ASCII and LCD custom
// character slots 0..7 are supported; all other bytes are rejected. The
// caller supplies fields after expanding time/date/static-text configuration.
[[nodiscard]] LayoutResult render_lcd_row(const std::vector<std::string_view>& fields);

}  // namespace locator
