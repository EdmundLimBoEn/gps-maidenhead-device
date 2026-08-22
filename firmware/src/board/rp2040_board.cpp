// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/board/battery.hpp"

#include <algorithm>

#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"

namespace pocket_locator::board {

BatteryAdc::BatteryAdc(PinMap pins, std::uint32_t divider_numerator, std::uint32_t divider_denominator)
    : pins_(pins), divider_numerator_(divider_numerator), divider_denominator_(divider_denominator) {}

void BatteryAdc::init() {
    adc_init();
    adc_gpio_init(pins_.battery_adc);
    adc_set_temp_sensor_enabled(true);
    gpio_init(pins_.battery_sense_enable);
    gpio_set_dir(pins_.battery_sense_enable, GPIO_OUT);
    gpio_put(pins_.battery_sense_enable, false);
    adc_select_input(static_cast<unsigned>(pins_.battery_adc - 26U));
}

void BatteryAdc::begin_read() const {
    gpio_put(pins_.battery_sense_enable, true);
}

BatteryReading BatteryAdc::finish_read() const {
    adc_select_input(static_cast<unsigned>(pins_.battery_adc - 26U));
    const std::uint16_t raw = adc_read();
    const std::uint32_t pin_mv = (static_cast<std::uint32_t>(raw) * 3300U) / 4095U;
    const std::uint32_t mv = (pin_mv * divider_numerator_) / divider_denominator_;
    // Conservative LiPo open-circuit mapping. It is a user-facing estimate,
    // not a fuel gauge; raw ADC is also exposed in diagnostics.
    const std::uint32_t percent = mv <= 3300U ? 0U : (mv >= 4200U ? 100U : ((mv - 3300U) * 100U) / 900U);
    adc_select_input(4);
    const std::uint32_t temperature_mv = (static_cast<std::uint32_t>(adc_read()) * 3300U) / 4095U;
    gpio_put(pins_.battery_sense_enable, false);
    const std::int32_t temperature_centi = 2700 - (static_cast<std::int32_t>(temperature_mv) - 706) * 100000 / 1721;
    return {raw,
            static_cast<std::uint16_t>(std::min<std::uint32_t>(mv, UINT16_MAX)),
            static_cast<std::uint8_t>(percent),
            static_cast<std::int16_t>(std::clamp<std::int32_t>(temperature_centi, -4000, 12500))};
}

BatteryReading BatteryAdc::read() const {
    begin_read();
    sleep_us(kBatteryDividerSettleUs);
    return finish_read();
}

}  // namespace pocket_locator::board
