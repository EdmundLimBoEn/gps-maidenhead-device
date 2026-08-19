// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstdio>
#include <optional>
#include <string>
#include <string_view>

#include "hardware/watchdog.h"
#include "pico/stdlib.h"

#include "locator/maidenhead.h"
#include "pocket_locator/app/check_session.hpp"
#include "pocket_locator/board/battery.hpp"
#include "pocket_locator/board/bootloader.hpp"
#include "pocket_locator/board/buttons.hpp"
#include "pocket_locator/board/power.hpp"
#include "pocket_locator/config/config.hpp"
#include "pocket_locator/display/hd44780.hpp"
#include "pocket_locator/display/format.hpp"
#include "pocket_locator/gnss/uart_gnss.hpp"
#include "pocket_locator/storage/flash_config_store.hpp"
#include "pocket_locator/usb/protocol.hpp"

namespace {

[[nodiscard]] std::uint64_t now_ms() { return to_ms_since_boot(get_absolute_time()); }

[[nodiscard]] pocket_locator::app::SessionSettings session_settings(const pocket_locator::config::Settings& config) {
    return {
        .gnss_mode = config.gnss_mode,
        .hold_ms = 1'000,
        .factory_reset_hold_ms = 5'000,
        .acquisition_timeout_ms = config.acquisition_timeout_ms,
        .dim_deadline_ms = config.dim_deadline_ms,
        .shutdown_deadline_ms = config.shutdown_deadline_ms,
        .no_gps_message_ms = 3'000,
        .tracking_render_interval_ms = config.tracking_render_interval_ms,
    };
}

[[nodiscard]] const char* gnss_mode_name(pocket_locator::app::GnssMode mode) {
    return mode == pocket_locator::app::GnssMode::Tracking ? "tracking" : "single_fix";
}

[[nodiscard]] const char* date_format_name(pocket_locator::config::DateFormat format) {
    using pocket_locator::config::DateFormat;
    switch (format) {
        case DateFormat::DdMm: return "DD/MM";
        case DateFormat::MmDd: return "MM/DD";
        case DateFormat::DdMmm: return "DDMMM";
        case DateFormat::YyyyMmDd: return "YYYY-MM-DD";
    }
    return "DD/MM";
}

[[nodiscard]] std::string blocks_json(const std::vector<pocket_locator::config::DisplayBlock>& blocks) {
    using pocket_locator::config::DisplayBlockKind;
    std::string result{"["};
    for (std::size_t i = 0; i < blocks.size(); ++i) {
        if (i != 0U) result += ',';
        const auto& block = blocks[i];
        const char* kind = block.kind == DisplayBlockKind::Battery ? "battery" : block.kind == DisplayBlockKind::Time ? "time" :
                           block.kind == DisplayBlockKind::Date ? "date" : block.kind == DisplayBlockKind::Text ? "text" :
                           block.kind == DisplayBlockKind::Space ? "space" : "separator";
        result += "{\"kind\":\"";
        result += kind;
        result += "\"";
        if (!block.value.empty()) {
            std::string escaped;
            escaped.reserve(block.value.size());
            for (const char c : block.value) { if (c == '"' || c == '\\') escaped.push_back('\\'); escaped.push_back(c); }
            result += ",\"value\":\"" + escaped + "\"";
        }
        result += '}';
    }
    return result + ']';
}

[[nodiscard]] std::string config_json(const pocket_locator::config::Settings& config) {
    return "{\"schema_version\":" + std::to_string(config.schema_version) +
           ",\"top_template\":\"GRID: {grid6}\",\"bottom_blocks\":" + blocks_json(config.bottom_blocks) + ",\"timezone\":\"" +
           config.named_time_zone + "\",\"clock_24h\":" + (config.clock_24h ? "true" : "false") +
           ",\"show_seconds\":" + (config.show_seconds ? "true" : "false") + ",\"date_format\":\"" + date_format_name(config.date_format) + "\",\"gnss_mode\":\"" +
           gnss_mode_name(config.gnss_mode) + "\",\"tracking_interval_seconds\":" +
           std::to_string(config.tracking_render_interval_ms / 1000U) +
           ",\"acquisition_timeout_seconds\":" + std::to_string(config.acquisition_timeout_ms / 1000U) +
           ",\"dim_deadline_seconds\":" + std::to_string(config.dim_deadline_ms / 1000U) +
           ",\"shutdown_deadline_seconds\":" + std::to_string(config.shutdown_deadline_ms / 1000U) +
           ",\"normal_brightness_percent\":" + std::to_string(config.normal_brightness) +
           ",\"dim_brightness_percent\":" + std::to_string(config.dim_brightness) + "}";
}

void response(std::string_view request_id, std::string_view data) {
    std::printf("{\"request_id\":\"%.*s\",\"ok\":true,\"data\":%.*s}\n", static_cast<int>(request_id.size()), request_id.data(),
                static_cast<int>(data.size()), data.data());
}

[[nodiscard]] std::optional<std::string> json_string(std::string_view json, std::string_view key) {
    const std::string needle = "\"" + std::string(key) + "\"";
    const auto field = json.find(needle);
    if (field == std::string_view::npos) return std::nullopt;
    const auto colon = json.find(':', field + needle.size());
    if (colon == std::string_view::npos) return std::nullopt;
    const auto first_quote = json.find('"', colon + 1U);
    if (first_quote == std::string_view::npos) return std::nullopt;
    std::string result;
    bool escaping = false;
    for (std::size_t i = first_quote + 1U; i < json.size(); ++i) {
        const char c = json[i];
        if (escaping) {
            if (c != '"' && c != '\\' && c != '/') return std::nullopt;
            result.push_back(c); escaping = false; continue;
        }
        if (c == '\\') { escaping = true; continue; }
        if (c == '"') return result;
        if (static_cast<unsigned char>(c) < 0x20U) return std::nullopt;
        result.push_back(c);
    }
    return std::nullopt;
}

[[nodiscard]] std::optional<std::uint32_t> json_unsigned(std::string_view json, std::string_view key) {
    const std::string needle = "\"" + std::string(key) + "\"";
    const auto field = json.find(needle);
    if (field == std::string_view::npos) return std::nullopt;
    const auto colon = json.find(':', field + needle.size());
    if (colon == std::string_view::npos) return std::nullopt;
    std::size_t begin = colon + 1U;
    while (begin < json.size() && (json[begin] == ' ' || json[begin] == '\t')) ++begin;
    std::uint32_t value = 0;
    std::size_t index = begin;
    while (index < json.size() && json[index] >= '0' && json[index] <= '9') {
        const std::uint32_t digit = static_cast<std::uint32_t>(json[index] - '0');
        if (value > (UINT32_MAX - digit) / 10U) return std::nullopt;
        value = value * 10U + digit;
        ++index;
    }
    return index == begin ? std::nullopt : std::optional<std::uint32_t>(value);
}

[[nodiscard]] std::optional<bool> json_bool(std::string_view json, std::string_view key) {
    const std::string needle = "\"" + std::string(key) + "\"";
    const auto field = json.find(needle);
    if (field == std::string_view::npos) return std::nullopt;
    const auto colon = json.find(':', field + needle.size());
    if (colon == std::string_view::npos) return std::nullopt;
    const auto value = json.substr(colon + 1U);
    if (value.starts_with("true")) return true;
    if (value.starts_with("false")) return false;
    return std::nullopt;
}

[[nodiscard]] std::optional<pocket_locator::config::DisplayBlockKind> block_kind(std::string_view value) {
    using pocket_locator::config::DisplayBlockKind;
    if (value == "battery") return DisplayBlockKind::Battery;
    if (value == "time") return DisplayBlockKind::Time;
    if (value == "date") return DisplayBlockKind::Date;
    if (value == "text") return DisplayBlockKind::Text;
    if (value == "space") return DisplayBlockKind::Space;
    if (value == "separator") return DisplayBlockKind::Separator;
    return std::nullopt;
}

[[nodiscard]] std::optional<std::size_t> matching_delimiter(std::string_view text, std::size_t open, char opening, char closing) {
    if (open >= text.size() || text[open] != opening) return std::nullopt;
    int depth = 0; bool in_string = false; bool escaping = false;
    for (std::size_t i = open; i < text.size(); ++i) {
        const char c = text[i];
        if (in_string) {
            if (escaping) escaping = false;
            else if (c == '\\') escaping = true;
            else if (c == '"') in_string = false;
            continue;
        }
        if (c == '"') in_string = true;
        else if (c == opening) ++depth;
        else if (c == closing && --depth == 0) return i;
    }
    return std::nullopt;
}

[[nodiscard]] std::optional<std::vector<pocket_locator::config::DisplayBlock>> parse_blocks(std::string_view json) {
    const auto field = json.find("\"bottom_blocks\"");
    if (field == std::string_view::npos) return std::nullopt;
    const auto open = json.find('[', field);
    const auto close = matching_delimiter(json, open, '[', ']');
    if (open == std::string_view::npos || !close) return std::nullopt;
    std::vector<pocket_locator::config::DisplayBlock> blocks;
    std::size_t cursor = open + 1U;
    while (cursor < *close) {
        const auto begin = json.find('{', cursor);
        if (begin == std::string_view::npos || begin >= *close) break;
        const auto end = matching_delimiter(json, begin, '{', '}');
        if (!end || *end > *close) return std::nullopt;
        const auto object = json.substr(begin, *end - begin + 1U);
        const auto kind = json_string(object, "kind");
        if (!kind || !block_kind(*kind)) return std::nullopt;
        blocks.push_back({*block_kind(*kind), json_string(object, "value").value_or("")});
        cursor = *end + 1U;
    }
    return blocks.empty() ? std::nullopt : std::optional(blocks);
}

[[nodiscard]] std::optional<std::int64_t> json_signed64(std::string_view json, std::string_view key) {
    const std::string needle = "\"" + std::string(key) + "\"";
    const auto field = json.find(needle);
    if (field == std::string_view::npos) return std::nullopt;
    const auto colon = json.find(':', field + needle.size());
    if (colon == std::string_view::npos) return std::nullopt;
    std::size_t i = colon + 1U; while (i < json.size() && (json[i] == ' ' || json[i] == '\t')) ++i;
    bool negative = i < json.size() && json[i] == '-'; if (negative) ++i;
    std::int64_t value = 0; const auto begin = i;
    while (i < json.size() && json[i] >= '0' && json[i] <= '9') { if (value > (INT64_MAX - (json[i] - '0')) / 10) return std::nullopt; value = value * 10 + (json[i++] - '0'); }
    if (i == begin) return std::nullopt;
    return negative ? -value : value;
}

[[nodiscard]] std::optional<std::string_view> json_object(std::string_view json, std::string_view key) {
    const std::string needle = "\"" + std::string(key) + "\"";
    const auto field = json.find(needle);
    if (field == std::string_view::npos) return std::nullopt;
    const auto open = json.find('{', field + needle.size());
    if (open == std::string_view::npos) return std::nullopt;
    const auto close = matching_delimiter(json, open, '{', '}');
    return close ? std::optional(json.substr(open, *close - open + 1U)) : std::nullopt;
}

[[nodiscard]] std::optional<std::int64_t> iso_utc_epoch(std::string_view value) {
    // Host-generated values are canonical UTC ISO 8601 (`YYYY-MM-DDTHH:MM:SS+00:00`).
    if (value.size() < 19U || value[4] != '-' || value[7] != '-' || value[10] != 'T' || value[13] != ':' || value[16] != ':') return std::nullopt;
    const auto integer = [&](std::size_t at, std::size_t count) -> std::optional<int> {
        int result = 0; for (std::size_t i = 0; i < count; ++i) { const char c = value[at + i]; if (c < '0' || c > '9') return std::nullopt; result = result * 10 + c - '0'; } return result;
    };
    const auto year = integer(0, 4); const auto month = integer(5, 2); const auto day = integer(8, 2);
    const auto hour = integer(11, 2); const auto minute = integer(14, 2); const auto second = integer(17, 2);
    if (!year || !month || !day || !hour || !minute || !second || *month < 1 || *month > 12 || *day < 1 || *day > 31 || *hour > 23 || *minute > 59 || *second > 59) return std::nullopt;
    int adjusted_year = *year - (*month <= 2 ? 1 : 0);
    const int era = (adjusted_year >= 0 ? adjusted_year : adjusted_year - 399) / 400;
    const unsigned yoe = static_cast<unsigned>(adjusted_year - era * 400);
    const unsigned mp = *month > 2 ? static_cast<unsigned>(*month - 3) : static_cast<unsigned>(*month + 9);
    const unsigned doy = (153U * mp + 2U) / 5U + static_cast<unsigned>(*day) - 1U;
    const unsigned doe = yoe * 365U + yoe / 4U - yoe / 100U + doy;
    return (static_cast<std::int64_t>(era) * 146097 + static_cast<int>(doe) - 719468) * 86400 + *hour * 3600 + *minute * 60 + *second;
}

[[nodiscard]] std::optional<pocket_locator::time::ZoneTable> parse_zone_table(std::string_view json, std::string_view expected_name) {
    const auto object = json_object(json, "timezone_table");
    if (!object) return std::nullopt;
    pocket_locator::time::ZoneTable table{};
    const auto name = json_string(*object, "zone_name");
    const auto generated = json_string(*object, "generated_at");
    const auto expires = json_string(*object, "expires_at");
    const auto expiry_year = json_unsigned(*object, "expiry_year");
    const auto initial_offset = json_signed64(*object, "initial_offset_seconds");
    const auto abbreviation = json_string(*object, "initial_abbreviation");
    if (!name || !generated || !expires || !expiry_year || !initial_offset || !abbreviation || *name != expected_name) return std::nullopt;
    const auto generated_epoch = iso_utc_epoch(*generated);
    const auto expires_epoch = iso_utc_epoch(*expires);
    if (!generated_epoch || !expires_epoch || *expires_epoch - *generated_epoch < 15LL * 365LL * 86400LL ||
        *initial_offset < INT32_MIN || *initial_offset > INT32_MAX || *expiry_year < 2000U ||
        expires->substr(0, 4) != std::to_string(*expiry_year)) return std::nullopt;
    table.zone_name = *name;
    table.generated_at_epoch_seconds = *generated_epoch;
    table.expires_at_epoch_seconds = *expires_epoch;
    table.initial_offset_seconds = static_cast<std::int32_t>(*initial_offset);
    table.initial_abbreviation = *abbreviation;
    const auto transitions_key = object->find("\"transitions\"");
    if (transitions_key == std::string_view::npos) return std::nullopt;
    const auto open = object->find('[', transitions_key);
    const auto close = matching_delimiter(*object, open, '[', ']');
    if (open == std::string_view::npos || !close) return std::nullopt;
    std::size_t cursor = open + 1U;
    while (cursor < *close) {
        const auto begin = object->find('{', cursor);
        if (begin == std::string_view::npos || begin >= *close) break;
        const auto end = matching_delimiter(*object, begin, '{', '}');
        if (!end || *end > *close) return std::nullopt;
        const auto item = object->substr(begin, *end - begin + 1U);
        const auto at = json_signed64(item, "utc_epoch");
        const auto offset = json_signed64(item, "offset_seconds");
        const auto abbr = json_string(item, "abbreviation");
        if (!at || !offset || !abbr || *offset < INT32_MIN || *offset > INT32_MAX) return std::nullopt;
        table.transitions.push_back({*at, static_cast<std::int32_t>(*offset), *abbr});
        cursor = *end + 1U;
    }
    return pocket_locator::time::validate(table) == pocket_locator::time::ZoneTableError::None ? std::optional(table) : std::nullopt;
}

[[nodiscard]] std::optional<pocket_locator::config::Settings> config_from_request(std::string_view json) {
    using pocket_locator::app::GnssMode;
    auto config = pocket_locator::config::factory_defaults();
    const auto zone = json_string(json, "timezone");
    const auto mode = json_string(json, "gnss_mode");
    const auto top_template = json_string(json, "top_template");
    const auto blocks = parse_blocks(json);
    const auto clock_24h = json_bool(json, "clock_24h");
    const auto show_seconds = json_bool(json, "show_seconds");
    const auto date_format = json_string(json, "date_format");
    const auto tracking = json_unsigned(json, "tracking_interval_seconds");
    const auto acquisition = json_unsigned(json, "acquisition_timeout_seconds");
    const auto dim = json_unsigned(json, "dim_deadline_seconds");
    const auto shutdown = json_unsigned(json, "shutdown_deadline_seconds");
    const auto normal = json_unsigned(json, "normal_brightness_percent");
    const auto dim_brightness = json_unsigned(json, "dim_brightness_percent");
    if (!zone || !mode || !top_template || *top_template != "GRID: {grid6}" || !blocks || !clock_24h || !show_seconds || !date_format ||
        !tracking || !acquisition || !dim || !shutdown || !normal || !dim_brightness) return std::nullopt;
    config.named_time_zone = *zone;
    if (*mode == "single_fix") config.gnss_mode = GnssMode::SingleFix;
    else if (*mode == "tracking") config.gnss_mode = GnssMode::Tracking;
    else return std::nullopt;
    config.bottom_blocks = *blocks;
    config.clock_24h = *clock_24h;
    config.show_seconds = *show_seconds;
    if (*date_format == "DD/MM") config.date_format = pocket_locator::config::DateFormat::DdMm;
    else if (*date_format == "MM/DD") config.date_format = pocket_locator::config::DateFormat::MmDd;
    else if (*date_format == "DDMMM") config.date_format = pocket_locator::config::DateFormat::DdMmm;
    else if (*date_format == "YYYY-MM-DD") config.date_format = pocket_locator::config::DateFormat::YyyyMmDd;
    else return std::nullopt;
    const auto zone_table = parse_zone_table(json, *zone);
    if (!zone_table) return std::nullopt;
    config.zone_table = *zone_table;
    constexpr std::uint32_t kMillisecondsPerSecond = 1'000;
    if (*tracking > UINT32_MAX / kMillisecondsPerSecond || *acquisition > UINT32_MAX / kMillisecondsPerSecond ||
        *dim > UINT32_MAX / kMillisecondsPerSecond || *shutdown > UINT32_MAX / kMillisecondsPerSecond ||
        *normal > 100U || *dim_brightness > 100U) return std::nullopt;
    config.tracking_render_interval_ms = *tracking * kMillisecondsPerSecond;
    config.acquisition_timeout_ms = *acquisition * kMillisecondsPerSecond;
    config.dim_deadline_ms = *dim * kMillisecondsPerSecond;
    config.shutdown_deadline_ms = *shutdown * kMillisecondsPerSecond;
    config.normal_brightness = static_cast<std::uint8_t>(*normal);
    config.dim_brightness = static_cast<std::uint8_t>(*dim_brightness);
    return pocket_locator::config::validate(config) == pocket_locator::config::ValidationError::None ? std::optional(config) : std::nullopt;
}

void render(pocket_locator::display::Hd44780& lcd, pocket_locator::app::CheckSession& session,
            const pocket_locator::board::BatteryReading& battery, bool charging,
            const pocket_locator::config::Settings& settings, pocket_locator::app::State& last_state,
            std::string& last_grid, std::string& last_bottom, const std::optional<locator::CurrentFix>& latest_fix,
            bool& timezone_refresh_required) {
    const auto state = session.state();
    const bool active = state == pocket_locator::app::State::Acquiring || state == pocket_locator::app::State::DisplayFix ||
                        state == pocket_locator::app::State::Dimmed || state == pocket_locator::app::State::NoGps ||
                        state == pocket_locator::app::State::FactoryReset;
    lcd.set_enabled(active);
    if (state == pocket_locator::app::State::UsbIdle || state == pocket_locator::app::State::Off ||
        state == pocket_locator::app::State::PressCheck) {
        lcd.set_backlight_percent(0);
    } else if (session.backlight() == pocket_locator::app::Backlight::Dim) {
        lcd.set_backlight_percent(settings.dim_brightness);
    } else {
        lcd.set_backlight_percent(settings.normal_brightness);
    }
    std::string bottom;
    if ((state == pocket_locator::app::State::DisplayFix || state == pocket_locator::app::State::Dimmed) && latest_fix) {
        const auto screen = pocket_locator::display::format_fix_screen(settings, session.displayed_grid(), *latest_fix, battery.percent, charging);
        bottom = screen.bottom_row;
        timezone_refresh_required = screen.timezone_refresh_required;
    }
    if (state == last_state && session.displayed_grid() == last_grid && bottom == last_bottom) return;
    if (state == pocket_locator::app::State::Acquiring) lcd.show_acquiring();
    else if (state == pocket_locator::app::State::NoGps) lcd.show_no_gps();
    else if (state == pocket_locator::app::State::DisplayFix || state == pocket_locator::app::State::Dimmed) {
        lcd.show_grid(session.displayed_grid(), bottom);
    } else if (state == pocket_locator::app::State::FactoryReset) lcd.write_rows("FACTORY RESET", "RESTARTING");
    last_state = state;
    last_grid = session.displayed_grid();
    last_bottom = bottom;
}

}  // namespace

