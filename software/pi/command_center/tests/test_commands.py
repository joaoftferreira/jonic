import pytest

from command_center.commands import BUTTONS, button, eye_buttons, grouped
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


# --- the robot -------------------------------------------------------------

def test_no_drive_command_is_ever_retained():
    """A retained drive would be replayed the moment the ESP32 reconnects and
    the robot would set off with nobody holding a button."""
    for b in BUTTONS:
        if b.get("topic") == "robot/drive":
            assert b.get("retain", False) is False, b["id"]


def test_lights_and_lock_are_retained_so_a_reboot_restores_them():
    for b in BUTTONS:
        if b.get("topic") in ("robot/lights", "robot/lock"):
            assert b.get("retain") is True, b["id"]


def test_the_four_directions_are_held_and_stop_is_not():
    held = {b["payload"] for b in BUTTONS if b.get("hold")}
    assert held == {"forward", "back", "left", "right"}
    assert button("robot_stop").get("hold") is None


def test_every_drive_payload_is_in_the_contract():
    from common import mqtt_contract as c
    for b in BUTTONS:
        if b.get("topic") == c.ROBOT_DRIVE:
            assert b["payload"] in c.DRIVE_COMMANDS


def test_groups_keep_declaration_order_and_cover_every_button():
    seen = [b for _, bs in grouped() for b in bs]
    assert seen == BUTTONS
