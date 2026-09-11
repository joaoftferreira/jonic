"""What the eyes can do, and the numbers that define it.

This is the contract between the phone (which names an animation), the server
(which validates the name and broadcasts it) and the kiosk page (which plays
it). Keep it small: the page owns all timing, the server owns none.
"""

# Sonic's fur blue. The eyelid is the only coloured thing on screen.
LID_COLOR = "#1F4FD8"

# How far an iris slides sideways at full gaze, in SVG user units, for the eye
# moving AWAY from the notch between the two eyes.
GAZE_TRAVEL = 15.0

# The other eye's iris moves toward that notch, where there is far less room:
# both irises rest close to it, so an equal shift buries the inner one and its
# shine disappears entirely. Cheating the inner eye's travel keeps it readable
# while the outer one still swings far enough to see across a room.
# test_animations measures both against the real outline.
GAZE_INNER_RATIO = 0.3

# Fast, so it reads as a blink and not a doze.
BLINK_MS = 300
GAZE_MS = 180

ANIMATIONS = {
    # The lid drops over the whole contour and lifts again, half the time each way.
    "blink": {"kind": "blink", "duration_ms": BLINK_MS},
    # Gaze latches: the eyes hold the look until told otherwise. "left" and
    # "right" are the operator's left and right as they face the screen.
    "look_left": {"kind": "gaze", "duration_ms": GAZE_MS, "gaze": -1},
    "look_right": {"kind": "gaze", "duration_ms": GAZE_MS, "gaze": 1},
    "center": {"kind": "gaze", "duration_ms": GAZE_MS, "gaze": 0},
}


def is_animation(name) -> bool:
    return isinstance(name, str) and name in ANIMATIONS
