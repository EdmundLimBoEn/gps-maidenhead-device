// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
constexpr std::uint32_t FLASH_SECTOR_SIZE = 4096;
constexpr std::uint32_t FLASH_PAGE_SIZE = 256;
inline void flash_range_erase(std::uint32_t, std::uint32_t) {}
inline void flash_range_program(std::uint32_t, const std::uint8_t*, std::uint32_t) {}
