"""What the eyes can do, and the numbers that define it.

This is the contract between the phone (which names an animation), the server
(which validates the name and broadcasts it) and the kiosk page (which plays
it). Keep it small: the page owns all timing, the server owns none.
"""
from eyes import emeralds, scene

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

# Fast enough to read as a blink rather than a doze, but not so fast that a
# slow panel cannot draw it. 300 ms was too quick on the Pi 3: the eyes often
# appeared to shut only halfway.
BLINK_MS = 500

# The lid holds shut between these two fractions of the blink. Without a hold
# it is fully closed at a single instant, and a renderer that is dropping
# frames simply never paints that instant -- so the lid visibly turns back
# partway down and the blink never completes. The plateau guarantees at least
# one painted frame with the eyes actually shut.
#
# Measured on the Pi 3: it paints only about 8 frames across the whole blink,
# roughly 60 ms apart, so the plateau needs to be worth three of them.
BLINK_CLOSED_FROM = 0.30     # shut by 150 ms
BLINK_CLOSED_TO = 0.70       # held shut for 200 ms, then 150 ms to open

GAZE_MS = 180

ANIMATIONS = {
    # The lid drops over the whole contour and lifts again, half the time each way.
    "blink": {"kind": "blink", "duration_ms": BLINK_MS},
    # Gaze latches: the eyes hold the look until told otherwise. "left" and
    # "right" are the operator's left and right as they face the screen.
    "look_left": {"kind": "gaze", "duration_ms": GAZE_MS, "gaze": -1},
    "look_right": {"kind": "gaze", "duration_ms": GAZE_MS, "gaze": 1},
    "center": {"kind": "gaze", "duration_ms": GAZE_MS, "gaze": 0},
    # The Chaos Emeralds fill both eyes and then turn forever. Like gaze it
    # latches; any other animation clears it and brings the irises back.
    "emeralds": {"kind": "emeralds", "duration_ms": emeralds.settle_ms()},
    # A few seconds of cartoon telling the children what to do. Unlike the
    # others this one ends by itself and leaves the eyes as it found them.
    "shoot_eggman": {"kind": "scene", "duration_ms": scene.total_ms()},
}


def is_animation(name) -> bool:
    return isinstance(name, str) and name in ANIMATIONS
