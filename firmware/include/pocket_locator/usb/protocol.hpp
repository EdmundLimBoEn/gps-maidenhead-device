// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>

namespace pocket_locator::usb {

constexpr std::uint32_t kProtocolVersion = 1;
constexpr std::size_t kMaxMessageBytes = 4'096;

enum class FrameKind { Complete, TooLarge };

struct Frame {
    FrameKind kind{FrameKind::Complete};
    std::string payload;
};

class NdjsonFramer {
public:
    explicit NdjsonFramer(std::size_t max_message_bytes = kMaxMessageBytes);

    [[nodiscard]] std::optional<Frame> push(char byte);
    void reset();

private:
    std::size_t max_message_bytes_;
    bool discarding_oversized_frame_{false};
    std::string buffer_;
};

enum class Command {
    Hello,
    GetInfo,
    GetConfig,
    ValidateConfig,
    SetConfig,
    GetDiagnostics,
    FactoryReset,
    RebootToBootloader,
};

enum class ErrorCode {
    InvalidJson,
    MessageTooLarge,
    MissingField,
    InvalidField,
    UnsupportedProtocol,
    UnknownCommand,
    StorageError,
    Busy,
};

struct Request {
    std::uint32_t protocol_version{0};
    std::string request_id;
    Command command{Command::Hello};
    std::string raw_json;
};

struct ParseResult {
    std::optional<Request> request;
    std::optional<ErrorCode> error;
};

[[nodiscard]] ParseResult parse_request(std::string_view json);
[[nodiscard]] const char* error_code_name(ErrorCode code);
[[nodiscard]] std::string error_response(std::string_view request_id, ErrorCode code);
[[nodiscard]] bool object_has_exact_keys(
    std::string_view json, std::span<const std::string_view> expected_keys);

}  // namespace pocket_locator::usb
