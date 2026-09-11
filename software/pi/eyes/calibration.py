"""Persisted tuning for how the eye contour sits on the physical panel.

The mechanical frame around the LCD hides an unpredictable amount of the glass,
so the drawing has to be stretched and nudged once the head is assembled. Four
numbers cover it: a horizontal and a vertical scale, multiplied onto the
fit-to-screen factor the page computes, and a pixel offset in each axis.

The reading and writing live in common/jsonstore.py, shared with the robot's
motor speed.
"""
from pathlib import Path

from common import jsonstore

DEFAULTS = {"scale_x": 1.0, "scale_y": 1.0, "offset_x": 0.0, "offset_y": 0.0}

# (min, max) per field. Scale is a multiplier on the fit; offset is in panel
# pixels, generous enough to push the eyes off a 1024x600 screen entirely if
# the frame demands it.
LIMITS = {
    "scale_x": (0.4, 2.5),
    "scale_y": (0.4, 2.5),
    "offset_x": (-400.0, 400.0),
    "offset_y": (-400.0, 400.0),
}

DEFAULT_PATH = Path(__file__).resolve().parent / "eyes_calibration.json"


def sanitize(value) -> dict:
    return jsonstore.sanitize(value, DEFAULTS, LIMITS)


def load(path=DEFAULT_PATH) -> dict:
    return jsonstore.load(path, DEFAULTS, LIMITS)


def save(path, value) -> dict:
    return jsonstore.save(path, value, DEFAULTS, LIMITS)
