import json

import pytest

from robot import settings


def test_default_speed_is_usable_and_in_range():
    lo, hi = settings.LIMITS["speed"]
    assert lo <= settings.DEFAULTS["speed"] <= hi


def test_the_slider_cannot_ask_for_a_speed_that_only_buzzes():
    assert settings.LIMITS["speed"][0] >= 25


def test_out_of_range_is_clamped_not_rejected():
    assert settings.sanitize({"speed": 500})["speed"] == settings.LIMITS["speed"][1]
    assert settings.sanitize({"speed": -10})["speed"] == settings.LIMITS["speed"][0]


@pytest.mark.parametrize("junk", ["fast", None, [], {}, True, float("nan")])
def test_nonsense_falls_back_to_the_default(junk):
    assert settings.sanitize({"speed": junk})["speed"] == settings.DEFAULTS["speed"]


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "robot_settings.json"
    settings.save(path, {"speed": 80})
    assert settings.load(path) == {"speed": 80.0}


def test_a_missing_file_gives_the_default(tmp_path):
    assert settings.load(tmp_path / "nope.json") == settings.DEFAULTS


def test_a_corrupt_file_does_not_stop_the_robot_coming_up(tmp_path):
    path = tmp_path / "robot_settings.json"
    path.write_text("{ truncated")
    assert settings.load(path) == settings.DEFAULTS


def test_save_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "robot_settings.json"
    settings.save(path, {"speed": 70})
    assert list(tmp_path.iterdir()) == [path]
    assert json.loads(path.read_text())["speed"] == 70
