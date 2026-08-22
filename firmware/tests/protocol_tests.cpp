// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include "pocket_locator/usb/protocol.hpp"

#include <array>
#include <string_view>

namespace {

using pocket_locator::usb::Command;
using pocket_locator::usb::ErrorCode;
using pocket_locator::usb::FrameKind;
using pocket_locator::usb::NdjsonFramer;
using pocket_locator::usb::parse_request;

}  // namespace

TEST(ndjson_framer_preserves_complete_line_and_strips_crlf) {
    NdjsonFramer framer;
    std::optional<pocket_locator::usb::Frame> completed;
    for (const char byte : std::string("{\"protocol_version\":1}\r\n")) {
        completed = framer.push(byte);
    }
    REQUIRE(completed.has_value());
    REQUIRE_EQ(completed->kind, FrameKind::Complete);
    REQUIRE_EQ(completed->payload, std::string("{\"protocol_version\":1}"));
}

TEST(ndjson_framer_rejects_oversized_message_then_recovers_on_next_line) {
    NdjsonFramer framer(4);
    std::optional<pocket_locator::usb::Frame> result;
    for (const char byte : std::string("12345")) {
        result = framer.push(byte);
    }
    REQUIRE(result.has_value());
    REQUIRE_EQ(result->kind, FrameKind::TooLarge);
    REQUIRE(!framer.push('x').has_value());
    REQUIRE(!framer.push('\n').has_value());
    for (const char byte : std::string("ok\n")) {
        result = framer.push(byte);
    }
    REQUIRE(result.has_value());
    REQUIRE_EQ(result->kind, FrameKind::Complete);
    REQUIRE_EQ(result->payload, std::string("ok"));
}

TEST(protocol_parses_required_envelope_and_accepts_command_body) {
    const auto result = parse_request(
        "{\"protocol_version\":1,\"request_id\":\"req-7\",\"command\":\"set_config\",\"config\":{\"mode\":\"tracking\"}}");
    REQUIRE(result.request.has_value());
    REQUIRE(!result.error.has_value());
    REQUIRE_EQ(result.request->request_id, std::string("req-7"));
    REQUIRE_EQ(result.request->command, Command::SetConfig);
}

TEST(protocol_rejects_missing_malformed_unsupported_and_unknown_requests) {
    auto result = parse_request("{\"protocol_version\":1,\"request_id\":\"x\"}");
    REQUIRE_EQ(*result.error, ErrorCode::MissingField);

    result = parse_request("{\"protocol_version\":1,\"request_id\":\"x\",\"command\":");
    REQUIRE_EQ(*result.error, ErrorCode::InvalidJson);

    result = parse_request(
        "{\"protocol_version\":1,\"request_id\":\"x\",\"command\":\"hello\",\"x\":junk}");
    REQUIRE_EQ(*result.error, ErrorCode::InvalidJson);

    result = parse_request("{\"protocol_version\":2,\"request_id\":\"x\",\"command\":\"hello\"}");
    REQUIRE_EQ(*result.error, ErrorCode::UnsupportedProtocol);

    result = parse_request("{\"protocol_version\":1,\"request_id\":\"x\",\"command\":\"erase_everything\"}");
    REQUIRE_EQ(*result.error, ErrorCode::UnknownCommand);
}

TEST(protocol_rejects_duplicate_or_invalid_envelope_fields_and_emits_stable_error) {
    auto result = parse_request(
        "{\"protocol_version\":1,\"request_id\":\"x\",\"request_id\":\"y\",\"command\":\"hello\"}");
    REQUIRE_EQ(*result.error, ErrorCode::InvalidField);

    result = parse_request("{\"protocol_version\":1,\"request_id\":\"\",\"command\":\"hello\"}");
    REQUIRE_EQ(*result.error, ErrorCode::InvalidField);

    result = parse_request("{\"protocol_version\":1,\"request_id\":\"not valid\",\"command\":\"hello\"}");
    REQUIRE_EQ(*result.error, ErrorCode::InvalidField);

    result = parse_request(
        "{\"protocol_version\":1,\"request_id\":\"x\",\"command\":\"hello\",\"unexpected\":true}");
    REQUIRE_EQ(*result.error, ErrorCode::InvalidField);

    result = parse_request(
        "{\"protocol_version\":1,\"request_id\":\"x\",\"command\":\"set_config\"}");
    REQUIRE_EQ(*result.error, ErrorCode::InvalidField);

    result = parse_request(std::string(pocket_locator::usb::kMaxMessageBytes + 1U, ' '));
    REQUIRE_EQ(*result.error, ErrorCode::MessageTooLarge);

    REQUIRE_EQ(pocket_locator::usb::error_response("x", ErrorCode::UnknownCommand),
               std::string("{\"request_id\":\"x\",\"ok\":false,\"error\":{\"code\":\"unknown_command\","
                           "\"message\":\"unknown_command\"}}\n"));
}

TEST(strict_json_object_keys_reject_unknown_duplicate_and_malformed_values) {
    static constexpr std::array<std::string_view, 2> keys{"schema_version", "enabled"};
    REQUIRE(pocket_locator::usb::object_has_exact_keys(
        "{\"schema_version\":1,\"enabled\":true}", keys));
    REQUIRE(!pocket_locator::usb::object_has_exact_keys(
        "{\"schema_version\":1,\"enabled\":true,\"unknown\":0}", keys));
    REQUIRE(!pocket_locator::usb::object_has_exact_keys(
        "{\"schema_version\":1,\"schema_version\":1}", keys));
    REQUIRE(!pocket_locator::usb::object_has_exact_keys(
        "{\"schema_version\":1junk,\"enabled\":true}", keys));
    REQUIRE(!pocket_locator::usb::object_has_exact_keys(
        "{\"schema_version\":01,\"enabled\":true}", keys));
    REQUIRE(!pocket_locator::usb::object_has_exact_keys(
        "{\"schema_version\":1,\"enabled\":truejunk}", keys));
}
