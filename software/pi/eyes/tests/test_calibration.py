import json

import pytest

from eyes import calibration as cal


def test_defaults_are_a_neutral_identity_fit():
    d = cal.DEFAULTS
    assert d == {"scale_x": 1.0, "scale_y": 1.0, "offset_x": 0.0, "offset_y": 0.0}


def test_sanitize_fills_in_anything_missing():
    assert cal.sanitize({"scale_y": 0.9}) == {
        "scale_x": 1.0, "scale_y": 0.9, "offset_x": 0.0, "offset_y": 0.0}


def test_sanitize_drops_unknown_keys():
    assert "nonsense" not in cal.sanitize({"nonsense": 5})


def test_sanitize_clamps_out_of_range_values():
    out = cal.sanitize({"scale_x": 99, "scale_y": -3, "offset_x": 9999, "offset_y": -9999})
    assert out["scale_x"] == cal.LIMITS["scale_x"][1]
    assert out["scale_y"] == cal.LIMITS["scale_y"][0]
    assert out["offset_x"] == cal.LIMITS["offset_x"][1]
    assert out["offset_y"] == cal.LIMITS["offset_y"][0]


@pytest.mark.parametrize("junk", ["1.0", None, [], {}, float("nan"), float("inf")])
def test_sanitize_replaces_non_numbers_with_the_default(junk):
    assert cal.sanitize({"scale_x": junk})["scale_x"] == 1.0


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "eyes_calibration.json"
    value = {"scale_x": 1.2, "scale_y": 0.85, "offset_x": -12.0, "offset_y": 7.0}
    cal.save(path, value)
    assert cal.load(path) == value


def test_save_clamps_before_writing(tmp_path):
    path = tmp_path / "eyes_calibration.json"
    cal.save(path, {"scale_x": 99})
    assert json.loads(path.read_text())["scale_x"] == cal.LIMITS["scale_x"][1]


def test_load_returns_defaults_when_the_file_is_absent(tmp_path):
    assert cal.load(tmp_path / "nope.json") == cal.DEFAULTS


def test_load_returns_defaults_when_the_file_is_corrupt(tmp_path):
    """A half-written file must not stop the eyes from coming up."""
    path = tmp_path / "eyes_calibration.json"
    path.write_text("{not json")
    assert cal.load(path) == cal.DEFAULTS


def test_load_repairs_a_partial_file(tmp_path):
    path = tmp_path / "eyes_calibration.json"
    path.write_text(json.dumps({"scale_y": 0.8}))
    assert cal.load(path) == {
        "scale_x": 1.0, "scale_y": 0.8, "offset_x": 0.0, "offset_y": 0.0}


def test_save_is_atomic(tmp_path):
    """Saving must never leave a truncated file behind, because the sliders
    write on every drag and the Pi can lose power at any moment."""
    path = tmp_path / "eyes_calibration.json"
    cal.save(path, {"scale_x": 1.1})
    cal.save(path, {"scale_x": 1.3})
    assert json.loads(path.read_text())["scale_x"] == 1.3
    assert list(tmp_path.iterdir()) == [path], "a temp file was left behind"


def test_defaults_are_not_mutated_by_a_caller(tmp_path):
    got = cal.load(tmp_path / "nope.json")
    got["scale_x"] = 42
    assert cal.DEFAULTS["scale_x"] == 1.0
