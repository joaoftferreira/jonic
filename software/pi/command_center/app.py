"""Command center: serves the phone remote and the LCD kiosk page, and routes
every button press to whoever needs it.

    phone  --POST /fire/<id>-->  this app  --WebSocket-->  /eyes page (this Pi)
                                           --MQTT-------->  ESP32 (robot, later)

The MQTT link is optional on purpose. The eyes must come up even when the
broker is down or no ESP32 exists yet, so the connection is made in the
background and never blocks or fails a request.
"""
import json
import threading
import time

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template, request
from flask_sock import Sock

from command_center.commands import BUTTONS, button
from command_center.hub import WebSocketHub
from common import mqtt_contract as c
from eyes import animations, calibration
from eyes import geometry

BROKER = "127.0.0.1"      # the broker runs on this same Pi

app = Flask(__name__)
# Ping the kiosk browser so a silently dropped Wi-Fi link is noticed and
# reconnected instead of leaving the eyes frozen mid-party.
app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": 20}
sock = Sock(app)

hub = WebSocketHub()
_calibration = calibration.load()
_last_seen = {}           # node -> epoch seconds of its last heartbeat


# --------------------------------------------------------------------------
# MQTT (ESP32 only, best effort)
# --------------------------------------------------------------------------

_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def _on_connect(client, userdata, flags, reason_code, properties):
    for node in c.NODES:
        client.subscribe(c.heartbeat_topic(node))


def _on_message(client, userdata, msg):
    parts = msg.topic.split("/")
    if len(parts) == 3 and parts[0] == "system" and parts[1] == "heartbeat":
        _last_seen[parts[2]] = time.time()


def start_mqtt(broker=BROKER):
    """Connect in the background. connect_async never blocks, and the network
    loop keeps retrying on its own, so a missing broker costs us nothing."""
    _client.on_connect = _on_connect
    _client.on_message = _on_message
    _client.connect_async(broker, 1883, 60)
    _client.loop_start()


# --------------------------------------------------------------------------
# WebSocket to the LCD
# --------------------------------------------------------------------------

@sock.route("/ws")
def ws_endpoint(ws):
    hub.add(ws)
    try:
        # Catch the page up the moment it connects, so a refresh or a
        # mid-party browser restart restores the tuning without a button press.
        hub.send(ws, {"type": "calibration", "value": _calibration})
        while ws.receive() is not None:
            pass          # the page never sends us anything; this just parks
    finally:
        hub.remove(ws)


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        buttons=BUTTONS,
        calibration=_calibration,
        limits=calibration.LIMITS,
    )


@app.route("/eyes")
def eyes_page():
    return render_template(
        "eyes.html",
        geometry=geometry,
        # Each eye is drawn as its own group, so pair every iris with its shine.
        eyes=list(zip(geometry.IRISES, geometry.SHINES)),
        lid_color=animations.LID_COLOR,
        gaze_travel=animations.GAZE_TRAVEL,
        gaze_inner_ratio=animations.GAZE_INNER_RATIO,
        calibration=_calibration,
    )


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------

@app.route("/fire/<button_id>", methods=["POST"])
def fire(button_id):
    try:
        b = button(button_id)
    except KeyError:
        return jsonify(ok=False, error=f"unknown button {button_id}"), 404

    if b["transport"] == "eyes":
        delivered = hub.broadcast({"type": "anim", "name": b["animation"]})
        return jsonify(ok=True, transport="eyes",
                       animation=b["animation"], delivered=delivered)

    _client.publish(b["topic"], b["payload"], qos=1, retain=b.get("retain", False))
    return jsonify(ok=True, transport="mqtt",
                   topic=b["topic"], payload=b["payload"])


@app.route("/eyes/calibration", methods=["GET"])
def get_calibration():
    return jsonify(ok=True, value=_calibration, limits=calibration.LIMITS)


@app.route("/eyes/calibration", methods=["POST"])
def post_calibration():
    """Push new tuning to the LCD. Every slider drag lands here so the change
    is visible immediately; only a Save writes it to disk."""
    global _calibration
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(ok=False, error="expected a JSON object"), 400

    value = calibration.sanitize(body.get("value", body))
    persist = bool(body.get("persist"))
    if persist:
        value = calibration.save(calibration.DEFAULT_PATH, value)
    _calibration = value
    delivered = hub.broadcast({"type": "calibration", "value": value})
    return jsonify(ok=True, value=value, persisted=persist, delivered=delivered)


@app.route("/status")
def status():
    now = time.time()
    return jsonify(
        eyes=hub.count(),
        nodes={n: (now - _last_seen[n] < c.HEARTBEAT_TIMEOUT) if n in _last_seen
               else False for n in c.NODES},
    )


if __name__ == "__main__":
    start_mqtt()
    # threaded=True: flask-sock parks one thread per open socket, and the
    # kiosk page holds one for the whole party.
    app.run(host="0.0.0.0", port=8080, threaded=True)
