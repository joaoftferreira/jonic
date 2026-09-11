"""Single source of truth for MQTT topics and payloads.

MQTT carries messages to the ESP32 only. The eyes live on the Pi itself and are
driven over the WebSocket in command_center/app.py instead, because the browser
speaks that natively and the display is on the same machine as the server.

The ESP32 side (dual-wheel robot plus on/off lights) is not built yet. Its
topics belong here when it is; keep payloads as trivial strings so the Arduino
parsing stays dead simple.
"""

# ESP32 nodes the command center watches for a heartbeat.
NODES = ("robot",)

HEARTBEAT_SECONDS = 3     # nodes publish this often
HEARTBEAT_TIMEOUT = 10    # command center calls a node down after this long


def heartbeat_topic(node: str) -> str:
    return f"system/heartbeat/{node}"
