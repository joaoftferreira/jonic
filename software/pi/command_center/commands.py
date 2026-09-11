"""The buttons the phone shows, and where each one's message goes.

Two transports live side by side. `eyes` buttons are broadcast over the
WebSocket to the kiosk page on this same Pi, which owns the animation. `mqtt`
buttons are published to the broker for the ESP32 to pick up; the robot and
its lights will land there, so the field is already in place.
"""
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
