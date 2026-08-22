// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include "pocket_locator/app/check_session.hpp"

namespace {

using pocket_locator::app::Backlight;
using pocket_locator::app::Button;
using pocket_locator::app::CheckSession;
using pocket_locator::app::GnssMode;
using pocket_locator::app::ResetStorageAction;
using pocket_locator::app::SessionSettings;
using pocket_locator::app::State;

CheckSession accepted_session(SessionSettings settings = {}) {
    CheckSession session(settings);
    session.button_down(Button::Locate, 0);
    session.tick(1'000);
    session.button_up(Button::Locate, 1'001);
    return session;
}

}  // namespace

TEST(short_locate_press_never_latches_power) {
    CheckSession session;
    session.button_down(Button::Locate, 100);
    const auto update = session.button_up(Button::Locate, 1'099);

    REQUIRE_EQ(session.state(), State::Off);
    REQUIRE(update.power_released);
}

TEST(accepted_hold_anchors_deadlines_to_initial_press_edge) {
    CheckSession session = accepted_session();
    REQUIRE_EQ(session.state(), State::Acquiring);

    session.tick(59'999);
    REQUIRE_EQ(session.backlight(), Backlight::Normal);
    session.tick(60'000);
    REQUIRE_EQ(session.backlight(), Backlight::Dim);

    const auto no_gps = session.tick(120'000);
    REQUIRE(!no_gps.power_released);
    REQUIRE_EQ(session.state(), State::NoGps);
    REQUIRE_EQ(session.backlight(), Backlight::Normal);

    const auto shutdown = session.tick(123'000);
    REQUIRE(shutdown.power_released);
    REQUIRE_EQ(session.state(), State::Off);
}

TEST(single_fix_stops_gnss_and_shuts_down_at_original_deadline) {
    CheckSession session = accepted_session();
    const auto first_fix = session.valid_fix("OJ11XH", 10'000);

    REQUIRE(first_fix.display_changed);
    REQUIRE_EQ(session.displayed_grid(), std::string("OJ11XH"));
    REQUIRE(!session.gnss_is_active());
    REQUIRE_EQ(session.state(), State::DisplayFix);

    const auto ignored = session.valid_fix("OJ12XA", 20'000);
    REQUIRE(!ignored.display_changed);
    const auto shutdown = session.tick(120'000);
    REQUIRE(shutdown.power_released);
    REQUIRE_EQ(session.state(), State::Off);
}

TEST(first_valid_fix_pulses_backlight_then_restores_deadline_brightness) {
    CheckSession session = accepted_session();
    session.valid_fix("OJ11XH", 10'000);

    REQUIRE_EQ(session.backlight(), Backlight::Off);
    session.tick(10'119);
    REQUIRE_EQ(session.backlight(), Backlight::Off);
    session.tick(10'120);
    REQUIRE_EQ(session.backlight(), Backlight::Normal);

    CheckSession late_fix = accepted_session();
    late_fix.valid_fix("OJ11XH", 60'000);
    REQUIRE_EQ(late_fix.state(), State::Dimmed);
    REQUIRE_EQ(late_fix.backlight(), Backlight::Off);
    late_fix.tick(60'120);
    REQUIRE_EQ(late_fix.backlight(), Backlight::Dim);
}

TEST(tracking_requires_two_consecutive_new_grids_and_respects_render_interval) {
    SessionSettings settings;
    settings.gnss_mode = GnssMode::Tracking;
    CheckSession session = accepted_session(settings);
    REQUIRE(session.valid_fix("OJ11XH", 2'000).display_changed);

    REQUIRE(!session.valid_fix("OJ12XA", 3'000).display_changed);  // candidate B
    REQUIRE(!session.valid_fix("OJ11XH", 4'000).display_changed);  // A -> B -> A cancels B
    REQUIRE(!session.valid_fix("OJ12XA", 5'000).display_changed);  // candidate B again
    REQUIRE(!session.valid_fix("OJ12XA", 6'999).display_changed);  // two valid B fixes confirm it
    REQUIRE(session.tick(7'000).display_changed);                    // renderer commits at its five-second cap
    REQUIRE_EQ(session.displayed_grid(), std::string("OJ12XA"));
}

TEST(acquisition_timeout_is_independent_of_later_shutdown_deadline) {
    SessionSettings settings;
    settings.acquisition_timeout_ms = 10'000;
    settings.shutdown_deadline_ms = 20'000;
    CheckSession session = accepted_session(settings);

    session.tick(10'000);
    REQUIRE_EQ(session.state(), State::NoGps);
    REQUIRE(!session.tick(12'999).power_released);
    REQUIRE(session.tick(13'000).power_released);
    REQUIRE_EQ(session.state(), State::Off);
}

TEST(fix_received_at_or_after_acquisition_deadline_cannot_beat_timeout) {
    SessionSettings settings;
    settings.acquisition_timeout_ms = 10'000;
    settings.shutdown_deadline_ms = 20'000;
    CheckSession session = accepted_session(settings);

    const auto update = session.valid_fix("OJ11XH", 10'000);
    REQUIRE(!update.display_changed);
    REQUIRE_EQ(session.state(), State::NoGps);
}

TEST(invalid_fix_breaks_tracking_consecutiveness) {
    SessionSettings settings;
    settings.gnss_mode = GnssMode::Tracking;
    CheckSession session = accepted_session(settings);
    session.valid_fix("OJ11XH", 1'000);

    session.valid_fix("OJ12XA", 2'000);
    session.invalid_fix(3'000);
    REQUIRE(!session.valid_fix("OJ12XA", 7'000).display_changed);
    REQUIRE(session.valid_fix("OJ12XA", 8'000).display_changed);
}

TEST(off_requires_a_hold_and_usb_returns_to_dark_idle) {
    CheckSession session = accepted_session();
    session.valid_fix("OJ11XH", 2'000);
    session.set_usb_present(true, 2'500);

    session.button_down(Button::Off, 3'000);
    session.tick(3'999);
    REQUIRE_EQ(session.state(), State::DisplayFix);
    const auto shutdown = session.tick(4'000);
    REQUIRE(!shutdown.power_released);
    REQUIRE_EQ(session.state(), State::UsbIdle);
    REQUIRE_EQ(session.backlight(), Backlight::Off);
}

TEST(usb_boot_enters_dark_idle_without_starting_gnss) {
    CheckSession session;
    const auto update = session.set_usb_present(true, 0);

    REQUIRE(!update.power_released);
    REQUIRE_EQ(session.state(), State::UsbIdle);
    REQUIRE_EQ(session.backlight(), Backlight::Off);
    REQUIRE(!session.gnss_is_active());
}

TEST(two_button_hold_requests_factory_reset_without_triggering_off) {
    CheckSession session = accepted_session();
    session.valid_fix("OJ11XH", 2'000);
    session.button_down(Button::Locate, 3'000);
    session.button_down(Button::Off, 3'000);

    REQUIRE_EQ(session.factory_reset_countdown_seconds(3'000), std::optional<std::uint8_t>{5});
    REQUIRE_EQ(session.factory_reset_countdown_seconds(7'001), std::optional<std::uint8_t>{1});
    session.tick(4'000);
    REQUIRE_EQ(session.state(), State::DisplayFix);
    const auto reset = session.tick(8'000);
    REQUIRE(reset.factory_reset_requested);
    REQUIRE_EQ(session.state(), State::FactoryReset);
    REQUIRE(!session.tick(8'100).factory_reset_requested);
}

TEST(repeated_locate_press_cannot_extend_session_deadlines) {
    CheckSession session = accepted_session();
    session.valid_fix("OJ11XH", 2'000);
    session.button_down(Button::Locate, 50'000);
    session.button_up(Button::Locate, 50'500);

    REQUIRE(session.tick(120'000).power_released);
    REQUIRE_EQ(session.state(), State::Off);
}

TEST(factory_reset_reboots_only_after_verified_storage_success) {
    REQUIRE_EQ(pocket_locator::app::reset_storage_action(true), ResetStorageAction::Reboot);
    REQUIRE_EQ(
        pocket_locator::app::reset_storage_action(false), ResetStorageAction::ShowFailure);
}
