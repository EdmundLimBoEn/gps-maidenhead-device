// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include <iostream>
#include <limits>
#include <vector>

#include "locator/layout.h"
#include "locator/maidenhead.h"
#include "locator/nmea.h"

namespace {

using locator::LayoutError;
using locator::NmeaError;
using locator::NmeaKind;

TEST(maidenhead_known_vectors_and_closed_boundaries) {
    REQUIRE_EQ(*locator::maidenhead_6(0.0, 0.0), std::string("JJ00AA"));
    REQUIRE_EQ(*locator::maidenhead_6(51.5074, -0.1278), std::string("IO91WM"));
    REQUIRE_EQ(*locator::maidenhead_6(-90.0, -180.0), std::string("AA00AA"));
    REQUIRE_EQ(*locator::maidenhead_6(90.0, 180.0), std::string("AR09AX"));
}

TEST(maidenhead_rejects_non_finite_and_out_of_range_positions) {
    REQUIRE(!locator::maidenhead_6(std::numeric_limits<double>::quiet_NaN(), 0.0).has_value());
    REQUIRE(!locator::maidenhead_6(0.0, std::numeric_limits<double>::infinity()).has_value());
    REQUIRE(!locator::maidenhead_6(-90.00001, 0.0).has_value());
    REQUIRE(!locator::maidenhead_6(0.0, 180.00001).has_value());
}

TEST(nmea_valid_pair_yields_current_fix) {
    const auto rmc = locator::parse_nmea_sentence(
        "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n");
    const auto gga = locator::parse_nmea_sentence(
        "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n");
    REQUIRE(rmc.valid());
    REQUIRE(gga.valid());
    REQUIRE_EQ(rmc.sentence->kind, NmeaKind::rmc);
    REQUIRE_EQ(gga.sentence->kind, NmeaKind::gga);

    locator::FixAccumulator accumulator;
    REQUIRE(!accumulator.ingest(*rmc.sentence).has_value());
    const auto fix = accumulator.ingest(*gga.sentence);
    REQUIRE(fix.has_value());
    REQUIRE_EQ(fix->utc_date.year, 1994);
    REQUIRE_EQ(fix->utc_time.hour, 12);
}

TEST(nmea_rejects_bad_checksum_missing_checksum_and_contradictory_pair) {
    const auto checksum = locator::parse_nmea_sentence(
        "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*00");
    REQUIRE_EQ(checksum.error, NmeaError::checksum_invalid);

    const auto missing = locator::parse_nmea_sentence("$GPRMC,123519,A,4807.038,N,01131.000,E");
    REQUIRE_EQ(missing.error, NmeaError::checksum_missing);

    const auto rmc = locator::parse_nmea_sentence(
        "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A");
    const auto gga_wrong_time = locator::parse_nmea_sentence(
        "$GPGGA,123520,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*4D");
    REQUIRE(rmc.valid());
    REQUIRE(gga_wrong_time.valid());
    locator::FixAccumulator accumulator;
    REQUIRE(!accumulator.ingest(*rmc.sentence).has_value());
    REQUIRE(!accumulator.ingest(*gga_wrong_time.sentence).has_value());
}

TEST(layout_pads_short_rows_and_rejects_overflow_or_unsupported_bytes) {
    const std::vector<std::string_view> fields = {"GRID: ", "OJ11XH"};
    const auto valid = locator::render_lcd_row(fields);
    REQUIRE(valid.valid());
    REQUIRE_EQ(valid.content_width, 12U);
    REQUIRE_EQ(valid.row, std::string("GRID: OJ11XH    "));

    const auto overflow = locator::render_lcd_row({"12345678901234567"});
    REQUIRE_EQ(overflow.error, LayoutError::too_wide);
    const auto unsupported = locator::render_lcd_row({"A\xC3\xA9"});
    REQUIRE_EQ(unsupported.error, LayoutError::unsupported_character);
}

}  // namespace

int main() {
    int failures = 0;
    for (const auto& test : pocket_locator::test::registry()) {
        try {
            test.function();
            std::cout << "PASS " << test.name << '\n';
        } catch (const std::exception& error) {
            ++failures;
            std::cerr << "FAIL " << test.name << ": " << error.what() << '\n';
        }
    }
    std::cout << pocket_locator::test::registry().size() << " tests, " << failures << " failures\n";
    return failures == 0 ? 0 : 1;
}
