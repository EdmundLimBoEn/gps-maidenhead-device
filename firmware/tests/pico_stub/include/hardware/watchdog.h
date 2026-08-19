// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
inline void watchdog_enable(std::uint32_t, bool) {}
inline void watchdog_update() {}
inline void watchdog_reboot(std::uint32_t, std::uint32_t, std::uint32_t) {}
