"""End-to-end check of the real WebSocket.

The other tests push into the hub directly, which proves the routing but not
the handshake. This one starts the actual server and connects a real client,
so a broken flask-sock setup fails here rather than on the LCD.
"""
import importlib
import json
import socket
import threading
import urllib.request
from unittest.mock import MagicMock

import pytest
import simple_websocket
from werkzeug.serving import make_server


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    import command_center.app as mod
    importlib.reload(mod)
    mod._client = MagicMock()          # no broker in the test environment
    port = _free_port()
    httpd = make_server("127.0.0.1", port, mod.app, threaded=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"127.0.0.1:{port}", mod
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def _post(host, path, body=None):
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(
        f"http://{host}{path}", data=data, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def test_a_connecting_page_is_sent_the_current_calibration_first(server):
    host, mod = server
    ws = simple_websocket.Client(f"ws://{host}/ws")
    try:
        first = json.loads(ws.receive(timeout=5))
        assert first["type"] == "calibration"
        assert set(first["value"]) == {"scale_x", "scale_y", "offset_x", "offset_y"}
    finally:
        ws.close()


def test_a_button_press_arrives_over_the_socket(server):
    host, _ = server
    ws = simple_websocket.Client(f"ws://{host}/ws")
    try:
        ws.receive(timeout=5)                      # the calibration greeting
        assert _post(host, "/fire/eyes_blink")["delivered"] == 1
        assert json.loads(ws.receive(timeout=5)) == {"type": "anim", "name": "blink"}
    finally:
        ws.close()


def test_a_slider_drag_arrives_over_the_socket(server):
    host, _ = server
    ws = simple_websocket.Client(f"ws://{host}/ws")
    try:
        ws.receive(timeout=5)
        _post(host, "/eyes/calibration", {"value": {"scale_y": 0.85}})
        message = json.loads(ws.receive(timeout=5))
        assert message["type"] == "calibration"
        assert message["value"]["scale_y"] == 0.85
    finally:
        ws.close()


def test_two_pages_both_receive_the_same_press(server):
    """A laptop can watch alongside the LCD while the frame is being tuned."""
    host, _ = server
    a = simple_websocket.Client(f"ws://{host}/ws")
    b = simple_websocket.Client(f"ws://{host}/ws")
    try:
        a.receive(timeout=5)
        b.receive(timeout=5)
        assert _post(host, "/fire/eyes_look_left")["delivered"] == 2
        for ws in (a, b):
            assert json.loads(ws.receive(timeout=5))["name"] == "look_left"
    finally:
        a.close()
        b.close()


def test_a_closed_page_is_forgotten(server):
    host, mod = server
    ws = simple_websocket.Client(f"ws://{host}/ws")
    ws.receive(timeout=5)
    ws.close()
    # The server's reader thread needs a moment to notice the close.
    for _ in range(50):
        if mod.hub.count() == 0:
            break
        threading.Event().wait(0.05)
    assert mod.hub.count() == 0
