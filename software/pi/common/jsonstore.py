"""A tiny store for a handful of tuned numbers, written atomically.

Both the eye calibration and the robot's motor speed are the same shape: a few
named numbers, adjusted from the phone, that must survive a reboot. They are
also both written on demand while the Pi is running on a supply that gets
pulled rather than shut down, so every write is atomic and every read is
forgiving: a missing, partial or corrupt file falls back to sane defaults
rather than taking the party's hardware down.
"""
import json
import math
import os
import tempfile
from pathlib import Path


def clamp(name, value, defaults, limits):
    lo, hi = limits[name]
    try:
        # bool is an int subclass and would silently become 0/1; reject it.
        if isinstance(value, bool):
            raise TypeError
        number = float(value)
    except (TypeError, ValueError):
        return defaults[name]
    if not math.isfinite(number):
        return defaults[name]
    return min(hi, max(lo, number))


def sanitize(value, defaults, limits) -> dict:
    """Coerce anything at all into a complete, in-range dict."""
    if not isinstance(value, dict):
        value = {}
    return {name: clamp(name, value.get(name, default), defaults, limits)
            for name, default in defaults.items()}


def load(path, defaults, limits) -> dict:
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return dict(defaults)
    return sanitize(raw, defaults, limits)


def save(path, value, defaults, limits) -> dict:
    """Write atomically and return what was actually stored."""
    path = Path(path)
    clean = sanitize(value, defaults, limits)
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
