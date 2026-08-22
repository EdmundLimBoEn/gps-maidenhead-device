// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
struct uart_inst_t {};
inline uart_inst_t* uart0 = nullptr;
constexpr int UART_PARITY_NONE = 0;
inline unsigned uart_init(uart_inst_t*, std::uint32_t) { return 0; }
inline void uart_deinit(uart_inst_t*) {}
inline void uart_set_format(uart_inst_t*, unsigned, unsigned, int) {}
inline void uart_set_fifo_enabled(uart_inst_t*, bool) {}
inline bool uart_is_readable(uart_inst_t*) { return false; }
inline std::uint8_t uart_getc(uart_inst_t*) { return 0; }
