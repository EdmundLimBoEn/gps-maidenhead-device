// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
constexpr bool GPIO_IN = false;
constexpr bool GPIO_OUT = true;
constexpr unsigned GPIO_FUNC_UART = 2;
constexpr unsigned GPIO_FUNC_PWM = 4;
inline void gpio_init(std::uint8_t) {}
inline void gpio_set_dir(std::uint8_t, bool) {}
inline void gpio_pull_up(std::uint8_t) {}
inline void gpio_disable_pulls(std::uint8_t) {}
inline bool gpio_get(std::uint8_t) { return false; }
inline void gpio_put(std::uint8_t, bool) {}
inline void gpio_set_function(std::uint8_t, unsigned) {}
