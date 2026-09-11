"""Tuned settings for Eggman's robot. Currently just how hard it drives.

Carpet and hard floor need very different power, and which one the party
happens on is not knowable until the robot is built, so the speed is a slider
on the phone rather than a constant in the firmware.
"""
from pathlib import Path

from common import jsonstore

DEFAULTS = {"speed": 65.0}          # percent of full motor power

#: Below about 25% a geared robot usually will not overcome its own friction,
#: so the slider does not offer settings that just make it buzz.
LIMITS = {"speed": (25.0, 100.0)}

DEFAULT_PATH = Path(__file__).resolve().parent / "robot_settings.json"


def sanitize(value) -> dict:
    return jsonstore.sanitize(value, DEFAULTS, LIMITS)


def load(path=DEFAULT_PATH) -> dict:
    return jsonstore.load(path, DEFAULTS, LIMITS)


def save(path, value) -> dict:
    return jsonstore.save(path, value, DEFAULTS, LIMITS)
