// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/usb/protocol.hpp"

#include <cctype>
#include <limits>

namespace pocket_locator::usb {
namespace {

struct FieldSearch {
    bool found{false};
    bool valid{false};
    std::string value;
};

void skip_spaces(std::string_view text, std::size_t& index) {
    while (index < text.size() && std::isspace(static_cast<unsigned char>(text[index])) != 0) {
        ++index;
    }
}

bool parse_string(std::string_view text, std::size_t& index, std::string& value) {
    if (index >= text.size() || text[index] != '"') {
        return false;
    }
    ++index;
    value.clear();
    while (index < text.size()) {
        const char current = text[index++];
        if (current == '"') {
            return true;
        }
        if (current == '\\') {
            if (index >= text.size()) {
                return false;
            }
            const char escaped = text[index++];
            if (escaped != '"' && escaped != '\\' && escaped != '/') {
                return false;
            }
            value.push_back(escaped);
            continue;
        }
        if (static_cast<unsigned char>(current) < 0x20U) {
            return false;
        }
        value.push_back(current);
    }
    return false;
}

bool value_is_structurally_valid(std::string_view text) {
    std::size_t index = 0;
    skip_spaces(text, index);
    if (index >= text.size() || text[index] != '{') {
        return false;
    }
    int object_depth = 0;
    int array_depth = 0;
    bool in_string = false;
    bool escaping = false;
    bool root_closed = false;
    for (; index < text.size(); ++index) {
        const char current = text[index];
        if (root_closed) {
            if (std::isspace(static_cast<unsigned char>(current)) == 0) {
                return false;
            }
            continue;
        }
        if (in_string) {
            if (escaping) {
                escaping = false;
            } else if (current == '\\') {
                escaping = true;
            } else if (current == '"') {
                in_string = false;
            } else if (static_cast<unsigned char>(current) < 0x20U) {
                return false;
            }
            continue;
        }
        if (current == '"') {
            in_string = true;
        } else if (current == '{') {
            ++object_depth;
        } else if (current == '}') {
            if (--object_depth < 0) {
                return false;
            }
            if (object_depth == 0 && array_depth == 0) {
                root_closed = true;
            }
        } else if (current == '[') {
            ++array_depth;
        } else if (current == ']') {
            if (--array_depth < 0) {
                return false;
            }
        }
    }
    return !in_string && !escaping && root_closed && object_depth == 0 && array_depth == 0;
}

bool valid_request_id(std::string_view request_id) {
    if (request_id.empty() || request_id.size() > 64) {
        return false;
    }
    for (const unsigned char character : request_id) {
        if (!std::isalnum(character) && character != '-' && character != '_' && character != '.') {
            return false;
        }
    }
    return true;
}

FieldSearch string_field(std::string_view text, std::string_view sought_key) {
    FieldSearch result{};
    std::size_t index = 0;
    skip_spaces(text, index);
    if (index >= text.size() || text[index++] != '{') {
        return result;
    }
    while (index < text.size()) {
        skip_spaces(text, index);
        if (index >= text.size() || text[index] == '}') {
            break;
        }
        std::string key;
        if (!parse_string(text, index, key)) {
            return result;
        }
        skip_spaces(text, index);
        if (index >= text.size() || text[index++] != ':') {
            return result;
        }
        skip_spaces(text, index);
        if (key == sought_key) {
            if (result.found) {
                result.valid = false;
                return result;
            }
            if (!parse_string(text, index, result.value)) {
                return result;
            }
            result.found = true;
            result.valid = true;
        } else {
            // This parser validates only the protocol envelope. Values belonging
            // to the command-specific body are validated by the command handler.
            if (index >= text.size()) {
                return result;
            }
            if (text[index] == '"') {
                std::string ignored;
                if (!parse_string(text, index, ignored)) {
                    return result;
                }
            } else {
                int depth = 0;
                bool nested_string = false;
                bool nested_escape = false;
                while (index < text.size()) {
                    const char current = text[index];
                    if (nested_string) {
                        if (nested_escape) {
                            nested_escape = false;
                        } else if (current == '\\') {
                            nested_escape = true;
                        } else if (current == '"') {
                            nested_string = false;
                        }
                    } else if (current == '"') {
                        nested_string = true;
                    } else if (current == '{' || current == '[') {
                        ++depth;
                    } else if (current == '}' || current == ']') {
                        if (depth == 0) {
                            break;
                        }
                        --depth;
                    } else if (current == ',' && depth == 0) {
                        break;
                    }
                    ++index;
                }
            }
        }
        skip_spaces(text, index);
        if (index < text.size() && text[index] == ',') {
            ++index;
            continue;
        }
        if (index < text.size() && text[index] == '}') {
            break;
        }
        return result;
    }
    return result;
}

FieldSearch unsigned_field(std::string_view text, std::string_view sought_key) {
    FieldSearch result{};
    std::size_t index = 0;
    skip_spaces(text, index);
    if (index >= text.size() || text[index++] != '{') {
        return result;
    }
    while (index < text.size()) {
        skip_spaces(text, index);
        if (index >= text.size() || text[index] == '}') {
            break;
        }
        std::string key;
        if (!parse_string(text, index, key)) {
            return result;
        }
        skip_spaces(text, index);
        if (index >= text.size() || text[index++] != ':') {
            return result;
        }
        skip_spaces(text, index);
        if (key == sought_key) {
            if (result.found) {
                result.valid = false;
                return result;
            }
            if (index >= text.size() || !std::isdigit(static_cast<unsigned char>(text[index]))) {
                return result;
            }
            std::uint64_t value = 0;
            while (index < text.size() && std::isdigit(static_cast<unsigned char>(text[index]))) {
                value = value * 10U + static_cast<unsigned>(text[index++] - '0');
                if (value > std::numeric_limits<std::uint32_t>::max()) {
                    return result;
                }
            }
            result.found = true;
            result.valid = true;
            result.value = std::to_string(value);
        } else {
            // Advance exactly as string_field does for values not owned by this layer.
            if (index >= text.size()) {
                return result;
            }
            if (text[index] == '"') {
                std::string ignored;
                if (!parse_string(text, index, ignored)) {
                    return result;
                }
            } else {
                int depth = 0;
                bool nested_string = false;
                bool nested_escape = false;
                while (index < text.size()) {
                    const char current = text[index];
                    if (nested_string) {
                        if (nested_escape) {
                            nested_escape = false;
                        } else if (current == '\\') {
                            nested_escape = true;
                        } else if (current == '"') {
                            nested_string = false;
                        }
                    } else if (current == '"') {
                        nested_string = true;
                    } else if (current == '{' || current == '[') {
                        ++depth;
                    } else if (current == '}' || current == ']') {
                        if (depth == 0) {
                            break;
                        }
                        --depth;
                    } else if (current == ',' && depth == 0) {
                        break;
                    }
                    ++index;
                }
            }
        }
        skip_spaces(text, index);
        if (index < text.size() && text[index] == ',') {
            ++index;
            continue;
        }
        if (index < text.size() && text[index] == '}') {
            break;
        }
        return result;
    }
    return result;
}

std::optional<Command> command_from_name(std::string_view name) {
    if (name == "hello") return Command::Hello;
    if (name == "get_info") return Command::GetInfo;
    if (name == "get_config") return Command::GetConfig;
    if (name == "validate_config") return Command::ValidateConfig;
    if (name == "set_config") return Command::SetConfig;
    if (name == "get_diagnostics") return Command::GetDiagnostics;
    if (name == "factory_reset") return Command::FactoryReset;
    if (name == "reboot_to_bootloader") return Command::RebootToBootloader;
    return std::nullopt;
}

}  // namespace

NdjsonFramer::NdjsonFramer(std::size_t max_message_bytes) : max_message_bytes_(max_message_bytes) {}

std::optional<Frame> NdjsonFramer::push(char byte) {
    if (discarding_oversized_frame_) {
        if (byte == '\n') {
            discarding_oversized_frame_ = false;
        }
        return std::nullopt;
    }
    if (byte == '\n') {
        Frame frame{FrameKind::Complete, std::move(buffer_)};
        buffer_.clear();
        if (!frame.payload.empty() && frame.payload.back() == '\r') {
            frame.payload.pop_back();
        }
        return frame;
    }
    if (buffer_.size() >= max_message_bytes_) {
        buffer_.clear();
        discarding_oversized_frame_ = true;
        return Frame{FrameKind::TooLarge, {}};
    }
    buffer_.push_back(byte);
    return std::nullopt;
}

void NdjsonFramer::reset() {
    buffer_.clear();
    discarding_oversized_frame_ = false;
}

ParseResult parse_request(std::string_view json) {
    if (json.size() > kMaxMessageBytes) {
        return {{}, ErrorCode::MessageTooLarge};
    }
    if (!value_is_structurally_valid(json)) {
        return {{}, ErrorCode::InvalidJson};
    }

    const FieldSearch version = unsigned_field(json, "protocol_version");
    const FieldSearch request_id = string_field(json, "request_id");
    const FieldSearch command = string_field(json, "command");
    if (!version.found || !request_id.found || !command.found) {
        return {{}, ErrorCode::MissingField};
    }
    if (!version.valid || !request_id.valid || !command.valid) {
        return {{}, ErrorCode::InvalidField};
    }
    if (!valid_request_id(request_id.value)) {
        return {{}, ErrorCode::InvalidField};
    }
    if (version.value != std::to_string(kProtocolVersion)) {
        return {{}, ErrorCode::UnsupportedProtocol};
    }
    const std::optional<Command> parsed_command = command_from_name(command.value);
    if (!parsed_command.has_value()) {
        return {{}, ErrorCode::UnknownCommand};
    }
    return {Request{kProtocolVersion, request_id.value, *parsed_command, std::string(json)}, {}};
}

const char* error_code_name(ErrorCode code) {
    switch (code) {
        case ErrorCode::InvalidJson: return "invalid_json";
        case ErrorCode::MessageTooLarge: return "message_too_large";
        case ErrorCode::MissingField: return "missing_field";
        case ErrorCode::InvalidField: return "invalid_field";
        case ErrorCode::UnsupportedProtocol: return "unsupported_protocol";
        case ErrorCode::UnknownCommand: return "unknown_command";
    }
    return "invalid_field";
}

std::string error_response(std::string_view request_id, ErrorCode code) {
    const std::string stable_code = error_code_name(code);
    return std::string{"{\"request_id\":\""} + std::string(request_id) +
           "\",\"ok\":false,\"error\":{\"code\":\"" + stable_code +
           "\",\"message\":\"" + stable_code + "\"}}\n";
}

}  // namespace pocket_locator::usb
