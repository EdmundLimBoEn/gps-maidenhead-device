// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace pocket_locator::app {

enum class State {
    Off,
    PressCheck,
    UsbIdle,
    Acquiring,
    DisplayFix,
    Dimmed,
    NoGps,
    FactoryReset,
};

enum class Button { Locate, Off };
enum class GnssMode { SingleFix, Tracking };
enum class Backlight { Off, Normal, Dim };
enum class ResetStorageAction { Reboot, ShowFailure };

[[nodiscard]] constexpr ResetStorageAction reset_storage_action(bool verified) {
    return verified ? ResetStorageAction::Reboot : ResetStorageAction::ShowFailure;
}

struct SessionSettings {
    GnssMode gnss_mode{GnssMode::SingleFix};
    std::uint64_t hold_ms{1'000};
    std::uint64_t factory_reset_hold_ms{5'000};
    std::uint64_t acquisition_timeout_ms{120'000};
    std::uint64_t dim_deadline_ms{60'000};
    std::uint64_t shutdown_deadline_ms{120'000};
    std::uint64_t no_gps_message_ms{3'000};
    std::uint64_t success_flash_ms{120};
    std::uint64_t tracking_render_interval_ms{5'000};
};

struct Update {
    bool display_changed{false};
    bool power_released{false};
    bool factory_reset_requested{false};
};

// Deterministic, hardware-agnostic check-session behavior.  The board layer
// translates its outputs to GPIO, LCD, and PWM operations.
class CheckSession {
public:
    explicit CheckSession(SessionSettings settings = {});

    [[nodiscard]] State state() const { return state_; }
    [[nodiscard]] Backlight backlight() const { return backlight_; }
    [[nodiscard]] const std::string& displayed_grid() const { return displayed_grid_; }
    [[nodiscard]] bool gnss_is_active() const { return gnss_active_; }
    [[nodiscard]] std::optional<std::uint8_t> factory_reset_countdown_seconds(
        std::uint64_t now_ms) const;

    Update set_usb_present(bool present, std::uint64_t now_ms);
    Update button_down(Button button, std::uint64_t now_ms);
    Update button_up(Button button, std::uint64_t now_ms);
    Update tick(std::uint64_t now_ms);
    Update valid_fix(std::string_view grid6, std::uint64_t now_ms);
    Update invalid_fix(std::uint64_t now_ms);

private:
    [[nodiscard]] bool locate_down() const { return locate_down_; }
    [[nodiscard]] bool off_down() const { return off_down_; }
    [[nodiscard]] bool both_down() const { return locate_down_ && off_down_; }
    void enter_idle_or_off(Update& update);
    void start_acquiring();
    void release_power(Update& update);
    void clear_tracking_candidate();
    void commit_tracking_candidate(std::uint64_t now_ms, Update& update);
    [[nodiscard]] bool has_accepted_session() const;

    SessionSettings settings_;
    State state_{State::Off};
    Backlight backlight_{Backlight::Off};
    bool usb_present_{false};
    bool locate_down_{false};
    bool off_down_{false};
    bool gnss_active_{false};
    std::uint64_t locate_down_at_ms_{0};
    std::uint64_t session_epoch_ms_{0};
    std::uint64_t off_down_at_ms_{0};
    std::uint64_t both_down_at_ms_{0};
    std::uint64_t no_gps_until_ms_{0};
    std::uint64_t success_flash_until_ms_{0};
    bool success_flash_active_{false};
    std::uint64_t last_grid_render_ms_{0};
    bool reset_emitted_{false};
    std::string displayed_grid_;
    std::string candidate_grid_;
    bool candidate_confirmed_{false};
};

}  // namespace pocket_locator::app
