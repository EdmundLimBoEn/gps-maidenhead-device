// SPDX-License-Identifier: GPL-3.0-or-later

#include "locator/layout.h"

namespace locator {
namespace {

bool supported_lcd_byte(unsigned char value) {
    return value <= 7U || (value >= 0x20U && value <= 0x7eU);
}

}  // namespace

LayoutResult render_lcd_row(const std::vector<std::string_view>& fields) {
    LayoutResult result{};
    for (const std::string_view field : fields) {
        for (const unsigned char character : field) {
            if (!supported_lcd_byte(character)) {
                result.error = LayoutError::unsupported_character;
                return result;
            }
        }
        result.content_width += field.size();
        if (result.content_width > 16U) {
            result.error = LayoutError::too_wide;
            return result;
        }
        result.row.append(field);
    }
    result.row.append(16U - result.content_width, ' ');
    return result;
}

}  // namespace locator
