"""Persisted tuning for how the eye contour sits on the physical panel.

The mechanical frame around the LCD hides an unpredictable amount of the glass,
so the drawing has to be stretched and nudged once the head is assembled. Four
numbers cover it: a horizontal and a vertical scale, multiplied onto the
fit-to-screen factor the page computes, and a pixel offset in each axis.

Everything here is deliberately forgiving. The sliders write on every drag and
the Pi can lose power mid-party, so a missing, partial or corrupt file falls
back to a sane default rather than taking the eyes down.
"""
import json
import math
import os
import tempfile
from pathlib import Path

DEFAULTS = {"scale_x": 1.0, "scale_y": 1.0, "offset_x": 0.0, "offset_y": 0.0}

# (min, max) per field. Scale is a multiplier on the fit; offset is in panel
# pixels, generous enough to push the eyes off a 800x480 screen entirely if the
# frame demands it.
LIMITS = {
    "scale_x": (0.4, 2.5),
    "scale_y": (0.4, 2.5),
    "offset_x": (-400.0, 400.0),
    "offset_y": (-400.0, 400.0),
}

DEFAULT_PATH = Path(__file__).resolve().parent / "eyes_calibration.json"


def _clamp(name, value):
    lo, hi = LIMITS[name]
    try:
        # bool is an int subclass and would silently become 0/1; reject it.
        if isinstance(value, bool):
            raise TypeError
        number = float(value)
    except (TypeError, ValueError):
        return DEFAULTS[name]
    if not math.isfinite(number):
        return DEFAULTS[name]
    return min(hi, max(lo, number))


def sanitize(value) -> dict:
    """Coerce anything at all into a complete, in-range calibration dict."""
    if not isinstance(value, dict):
        value = {}
    return {name: _clamp(name, value.get(name, default))
            for name, default in DEFAULTS.items()}


def load(path=DEFAULT_PATH) -> dict:
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return dict(DEFAULTS)
    return sanitize(raw)


def save(path, value) -> dict:
    """Write atomically and return what was actually stored."""
    path = Path(path)
    clean = sanitize(value)
    # Same directory as the target so the replace stays on one filesystem.
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(clean, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    return clean
