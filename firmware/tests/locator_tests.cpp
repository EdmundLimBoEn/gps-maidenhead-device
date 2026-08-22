// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include "locator/layout.h"
#include "locator/maidenhead.h"
#include "locator/nmea.h"

#include <algorithm>
#include <cmath>
#include <optional>
#include <limits>
#include <random>
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

std::string reference_maidenhead(double latitude, double longitude) {
    if (longitude == 180.0) longitude = -180.0;
    if (latitude == 90.0) {
        latitude = std::nextafter(90.0, -std::numeric_limits<double>::infinity());
    }
    const int longitude_units = std::clamp(
        static_cast<int>(std::floor((longitude + 180.0) * 12.0)), 0, 4'319);
    const int latitude_units = std::clamp(
        static_cast<int>(std::floor((latitude + 90.0) * 24.0)), 0, 4'319);
    std::string result(6, 'A');
    result[0] = static_cast<char>('A' + longitude_units / 240);
    result[1] = static_cast<char>('A' + latitude_units / 240);
    result[2] = static_cast<char>('0' + (longitude_units / 24) % 10);
    result[3] = static_cast<char>('0' + (latitude_units / 24) % 10);
    result[4] = static_cast<char>('A' + longitude_units % 24);
    result[5] = static_cast<char>('A' + latitude_units % 24);
    return result;
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

TEST(maidenhead_matches_seeded_independent_fractional_oracle) {
    std::mt19937_64 random(0x4d414944454e4845ULL);
    std::uniform_real_distribution<double> latitudes(-90.0, 90.0);
    std::uniform_real_distribution<double> longitudes(-180.0, 180.0);
    for (int sample = 0; sample < 20'000; ++sample) {
        const double latitude = latitudes(random);
        const double longitude = longitudes(random);
        REQUIRE_EQ(locator::maidenhead_6(latitude, longitude),
                   std::optional<std::string>{reference_maidenhead(latitude, longitude)});
    }
}

TEST(maidenhead_matches_oracle_around_every_subsquare_boundary) {
    constexpr double epsilon = 1e-10;
    for (int boundary = 0; boundary <= 4'320; ++boundary) {
        const double longitude = -180.0 + static_cast<double>(boundary) / 12.0;
        const double latitude = -90.0 + static_cast<double>(boundary) / 24.0;
        for (const double offset : {-epsilon, 0.0, epsilon}) {
            if (longitude + offset >= -180.0 && longitude + offset <= 180.0) {
                REQUIRE_EQ(locator::maidenhead_6(1.3521, longitude + offset),
                           std::optional<std::string>{
                               reference_maidenhead(1.3521, longitude + offset)});
            }
            if (latitude + offset >= -90.0 && latitude + offset <= 90.0) {
                REQUIRE_EQ(locator::maidenhead_6(latitude + offset, 103.8198),
                           std::optional<std::string>{
                               reference_maidenhead(latitude + offset, 103.8198)});
            }
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

    const auto estimated = locator::parse_nmea_sentence(
        nmea("GPRMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,E"));
    REQUIRE(estimated.valid());
    REQUIRE(!estimated.sentence->receiver_fix_valid);
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
    REQUIRE(!accumulator.ingest(*rmc.sentence).fix);
    REQUIRE(!accumulator.ingest(*stale.sentence).fix);
    const auto result = accumulator.ingest(*gga.sentence);
    REQUIRE(result.fix.has_value());
    REQUIRE_EQ(result.fix->utc_date, locator::UtcDate({2026, 8, 19}));
}

TEST(nmea_accumulator_accepts_gga_before_rmc_and_flags_invalid_epochs) {
    const auto rmc = locator::parse_nmea_sentence(
        nmea("GPRMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"));
    const auto gga = locator::parse_nmea_sentence(
        nmea("GPGGA,143500.00,0121.1260,N,10349.1880,E,1,08,1.0,10.0,M,0.0,M,,"));
    const auto invalid = locator::parse_nmea_sentence(
        nmea("GPGGA,143501.00,,,,,0,00,99.9,,,,,,"));
    REQUIRE(rmc.valid() && gga.valid() && invalid.valid());

    locator::FixAccumulator accumulator;
    REQUIRE(!accumulator.ingest(*gga.sentence).fix);
    REQUIRE(accumulator.ingest(*rmc.sentence).fix.has_value());
    REQUIRE(accumulator.ingest(*invalid.sentence).invalid_fix);
}

TEST(nmea_accumulator_rejects_same_epoch_contradictory_positions) {
    const auto rmc = locator::parse_nmea_sentence(
        nmea("GPRMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"));
    const auto gga = locator::parse_nmea_sentence(
        nmea("GPGGA,143500.00,0221.1260,N,10349.1880,E,1,08,1.0,10.0,M,0.0,M,,"));
    locator::FixAccumulator accumulator;
    REQUIRE(!accumulator.ingest(*rmc.sentence).fix);
    REQUIRE(accumulator.ingest(*gga.sentence).invalid_fix);
}

TEST(nmea_accumulator_rejects_duplicate_and_replayed_epochs) {
    const auto rmc = locator::parse_nmea_sentence(
        nmea("GPRMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"));
    const auto gga = locator::parse_nmea_sentence(
        nmea("GPGGA,143500.00,0121.1260,N,10349.1880,E,1,08,1.0,10.0,M,0.0,M,,"));
    const auto older_rmc = locator::parse_nmea_sentence(
        nmea("GPRMC,143459.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"));
    const auto older_gga = locator::parse_nmea_sentence(
        nmea("GPGGA,143459.00,0121.1260,N,10349.1880,E,1,08,1.0,10.0,M,0.0,M,,"));
    REQUIRE(rmc.valid() && gga.valid() && older_rmc.valid() && older_gga.valid());

    locator::FixAccumulator accumulator;
    REQUIRE(!accumulator.ingest(*rmc.sentence).fix);
    REQUIRE(accumulator.ingest(*gga.sentence).fix.has_value());
    REQUIRE(!accumulator.ingest(*rmc.sentence).fix);
    REQUIRE(accumulator.ingest(*gga.sentence).invalid_fix);
    REQUIRE(!accumulator.ingest(*older_rmc.sentence).fix);
    REQUIRE(accumulator.ingest(*older_gga.sentence).invalid_fix);

    accumulator.clear();
    REQUIRE(!accumulator.ingest(*older_rmc.sentence).fix);
    REQUIRE(accumulator.ingest(*older_gga.sentence).fix.has_value());
}

TEST(nmea_uart_framer_discards_every_byte_after_overflow_until_newline) {
    locator::NmeaLineFramer framer(4);
    REQUIRE(!framer.push('$'));
    REQUIRE(!framer.push('A'));
    REQUIRE(!framer.push('B'));
    REQUIRE(!framer.push('C'));
    const auto overflow = framer.push('D');
    REQUIRE(overflow.has_value());
    REQUIRE_EQ(overflow->kind, locator::NmeaFrameKind::Overlong);
    for (const char tail : std::string("$OK")) REQUIRE(!framer.push(tail));
    REQUIRE(!framer.push('\n'));
    REQUIRE(!framer.push('$'));
    REQUIRE(!framer.push('X'));
    const auto recovered = framer.push('\n');
    REQUIRE(recovered.has_value());
    REQUIRE_EQ(recovered->payload, std::string("$X"));
}

TEST(nmea_rejects_noncanonical_numeric_and_coordinate_shapes) {
    REQUIRE(!locator::parse_nmea_sentence(
                 nmea("GPRMC,143500.00,A,+121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"))
                 .valid());
    REQUIRE(!locator::parse_nmea_sentence(
                 nmea("GPRMC,143500.00,A,0121.1260,N,103.1880,E,0.0,0.0,190826,,,A"))
                 .valid());
    REQUIRE(!locator::parse_nmea_sentence(
                 nmea("GPRMC,143500e0,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"))
                 .valid());
    REQUIRE(!locator::parse_nmea_sentence(
                 nmea("GPGGA,143500.00,0121.1260,N,10349.1880,E,+1,08,1.0,10.0,M,0.0,M,,"))
                 .valid());
    REQUIRE(!locator::parse_nmea_sentence(
                 nmea("GPRMC,143500.00,A,0121,N,10349.1880,E,0.0,0.0,190826,,,A"))
                 .valid());
    REQUIRE(!locator::parse_nmea_sentence(
                 nmea("12RMC,143500.00,A,0121.1260,N,10349.1880,E,0.0,0.0,190826,,,A"))
                 .valid());
}
