import pytest

from command_center.commands import BUTTONS, button, eye_buttons
from eyes.animations import is_animation

VALID_TRANSPORTS = {"eyes", "mqtt"}


def test_every_button_has_an_id_label_and_known_transport():
    for b in BUTTONS:
        assert b["id"] and b["label"]
        assert b["transport"] in VALID_TRANSPORTS


def test_button_ids_are_unique():
    ids = [b["id"] for b in BUTTONS]
    assert len(ids) == len(set(ids))


def test_eye_buttons_name_real_animations():
    for b in eye_buttons():
        assert is_animation(b["animation"])


def test_the_three_requested_animations_all_have_a_button():
    named = {b["animation"] for b in eye_buttons()}
    assert {"blink", "look_left", "look_right"} <= named


def test_mqtt_buttons_carry_a_topic_and_payload():
    for b in BUTTONS:
        if b["transport"] == "mqtt":
            assert b["topic"] and b["payload"]


def test_button_resolves_by_id():
    assert button("eyes_blink")["animation"] == "blink"


def test_unknown_button_raises():
    with pytest.raises(KeyError):
        button("does_not_exist")