int main() {
    using namespace pocket_locator;
    stdio_init_all();
    board::PowerHold power;
    power.init();
    board::Buttons buttons;
    buttons.init();
    board::BatteryAdc battery;
    battery.init();
    display::Hd44780 lcd;
    lcd.init();
    gnss::UartGnss gnss;
    gnss.init();
    storage::FlashConfigStore flash;
    auto loaded = flash.load();
    auto settings = loaded.settings;
    app::CheckSession session(session_settings(settings));
    usb::NdjsonFramer framer;
    app::State last_state = app::State::Off;
    std::string last_grid;
    std::string last_bottom;
    std::optional<locator::CurrentFix> latest_fix;
    bool timezone_refresh_required = false;
    bool last_gnss = false;
    bool power_held = false;
    watchdog_enable(8'000, true);

    while (true) {
        const auto now = now_ms();
        watchdog_update();
        auto update = session.set_usb_present(power.usb_present(), now);
        const auto merge = [](app::Update& target, const app::Update& next) {
            target.display_changed = target.display_changed || next.display_changed;
            target.power_released = target.power_released || next.power_released;
            target.factory_reset_requested = target.factory_reset_requested || next.factory_reset_requested;
        };
        board::ButtonEvent button{};
        while (buttons.poll(now, button)) {
            merge(update, button.down ? session.button_down(button.button, button.pressed_at_ms) : session.button_up(button.button, now));
        }
        merge(update, session.tick(now));
        if (session.state() == app::State::Acquiring && !power_held) {
            power.assert_hold();
            power_held = true;
        }
        if (session.gnss_is_active() != last_gnss) {
            gnss.set_enabled(session.gnss_is_active());
            last_gnss = session.gnss_is_active();
        }
        if (const auto fix = gnss.poll(); fix.has_value()) {
            latest_fix = fix;
            if (const auto grid = locator::maidenhead_6(fix->position.latitude_degrees, fix->position.longitude_degrees); grid) {
                merge(update, session.valid_fix(*grid, now));
            }
        }
        if (session.state() == app::State::UsbIdle || session.state() == app::State::Off || session.state() == app::State::PressCheck) {
            latest_fix.reset();
        }

        for (int character = getchar_timeout_us(0); character != PICO_ERROR_TIMEOUT; character = getchar_timeout_us(0)) {
            const auto frame = framer.push(static_cast<char>(character));
            if (!frame) continue;
            if (frame->kind == usb::FrameKind::TooLarge) {
                std::printf("%s\n", usb::error_response("", usb::ErrorCode::MessageTooLarge).c_str());
                continue;
            }
            const auto request = usb::parse_request(frame->payload);
            if (!request.request) {
                std::printf("%s\n", usb::error_response("", *request.error).c_str());
                continue;
            }
            const auto& request_value = *request.request;
            if (request_value.protocol_version != usb::kProtocolVersion) {
                std::printf("%s\n", usb::error_response(request_value.request_id, usb::ErrorCode::UnsupportedProtocol).c_str());
                continue;
            }
            switch (request_value.command) {
                case usb::Command::Hello:
                    response(request_value.request_id, "{\"protocol_version\":1,\"device\":\"pocket-locator\"}"); break;
                case usb::Command::GetInfo:
                    response(request_value.request_id, "{\"firmware_version\":\"0.1.0\",\"hardware_revision\":\"rev-a\"}"); break;
                case usb::Command::GetConfig:
                    response(request_value.request_id, config_json(settings)); break;
                case usb::Command::GetDiagnostics: {
                    const auto reading = battery.read();
                    const bool session_active = session.state() == app::State::Acquiring || session.state() == app::State::DisplayFix ||
                                                session.state() == app::State::Dimmed || session.state() == app::State::NoGps;
                    std::string diagnostics =
                             "{\"config_crc_healthy\":" + std::string(loaded.crc_healthy ? "true" : "false") +
                                 ",\"battery_adc\":" + std::to_string(reading.raw) + ",\"battery_level\":" +
                                 std::to_string(reading.percent) + ",\"battery_millivolts\":" + std::to_string(reading.millivolts) +
                                 ",\"onboard_temperature_celsius\":" + std::to_string(reading.temperature_centi_celsius / 100) +
                                 ",\"usb_present\":" +
                                 std::string(power.usb_present() ? "true" : "false") + ",\"gnss_state\":\"" +
                                 (gnss.enabled() ? "active" : "off") + "\",\"timezone_refresh_required\":" +
                                 std::string(timezone_refresh_required ? "true" : "false") + ",\"charger_active\":" +
                                 std::string(power.charger_active() ? "true" : "false") + ",\"gnss_fix_quality\":" +
                                 std::to_string(session_active && latest_fix ? latest_fix->fix_quality : 0U) + ",\"satellites_used\":" +
                                 std::to_string(session_active && latest_fix ? latest_fix->satellites_used : 0U);
                    if (session_active && latest_fix) {
                        diagnostics += ",\"latest_coordinates\":{\"latitude\":" + std::to_string(latest_fix->position.latitude_degrees) +
                                       ",\"longitude\":" + std::to_string(latest_fix->position.longitude_degrees) + "}";
                    }
                    response(request_value.request_id, diagnostics + "}");
                    break;
                }
                case usb::Command::ValidateConfig:
                case usb::Command::SetConfig: {
                    const auto candidate = config_from_request(request_value.raw_json);
                    if (!candidate) {
                        std::printf("%s\n", usb::error_response(request_value.request_id, usb::ErrorCode::InvalidField).c_str());
                        break;
                    }
                    if (request_value.command == usb::Command::SetConfig) {
                        if (flash.write(*candidate) != config::ValidationError::None) {
                            std::printf("%s\n", usb::error_response(request_value.request_id, usb::ErrorCode::InvalidField).c_str());
                            break;
                        }
                        settings = *candidate;
                        loaded = flash.load();
                        if (session.state() == app::State::UsbIdle) {
                            session = app::CheckSession(session_settings(settings));
                            (void)session.set_usb_present(power.usb_present(), now);
                        }
                    }
                    response(request_value.request_id, request_value.command == usb::Command::SetConfig ? config_json(*candidate) : "{\"valid\":true}");
                    break;
                }
                case usb::Command::FactoryReset:
                    (void)flash.factory_reset();
                    settings = config::factory_defaults();
                    loaded = flash.load();
                    if (session.state() == app::State::UsbIdle) {
                        session = app::CheckSession(session_settings(settings));
                        (void)session.set_usb_present(power.usb_present(), now);
                    }
                    response(request_value.request_id, config_json(settings));
                    break;
                case usb::Command::RebootToBootloader:
                    response(request_value.request_id, "{\"rebooting\":true}");
                    sleep_ms(25);
                    board::reboot_to_bootloader();
                    break;
            }
        }

        const auto reading = battery.read();
        render(lcd, session, reading, power.charger_active(), settings, last_state, last_grid, last_bottom, latest_fix,
               timezone_refresh_required);
        if (update.factory_reset_requested) {
            (void)flash.factory_reset();
            watchdog_reboot(0, 0, 0);
        }
        if (update.power_released) {
            gnss.set_enabled(false);
            latest_fix.reset();
            lcd.set_backlight_percent(0);
            power.release();
            power_held = false;
        }
        if (session.state() == app::State::UsbIdle && power_held) {
            gnss.set_enabled(false);
            latest_fix.reset();
            lcd.set_enabled(false);
            power.release();
            power_held = false;
        }
        sleep_ms(5);
    }
}
