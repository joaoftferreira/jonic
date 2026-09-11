"""Single source of truth for MQTT topics and payloads.

MQTT carries messages to the ESP32 only. The eyes live on the Pi itself and are
driven over the WebSocket in command_center/app.py instead, because the browser
speaks that natively and the display is on the same machine as the server.

Payloads are deliberately trivial strings so the Arduino parsing stays simple.
"""

# ESP32 nodes the command center watches for a heartbeat.
NODES = ("robot",)

HEARTBEAT_SECONDS = 3     # nodes publish this often
HEARTBEAT_TIMEOUT = 10    # command center calls a node down after this long

# --- Eggman's robot --------------------------------------------------------

#: Which way to drive. Sent repeatedly while a button is held, and NEVER
#: retained: a retained drive would be replayed the instant the ESP32
#: reconnects, and the robot would set off on its own with nobody holding a
#: button. The firmware also stops itself if this goes quiet, see DRIVE_TIMEOUT.
ROBOT_DRIVE = "robot/drive"
DRIVE_COMMANDS = ("forward", "back", "left", "right", "stop")

#: How often the phone repeats the held command, and how long the robot will
#: keep driving without hearing one. The gap between them absorbs a few lost
#: packets without the robot stuttering.
DRIVE_REPEAT_MS = 200
DRIVE_TIMEOUT_MS = 500

#: Motor power, "0".."100". Retained, so a robot that reboots mid-party comes
#: back at the speed you tuned rather than a default.
ROBOT_SPEED = "robot/speed"

#: The NeoPixel ring: "on" | "off". Retained, same reasoning.
ROBOT_LIGHTS = "robot/lights"

#: The lock servo: "open" drives it to its open position, "reset" returns it to
#: zero so the lock can be re-armed. Retained, so a reboot does not silently
#: re-lock a chest the children have already opened.
ROBOT_LOCK = "robot/lock"
LOCK_COMMANDS = ("open", "reset")


def heartbeat_topic(node: str) -> str:
    return f"system/heartbeat/{node}"
