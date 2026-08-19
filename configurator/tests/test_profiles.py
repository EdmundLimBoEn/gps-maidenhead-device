# SPDX-License-Identifier: GPL-3.0-or-later
import json

import pytest

from maidenhead_configurator.models import factory_config
from maidenhead_configurator.profiles import Profile, load_profile, profile_diff, save_profile


def test_profile_round_trip(tmp_path) -> None:
    path = tmp_path / "portable.json"
    original = Profile(factory_config(), notes="Field kit")
    save_profile(original, path)
    loaded = load_profile(path)
    assert loaded.to_dict() == original.to_dict()
    serialized = path.read_text()
    assert "coordinates" not in serialized
    assert "timezone_table" not in serialized


def test_unknown_profile_version_is_not_silently_migrated(tmp_path) -> None:
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"profile_schema_version": 2, "config": {}}))
    with pytest.raises(ValueError, match="unsupported profile"):
        load_profile(path)


def test_diff_only_contains_changed_values() -> None:
    before = factory_config()
    after = factory_config()
    after.gnss_mode = "tracking"
    assert profile_diff(before, after) == {"gnss_mode": ("single_fix", "tracking")}
