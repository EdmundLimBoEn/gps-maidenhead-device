// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include "pocket_locator/board/battery.hpp"
#include "pocket_locator/config/config.hpp"

namespace {

using pocket_locator::config::Settings;
using pocket_locator::config::TwoSlotStore;
using pocket_locator::config::ValidationError;
using pocket_locator::config::WriteInterruption;

}  // namespace

TEST(battery_divider_waits_at_least_five_rc_time_constants) {
    using namespace pocket_locator::board;

    REQUIRE_EQ(kBatteryDividerTimeConstantUs, 5'000U);
    REQUIRE(kBatteryDividerSettleUs >= 5U * kBatteryDividerTimeConstantUs);
}

TEST(factory_settings_are_valid_and_stable) {
    const Settings defaults = pocket_locator::config::factory_defaults();
    REQUIRE_EQ(pocket_locator::config::validate(defaults), ValidationError::None);
    REQUIRE_EQ(defaults.named_time_zone, std::string("Asia/Singapore"));
    REQUIRE_EQ(defaults.acquisition_timeout_ms, 120'000U);
    REQUIRE_EQ(defaults.dim_deadline_ms, 60'000U);
    REQUIRE_EQ(defaults.shutdown_deadline_ms, 120'000U);
}

TEST(config_validation_rejects_unsafe_or_unsupported_values) {
    Settings settings = pocket_locator::config::factory_defaults();
    settings.shutdown_deadline_ms = settings.dim_deadline_ms - 1U;
    REQUIRE_EQ(pocket_locator::config::validate(settings), ValidationError::InvalidDeadlineOrder);

    settings = pocket_locator::config::factory_defaults();
    settings.dim_brightness = 101;
    REQUIRE_EQ(pocket_locator::config::validate(settings), ValidationError::InvalidBrightness);

    settings = pocket_locator::config::factory_defaults();
    settings.acquisition_timeout_ms = settings.shutdown_deadline_ms + 1U;
    REQUIRE_EQ(pocket_locator::config::validate(settings), ValidationError::InvalidDeadlineOrder);

    settings = pocket_locator::config::factory_defaults();
    settings.named_time_zone = "Asia\nSingapore";
    REQUIRE_EQ(pocket_locator::config::validate(settings), ValidationError::InvalidTimeZone);

    settings = pocket_locator::config::factory_defaults();
    settings.schema_version = 99;
    REQUIRE_EQ(pocket_locator::config::validate(settings), ValidationError::UnsupportedSchema);
}

TEST(two_slot_store_loads_newest_valid_record) {
    TwoSlotStore store;
    Settings first = pocket_locator::config::factory_defaults();
    first.named_time_zone = "Europe/London";
    first.zone_table.zone_name = first.named_time_zone;
    REQUIRE_EQ(store.write(first), ValidationError::None);

    Settings second = first;
    second.named_time_zone = "America/New_York";
    second.zone_table.zone_name = second.named_time_zone;
    REQUIRE_EQ(store.write(second), ValidationError::None);

    const auto loaded = store.load();
    REQUIRE(!loaded.used_factory_defaults);
    REQUIRE(loaded.crc_healthy);
    REQUIRE_EQ(loaded.settings.named_time_zone, std::string("America/New_York"));
    REQUIRE_EQ(loaded.selected_slot, 1);
}

TEST(power_loss_before_marker_keeps_prior_valid_configuration) {
    TwoSlotStore store;
    Settings committed = pocket_locator::config::factory_defaults();
    committed.named_time_zone = "Europe/London";
    committed.zone_table.zone_name = committed.named_time_zone;
    REQUIRE_EQ(store.write(committed), ValidationError::None);

    Settings replacement = committed;
    replacement.named_time_zone = "America/New_York";
    replacement.zone_table.zone_name = replacement.named_time_zone;
    for (const auto interruption : {WriteInterruption::BeforePayload, WriteInterruption::AfterPayload,
                                    WriteInterruption::AfterVerification}) {
        TwoSlotStore trial = store;
        REQUIRE_EQ(trial.write(replacement, interruption), ValidationError::None);
        const auto loaded = trial.load();
        REQUIRE(!loaded.used_factory_defaults);
        REQUIRE_EQ(loaded.settings.named_time_zone, std::string("Europe/London"));
    }
}

TEST(corrupt_newest_slot_falls_back_to_older_valid_record) {
    TwoSlotStore store;
    Settings old = pocket_locator::config::factory_defaults();
    old.named_time_zone = "Europe/London";
    old.zone_table.zone_name = old.named_time_zone;
    REQUIRE_EQ(store.write(old), ValidationError::None);
    Settings newest = old;
    newest.named_time_zone = "Pacific/Chatham";
    newest.zone_table.zone_name = newest.named_time_zone;
    REQUIRE_EQ(store.write(newest), ValidationError::None);

    store.corrupt_crc_for_test(1);
    const auto loaded = store.load();
    REQUIRE(!loaded.used_factory_defaults);
    REQUIRE_EQ(loaded.settings.named_time_zone, std::string("Europe/London"));
    REQUIRE_EQ(loaded.selected_slot, 0);
}

TEST(two_corrupt_slots_boot_safe_factory_defaults) {
    TwoSlotStore store;
    REQUIRE_EQ(store.write(pocket_locator::config::factory_defaults()), ValidationError::None);
    store.corrupt_crc_for_test(0);

    const auto loaded = store.load();
    REQUIRE(loaded.used_factory_defaults);
    REQUIRE(!loaded.crc_healthy);
    REQUIRE_EQ(loaded.settings.named_time_zone, std::string("Asia/Singapore"));
}
