// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
namespace pico_stub {
inline std::uint32_t last_sleep_us{};
}
using absolute_time_t = std::uint64_t;
constexpr int PICO_ERROR_TIMEOUT = -1;
inline absolute_time_t get_absolute_time() { return 0; }
inline std::uint64_t to_ms_since_boot(absolute_time_t) { return 0; }
inline void sleep_ms(std::uint32_t) {}
inline void sleep_us(std::uint32_t duration_us) { pico_stub::last_sleep_us = duration_us; }
inline void tight_loop_contents() {}
inline void stdio_init_all() {}
inline int getchar_timeout_us(std::uint32_t) { return PICO_ERROR_TIMEOUT; }
