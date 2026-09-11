"""The buttons the phone shows, and where each one's message goes.

Two transports live side by side. `eyes` buttons are broadcast over the
WebSocket to the kiosk page on this same Pi, which owns the animation. `mqtt`
buttons are published to the broker for the ESP32 to pick up; the robot and
its lights will land there, so the field is already in place.
"""
from common import mqtt_contract as c
from eyes.animations import ANIMATIONS

BUTTONS = [
    {"id": "eyes_look_left", "label": "👈 Look left",
     "transport": "eyes", "animation": "look_left", "group": "eyes"},
    {"id": "eyes_blink", "label": "😉 Blink",
     "transport": "eyes", "animation": "blink", "group": "eyes"},
    {"id": "eyes_look_right", "label": "Look right 👉",
     "transport": "eyes", "animation": "look_right", "group": "eyes"},
    {"id": "eyes_center", "label": "👀 Look ahead",
     "transport": "eyes", "animation": "center", "group": "eyes"},
    {"id": "eyes_emeralds", "label": "💎 Emeralds",
     "transport": "eyes", "animation": "emeralds", "group": "eyes"},

    # Driving. `hold` tells the phone to repeat the press while your finger is
    # down; releasing sends robot_stop. None of these are retained, because a
    # retained drive would be replayed the moment the ESP32 reconnects and the
    # robot would set off with nobody touching the phone.
    {"id": "robot_forward", "label": "▲", "transport": "mqtt",
     "topic": c.ROBOT_DRIVE, "payload": "forward", "group": "drive", "hold": True},
    {"id": "robot_left", "label": "◀", "transport": "mqtt",
     "topic": c.ROBOT_DRIVE, "payload": "left", "group": "drive", "hold": True},
    {"id": "robot_stop", "label": "■", "transport": "mqtt",
     "topic": c.ROBOT_DRIVE, "payload": "stop", "group": "drive"},
    {"id": "robot_right", "label": "▶", "transport": "mqtt",
     "topic": c.ROBOT_DRIVE, "payload": "right", "group": "drive", "hold": True},
    {"id": "robot_back", "label": "▼", "transport": "mqtt",
     "topic": c.ROBOT_DRIVE, "payload": "back", "group": "drive", "hold": True},

    # Ring and lock. Retained: a robot that reboots mid-party comes back with
    # its lights as you left them and does not silently re-lock a chest the
    # children have already opened.
    {"id": "lights_on", "label": "💡 Lights on", "transport": "mqtt",
     "topic": c.ROBOT_LIGHTS, "payload": "on", "retain": True, "group": "robot"},
    {"id": "lights_off", "label": "🌑 Lights off", "transport": "mqtt",
     "topic": c.ROBOT_LIGHTS, "payload": "off", "retain": True, "group": "robot"},
    {"id": "lock_open", "label": "🔓 OPEN", "transport": "mqtt",
     "topic": c.ROBOT_LOCK, "payload": "open", "retain": True, "group": "robot"},
    {"id": "lock_reset", "label": "🔒 Re-arm lock", "transport": "mqtt",
     "topic": c.ROBOT_LOCK, "payload": "reset", "retain": True, "group": "robot"},
]

_BY_ID = {b["id"]: b for b in BUTTONS}

# Catch a typo in the table above at import time rather than on a button press
# in the middle of the party.
for _b in BUTTONS:
    if _b["transport"] == "eyes" and _b["animation"] not in ANIMATIONS:
        raise ValueError(f"button {_b['id']} names unknown animation {_b['animation']}")


def button(button_id: str) -> dict:
    """The button's definition. Raises KeyError if the id is unknown."""
    return _BY_ID[button_id]


def eye_buttons():
    return [b for b in BUTTONS if b["transport"] == "eyes"]


def grouped():
    """Buttons in declaration order, bundled by their `group` for layout."""
    out = []
    for b in BUTTONS:
        if not out or out[-1][0] != b["group"]:
            out.append((b["group"], []))
        out[-1][1].append(b)
    return out
