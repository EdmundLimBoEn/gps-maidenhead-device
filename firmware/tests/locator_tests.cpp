// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include "locator/layout.h"
#include "locator/maidenhead.h"
#include "locator/nmea.h"

#include <cmath>
#include <optional>
#include <string>
#include <string_view>

namespace {

std::string nmea(std::string_view payload) {
    unsigned char checksum = 0;
    for (const char character : payload) {
        checksum ^= static_cast<unsigned char>(character);
    }
    constexpr char hexadecimal[] = "0123456789ABCDEF";
    std::string line{"$"};
    line.append(payload);
    line.push_back('*');
    line.push_back(hexadecimal[checksum >> 4U]);
    line.push_back(hexadecimal[checksum & 0x0fU]);
    return line;
}

}  // namespace

TEST(maidenhead_converts_known_points_and_boundaries) {
    REQUIRE_EQ(locator::maidenhead_6(1.3521, 103.8198), std::optional<std::string>{"OJ11VI"});
    REQUIRE_EQ(locator::maidenhead_6(-90.0, -180.0), std::optional<std::string>{"AA00AA"});
    REQUIRE_EQ(locator::maidenhead_6(90.0, 180.0), std::optional<std::string>{"AR09AX"});
    REQUIRE_EQ(locator::maidenhead_6(0.0, 180.0), locator::maidenhead_6(0.0, -180.0));
    REQUIRE(!locator::maidenhead_6(90.00001, 0.0));
    REQUIRE(!locator::maidenhead_6(0.0, std::nan("")));
}

TEST(maidenhead_output_alphabet_is_always_valid) {
    for (int latitude = -90; latitude <= 90; latitude += 3) {
        for (int longitude = -180; longitude <= 180; longitude += 3) {
            const auto grid = locator::maidenhead_6(latitude, longitude);
            REQUIRE(grid.has_value());
            REQUIRE((*grid)[0] >= 'A' && (*grid)[0] <= 'R');
            REQUIRE((*grid)[1] >= 'A' && (*grid)[1] <= 'R');
            REQUIRE((*grid)[2] >= '0' && (*grid)[2] <= '9');
            REQUIRE((*grid)[3] >= '0' && (*grid)[3] <= '9');
            REQUIRE((*grid)[4] >= 'A' && (*grid)[4] <= 'X');
            REQUIRE((*grid)[5] >= 'A' && (*grid)[5] <= 'X');
        }
    }
}

TEST(layout_pads_to_sixteen_and_rejects_overflow_or_unicode) {
    const auto normal = locator::render_lcd_row({"GRID: OJ11XH"});
    REQUIRE(normal.valid());
    REQUIRE_EQ(normal.row, std::string("GRID: OJ11XH    "));
    REQUIRE_EQ(normal.row.size(), 16U);

    REQUIRE(locator::render_lcd_row({"1234567890123456"}).valid());
    REQUIRE(!locator::render_lcd_row({"12345678901234567"}).valid());
    REQUIRE(!locator::render_lcd_row({"CQ \xE2\x98\x83"}).valid());
}

TEST(nmea_requires_checksum_and_receiver_validity) {
    const auto valid_rmc = locator::parse_nmea_sentence(
        nmea("GPRMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"));
    REQUIRE(valid_rmc.valid());
    REQUIRE(valid_rmc.sentence->receiver_fix_valid);
    REQUIRE(valid_rmc.sentence->utc_date.has_value());

    const auto void_rmc = locator::parse_nmea_sentence(
        nmea("GPRMC,143500.00,V,,,,,,,190826,,,N"));
    REQUIRE(void_rmc.valid());
    REQUIRE(!void_rmc.sentence->receiver_fix_valid);

    REQUIRE(!locator::parse_nmea_sentence(
                 "$GPRMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A")
                 .valid());
    REQUIRE(!locator::parse_nmea_sentence("$GPRMC,143500.00,A*00").valid());
}

TEST(nmea_accumulator_requires_matching_valid_rmc_and_gga) {
    const auto rmc = locator::parse_nmea_sentence(
        nmea("GPRMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"));
    const auto gga = locator::parse_nmea_sentence(
        nmea("GPGGA,143500.00,0121.1260,N,10349.1880,E,1,08,1.0,10.0,M,0.0,M,,"));
    const auto stale = locator::parse_nmea_sentence(
        nmea("GPGGA,143501.00,0121.1260,N,10349.1880,E,1,08,1.0,10.0,M,0.0,M,,"));
    REQUIRE(rmc.valid() && gga.valid() && stale.valid());

    locator::FixAccumulator accumulator;
    REQUIRE(!accumulator.ingest(*rmc.sentence));
    REQUIRE(!accumulator.ingest(*stale.sentence));
    const auto fix = accumulator.ingest(*gga.sentence);
    REQUIRE(fix.has_value());
    REQUIRE_EQ(fix->utc_date, locator::UtcDate({2026, 8, 19}));
}
