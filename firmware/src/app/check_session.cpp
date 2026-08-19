// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/app/check_session.hpp"

#include <utility>

namespace pocket_locator::app {

CheckSession::CheckSession(SessionSettings settings) : settings_(std::move(settings)) {}

bool CheckSession::has_accepted_session() const {
    return state_ == State::Acquiring || state_ == State::DisplayFix || state_ == State::Dimmed ||
           state_ == State::NoGps || state_ == State::FactoryReset;
}

void CheckSession::enter_idle_or_off(Update& update) {
    gnss_active_ = false;
    displayed_grid_.clear();
    clear_tracking_candidate();
    backlight_ = Backlight::Off;
    if (usb_present_) {
        state_ = State::UsbIdle;
        return;
    }
    state_ = State::Off;
    update.power_released = true;
}

void CheckSession::start_acquiring() {
    state_ = State::Acquiring;
    backlight_ = Backlight::Normal;
    gnss_active_ = true;
    clear_tracking_candidate();
}

void CheckSession::release_power(Update& update) {
    enter_idle_or_off(update);
}

void CheckSession::clear_tracking_candidate() {
    candidate_grid_.clear();
    candidate_confirmed_ = false;
}

void CheckSession::commit_tracking_candidate(std::uint64_t now_ms, Update& update) {
    displayed_grid_ = candidate_grid_;
    last_grid_render_ms_ = now_ms;
    clear_tracking_candidate();
    update.display_changed = true;
}

Update CheckSession::set_usb_present(bool present, std::uint64_t now_ms) {
    (void)now_ms;
    usb_present_ = present;
    Update update{};
    if (usb_present_ && state_ == State::Off && !locate_down_) {
        state_ = State::UsbIdle;
        backlight_ = Backlight::Off;
    }
    if (!usb_present_ && (state_ == State::UsbIdle || state_ == State::PressCheck) && !locate_down_) {
        enter_idle_or_off(update);
    }
    return update;
}

Update CheckSession::button_down(Button button, std::uint64_t now_ms) {
    Update update{};
    if (button == Button::Locate) {
        if (locate_down_) {
            return update;
        }
        locate_down_ = true;
        locate_down_at_ms_ = now_ms;
        if (state_ == State::Off || state_ == State::UsbIdle) {
            state_ = State::PressCheck;
            backlight_ = Backlight::Off;
        }
    } else {
        if (off_down_) {
            return update;
        }
        off_down_ = true;
        off_down_at_ms_ = now_ms;
    }

    if (both_down()) {
        both_down_at_ms_ = now_ms;
    }
    return update;
}

Update CheckSession::button_up(Button button, std::uint64_t now_ms) {
    (void)now_ms;
    Update update{};
    if (button == Button::Locate) {
        locate_down_ = false;
        if (state_ == State::PressCheck) {
            enter_idle_or_off(update);
        }
    } else {
        off_down_ = false;
    }
    if (!both_down()) {
        both_down_at_ms_ = 0;
    }
    return update;
}

Update CheckSession::tick(std::uint64_t now_ms) {
    Update update{};

    if (state_ == State::PressCheck && locate_down_ && now_ms >= locate_down_at_ms_ + settings_.hold_ms) {
        start_acquiring();
    }

    if (both_down() && has_accepted_session() && now_ms >= both_down_at_ms_ + settings_.factory_reset_hold_ms) {
        state_ = State::FactoryReset;
        gnss_active_ = false;
        backlight_ = Backlight::Normal;
        if (!reset_emitted_) {
            update.factory_reset_requested = true;
            reset_emitted_ = true;
        }
        return update;
    }

    // A chord is reserved for factory reset.  It must not become an OFF hold.
    if (off_down() && !both_down() && has_accepted_session() &&
        now_ms >= off_down_at_ms_ + settings_.hold_ms) {
        release_power(update);
        return update;
    }

    if (!has_accepted_session()) {
        return update;
    }

    if (state_ == State::NoGps) {
        if (now_ms >= no_gps_until_ms_) {
            release_power(update);
        }
        return update;
    }

    if (state_ == State::FactoryReset) {
        return update;
    }

    const std::uint64_t acquisition_timeout_at = locate_down_at_ms_ + settings_.acquisition_timeout_ms;
    const std::uint64_t dim_at = locate_down_at_ms_ + settings_.dim_deadline_ms;
    const std::uint64_t shutdown_at = locate_down_at_ms_ + settings_.shutdown_deadline_ms;
    if (state_ == State::Acquiring && now_ms >= acquisition_timeout_at) {
        state_ = State::NoGps;
        gnss_active_ = false;
        backlight_ = Backlight::Normal;
        no_gps_until_ms_ = now_ms + settings_.no_gps_message_ms;
        return update;
    }
    if (now_ms >= shutdown_at) {
        release_power(update);
        return update;
    }

    if (now_ms >= dim_at) {
        backlight_ = Backlight::Dim;
        if (state_ == State::DisplayFix) {
            state_ = State::Dimmed;
        }
    }
    if ((state_ == State::DisplayFix || state_ == State::Dimmed) && settings_.gnss_mode == GnssMode::Tracking &&
        gnss_active_ && candidate_confirmed_ &&
        now_ms >= last_grid_render_ms_ + settings_.tracking_render_interval_ms) {
        commit_tracking_candidate(now_ms, update);
    }
    return update;
}

Update CheckSession::valid_fix(std::string_view grid6, std::uint64_t now_ms) {
    Update update = tick(now_ms);
    if (grid6.size() != 6 || (state_ != State::Acquiring && state_ != State::DisplayFix && state_ != State::Dimmed)) {
        return update;
    }

    if (state_ == State::Acquiring) {
        displayed_grid_ = std::string(grid6);
        last_grid_render_ms_ = now_ms;
        state_ = Backlight::Dim == backlight_ ? State::Dimmed : State::DisplayFix;
        update.display_changed = true;
        if (settings_.gnss_mode == GnssMode::SingleFix) {
            gnss_active_ = false;
        }
        return update;
    }

    if (settings_.gnss_mode == GnssMode::SingleFix || !gnss_active_) {
        return update;
    }

    if (grid6 == displayed_grid_) {
        clear_tracking_candidate();
        return update;
    }
    if (grid6 != candidate_grid_) {
        candidate_grid_ = std::string(grid6);
        candidate_confirmed_ = false;
        return update;
    }
    candidate_confirmed_ = true;
    if (now_ms < last_grid_render_ms_ + settings_.tracking_render_interval_ms) {
        return update;
    }
    commit_tracking_candidate(now_ms, update);
    return update;
}

Update CheckSession::invalid_fix(std::uint64_t now_ms) {
    (void)now_ms;
    Update update{};
    if (state_ == State::DisplayFix || state_ == State::Dimmed) {
        clear_tracking_candidate();
    }
    return update;
}

}  // namespace pocket_locator::app
