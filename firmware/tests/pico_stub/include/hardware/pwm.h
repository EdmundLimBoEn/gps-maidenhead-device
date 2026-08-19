// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
struct pwm_config {};
inline std::uint8_t pwm_gpio_to_slice_num(std::uint8_t) { return 0; }
inline pwm_config pwm_get_default_config() { return {}; }
inline void pwm_config_set_clkdiv(pwm_config*, float) {}
inline void pwm_config_set_wrap(pwm_config*, std::uint16_t) {}
inline void pwm_init(std::uint8_t, const pwm_config*, bool) {}
inline void pwm_set_gpio_level(std::uint8_t, std::uint16_t) {}
