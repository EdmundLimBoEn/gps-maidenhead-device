// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/gnss/uart_gnss.hpp"

#include "hardware/gpio.h"
#include "hardware/uart.h"
#include "pico/stdlib.h"

namespace pocket_locator::gnss {
namespace {
uart_inst_t* const kGnssUart = uart0;
}

UartGnss::UartGnss(board::PinMap pins, std::uint32_t baud) : pins_(pins), baud_(baud) {}

void UartGnss::init() {
    gpio_init(pins_.gnss_enable);
    gpio_set_dir(pins_.gnss_enable, GPIO_OUT);
    set_enabled(false);
}

void UartGnss::set_enabled(bool enabled) {
    if (enabled == enabled_ && enabled) return;
    enabled_ = enabled;
    if (enabled) {
        gpio_put(pins_.gnss_enable, true);
        sleep_us(kGnssPowerRailSettleUs);
        uart_init(kGnssUart, baud_);
        gpio_set_function(pins_.gnss_uart_tx, GPIO_FUNC_UART);
        gpio_set_function(pins_.gnss_uart_rx, GPIO_FUNC_UART);
        uart_set_format(kGnssUart, 8, 1, UART_PARITY_NONE);
        uart_set_fifo_enabled(kGnssUart, true);
    } else {
        uart_deinit(kGnssUart);
        for (const auto pin : {pins_.gnss_uart_tx, pins_.gnss_uart_rx}) {
            gpio_init(pin);
            gpio_set_dir(pin, GPIO_IN);
            gpio_disable_pulls(pin);
        }
        gpio_put(pins_.gnss_enable, false);
        framer_.reset();
        accumulator_.clear();
    }
}

PollResult UartGnss::poll() {
    if (!enabled_) {
        return {};
    }
    PollResult result;
    while (uart_is_readable(kGnssUart)) {
        const char byte = static_cast<char>(uart_getc(kGnssUart));
        if (const auto frame = framer_.push(byte)) {
            if (frame->kind == locator::NmeaFrameKind::Complete) {
                const auto parsed = locator::parse_nmea_sentence(frame->payload);
                if (parsed.valid()) {
                    const auto current = accumulator_.ingest(*parsed.sentence);
                    if (current.fix) {
                        result.fix = current.fix;
                        result.invalid_after_fix = false;
                    }
                    if (current.invalid_fix) {
                        result.invalid_fix = true;
                        result.invalid_after_fix = result.fix.has_value();
                    }
                }
            }
        }
    }
    return result;
}

}  // namespace pocket_locator::gnss
