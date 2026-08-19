// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/gnss/uart_gnss.hpp"

#include "hardware/gpio.h"
#include "hardware/uart.h"

namespace pocket_locator::gnss {
namespace {
uart_inst_t* const kGnssUart = uart0;
}

UartGnss::UartGnss(board::PinMap pins, std::uint32_t baud) : pins_(pins), baud_(baud) {}

void UartGnss::init() {
    uart_init(kGnssUart, baud_);
    gpio_set_function(pins_.gnss_uart_tx, GPIO_FUNC_UART);
    gpio_set_function(pins_.gnss_uart_rx, GPIO_FUNC_UART);
    uart_set_format(kGnssUart, 8, 1, UART_PARITY_NONE);
    uart_set_fifo_enabled(kGnssUart, true);
    gpio_init(pins_.gnss_enable);
    gpio_set_dir(pins_.gnss_enable, GPIO_OUT);
    set_enabled(false);
}

void UartGnss::set_enabled(bool enabled) {
    enabled_ = enabled;
    gpio_put(pins_.gnss_enable, enabled);
    if (!enabled) {
        line_length_ = 0;
        accumulator_.clear();
    }
}

std::optional<locator::CurrentFix> UartGnss::poll() {
    if (!enabled_) {
        return std::nullopt;
    }
    std::optional<locator::CurrentFix> fix;
    while (uart_is_readable(kGnssUart)) {
        const char byte = static_cast<char>(uart_getc(kGnssUart));
        if (byte == '\r') {
            continue;
        }
        if (byte == '\n') {
            if (line_length_ != 0U) {
                const auto parsed = locator::parse_nmea_sentence({line_.data(), line_length_});
                if (parsed.valid()) {
                    if (const auto current = accumulator_.ingest(*parsed.sentence); current.has_value()) {
                        fix = current;
                    }
                }
            }
            line_length_ = 0;
            continue;
        }
        if (line_length_ + 1U < line_.size()) {
            line_[line_length_++] = byte;
        } else {
            // A line longer than the parser's bounded input is discarded in
            // its entirety; never turn a truncated UART fragment into a fix.
            line_length_ = 0;
        }
    }
    return fix;
}

}  // namespace pocket_locator::gnss
