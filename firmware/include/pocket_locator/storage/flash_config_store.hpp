// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include "pocket_locator/config/config.hpp"

namespace pocket_locator::storage {

// Fixed two-sector records at the end of flash. The linker image must leave
// this reserved range untouched; CMake enforces it for the 2 MiB production
// flash target. The class mirrors TwoSlotStore's inactive-write/verify/mark
// order with real flash operations.
class FlashConfigStore {
public:
    [[nodiscard]] config::LoadResult load() const;
    [[nodiscard]] config::ValidationError write(const config::Settings& settings);
    [[nodiscard]] config::ValidationError factory_reset();
};

}  // namespace pocket_locator::storage
