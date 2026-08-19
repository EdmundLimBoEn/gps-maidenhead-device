// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
inline void adc_init() {}
inline void adc_gpio_init(std::uint8_t) {}
inline void adc_select_input(unsigned) {}
inline void adc_set_temp_sensor_enabled(bool) {}
inline std::uint16_t adc_read() { return 0; }
