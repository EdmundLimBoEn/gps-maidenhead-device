// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/display/format.hpp"

#include <algorithm>
#include <array>
#include <climits>
#include <cstdio>

namespace pocket_locator::display {
namespace {

[[nodiscard]] std::int64_t days_from_civil(int year, unsigned month, unsigned day) {
    year -= month <= 2U ? 1 : 0;
    const int era = (year >= 0 ? year : year - 399) / 400;
    const unsigned year_of_era = static_cast<unsigned>(year - era * 400);
    const unsigned month_prime = month > 2U ? month - 3U : month + 9U;
    const unsigned day_of_year = (153U * month_prime + 2U) / 5U + day - 1U;
    const unsigned day_of_era = year_of_era * 365U + year_of_era / 4U - year_of_era / 100U + day_of_year;
    return static_cast<std::int64_t>(era) * 146097 + static_cast<int>(day_of_era) - 719468;
}

struct Civil { int year; unsigned month; unsigned day; unsigned hour; unsigned minute; unsigned second; };

[[nodiscard]] Civil civil_from_epoch(std::int64_t epoch) {
    std::int64_t days = epoch / 86400;
    std::int64_t seconds = epoch % 86400;
    if (seconds < 0) { seconds += 86400; --days; }
    const std::int64_t z = days + 719468;
    const std::int64_t era = (z >= 0 ? z : z - 146096) / 146097;
    const unsigned day_of_era = static_cast<unsigned>(z - era * 146097);
    const unsigned year_of_era = (day_of_era - day_of_era / 1460U + day_of_era / 36524U - day_of_era / 146096U) / 365U;
    int year = static_cast<int>(year_of_era) + static_cast<int>(era) * 400;
    const unsigned day_of_year = day_of_era - (365U * year_of_era + year_of_era / 4U - year_of_era / 100U);
    const unsigned month_prime = (5U * day_of_year + 2U) / 153U;
    const unsigned day = day_of_year - (153U * month_prime + 2U) / 5U + 1U;
    const unsigned month = month_prime < 10U ? month_prime + 3U : month_prime - 9U;
    year += month <= 2U ? 1 : 0;
    return {year, month, day, static_cast<unsigned>(seconds / 3600), static_cast<unsigned>((seconds / 60) % 60), static_cast<unsigned>(seconds % 60)};
}

[[nodiscard]] std::int64_t epoch(const locator::CurrentFix& fix) {
    return days_from_civil(fix.utc_date.year, static_cast<unsigned>(fix.utc_date.month), static_cast<unsigned>(fix.utc_date.day)) * 86400 +
           static_cast<std::int64_t>(fix.utc_time.hour) * 3600 + static_cast<std::int64_t>(fix.utc_time.minute) * 60 + fix.utc_time.second;
}

[[nodiscard]] char battery_glyph(std::uint8_t percent, bool charging) {
    if (charging) return 4;
    return percent < 25U ? 0 : percent < 50U ? 1 : percent < 75U ? 2 : 3;
}

[[nodiscard]] std::string time_text(const config::Settings& settings, const Civil& civil) {
    char buffer[16]{};
    if (settings.clock_24h) {
        std::snprintf(buffer, sizeof(buffer), settings.show_seconds ? "%02u:%02u:%02u" : "%02u:%02u", civil.hour, civil.minute, civil.second);
    } else {
        const unsigned hour = civil.hour % 12U == 0U ? 12U : civil.hour % 12U;
        if (settings.show_seconds) {
            std::snprintf(buffer, sizeof(buffer), "%02u:%02u:%02u %s", hour, civil.minute, civil.second, civil.hour < 12U ? "AM" : "PM");
        } else {
            std::snprintf(buffer, sizeof(buffer), "%02u:%02u %s", hour, civil.minute, civil.hour < 12U ? "AM" : "PM");
        }
    }
    return buffer;
}

[[nodiscard]] std::string date_text(config::DateFormat format, const Civil& civil) {
    static constexpr std::array<const char*, 12> months{"JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"};
    char buffer[12]{};
    switch (format) {
        case config::DateFormat::DdMm: std::snprintf(buffer, sizeof(buffer), "%02u/%02u", civil.day, civil.month); break;
        case config::DateFormat::MmDd: std::snprintf(buffer, sizeof(buffer), "%02u/%02u", civil.month, civil.day); break;
        case config::DateFormat::DdMmm: std::snprintf(buffer, sizeof(buffer), "%02u%s", civil.day, months[civil.month - 1U]); break;
        case config::DateFormat::YyyyMmDd:
            buffer[0] = static_cast<char>('0' + ((civil.year / 1000) % 10));
            buffer[1] = static_cast<char>('0' + ((civil.year / 100) % 10));
            buffer[2] = static_cast<char>('0' + ((civil.year / 10) % 10));
            buffer[3] = static_cast<char>('0' + (civil.year % 10));
            buffer[4] = '-'; buffer[5] = static_cast<char>('0' + civil.month / 10U); buffer[6] = static_cast<char>('0' + civil.month % 10U);
            buffer[7] = '-'; buffer[8] = static_cast<char>('0' + civil.day / 10U); buffer[9] = static_cast<char>('0' + civil.day % 10U);
            break;
    }
    return buffer;
}
}  // namespace

FormattedFixScreen format_fix_screen(const config::Settings& settings, std::string_view grid, const locator::CurrentFix& fix,
                                     std::uint8_t battery_percent, bool charging, std::uint64_t elapsed_seconds) {
    const auto base_utc = epoch(fix);
    const auto maximum_elapsed = static_cast<std::uint64_t>(INT64_MAX - base_utc);
    const auto utc = base_utc + static_cast<std::int64_t>(std::min(elapsed_seconds, maximum_elapsed));
    const auto offset = time::offset_at(settings.zone_table, utc);
    const Civil local = civil_from_epoch(utc + offset.offset_seconds);
    std::string bottom;
    bottom.reserve(16);
    for (const auto& block : settings.bottom_blocks) {
        switch (block.kind) {
            case config::DisplayBlockKind::Battery: bottom.push_back(battery_glyph(battery_percent, charging)); break;
            case config::DisplayBlockKind::Time: bottom += time_text(settings, local); break;
            case config::DisplayBlockKind::Date: bottom += date_text(settings.date_format, local); break;
            case config::DisplayBlockKind::Text:
            case config::DisplayBlockKind::Space:
            case config::DisplayBlockKind::Separator: bottom += block.value; break;
        }
    }
    return {"GRID: " + std::string(grid), bottom, offset.refresh_required};
}

}  // namespace pocket_locator::display
