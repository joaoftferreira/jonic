import importlib
import json
from unittest.mock import MagicMock

import pytest

from command_center import commands
from eyes import calibration as cal


class FakeWs:
    """Stands in for a connected kiosk page."""

    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(json.loads(data))


@pytest.fixture
def appmod(tmp_path, monkeypatch):
    import command_center.app as mod
    importlib.reload(mod)              # fresh hub and calibration per test
    mod.app.config["TESTING"] = True
    # Never touch the real calibration file from a test.
    monkeypatch.setattr(mod.calibration, "DEFAULT_PATH",
                        tmp_path / "eyes_calibration.json")
    mod._client = MagicMock()
    return mod


@pytest.fixture
def client(appmod):
    return appmod.app.test_client()


@pytest.fixture
def kiosk(appmod):
    ws = FakeWs()
    appmod.hub.add(ws)
    return ws


# --- pages -----------------------------------------------------------------

def test_remote_page_lists_every_button(client, appmod):
    body = client.get("/").get_data(as_text=True)
    for b in appmod.BUTTONS:
        assert b["id"] in body


def test_eyes_page_embeds_the_real_contour_and_all_four_ellipses(client):
    from eyes import geometry as g

    body = client.get("/eyes").get_data(as_text=True)
    assert g.CONTOUR_PATH in body
    assert body.count('class="iris"') == 2
    assert body.count('class="shine"') == 2


def test_eyes_page_carries_the_current_calibration(client, appmod):
    appmod._calibration = {"scale_x": 1.25, "scale_y": 0.8,
                           "offset_x": -5.0, "offset_y": 3.0}
    assert "1.25" in client.get("/eyes").get_data(as_text=True)


# --- firing buttons --------------------------------------------------------

def test_eye_button_broadcasts_the_animation(client, kiosk):
    resp = client.post("/fire/eyes_blink")
    assert resp.get_json() == {"ok": True, "transport": "eyes",
                               "animation": "blink", "delivered": 1}
    assert kiosk.sent[-1] == {"type": "anim", "name": "blink"}


@pytest.mark.parametrize("button_id,name", [
    ("eyes_look_left", "look_left"),
    ("eyes_look_right", "look_right"),
    ("eyes_center", "center"),
])
def test_each_gaze_button_broadcasts_its_own_animation(client, kiosk, button_id, name):
    client.post("/fire/" + button_id)
    assert kiosk.sent[-1] == {"type": "anim", "name": name}


def test_firing_with_no_kiosk_connected_still_succeeds(client):
    """The operator may press a button before the LCD has booted."""
    resp = client.post("/fire/eyes_blink")
    assert resp.status_code == 200
    assert resp.get_json()["delivered"] == 0


def test_unknown_button_is_a_404_not_a_crash(client):
    resp = client.post("/fire/no_such_button")
    assert resp.status_code == 404
    assert resp.get_json()["ok"] is False


def test_mqtt_button_publishes_and_does_not_reach_the_eyes(client, appmod, kiosk,
                                                           monkeypatch):
    """The ESP32 transport is not wired to a button yet, so exercise it directly."""
    fake = {"id": "lights_on", "label": "Lights", "transport": "mqtt",
            "topic": "lights", "payload": "on", "retain": True}
    monkeypatch.setitem(commands._BY_ID, "lights_on", fake)
    resp = client.post("/fire/lights_on")
    assert resp.get_json()["transport"] == "mqtt"
    appmod._client.publish.assert_called_once_with("lights", "on", qos=1, retain=True)
    assert kiosk.sent == []


# --- calibration -----------------------------------------------------------

def test_get_calibration_returns_the_value_and_the_slider_limits(client):
    body = client.get("/eyes/calibration").get_json()
    assert body["value"] == cal.DEFAULTS
    assert body["limits"]["scale_x"] == list(cal.LIMITS["scale_x"])


def test_posting_calibration_pushes_it_to_the_eyes(client, kiosk):
    value = {"scale_x": 1.1, "scale_y": 0.9, "offset_x": 4, "offset_y": -6}
    resp = client.post("/eyes/calibration", json={"value": value})
    assert resp.get_json()["value"] == {"scale_x": 1.1, "scale_y": 0.9,
                                        "offset_x": 4.0, "offset_y": -6.0}
    assert kiosk.sent[-1]["type"] == "calibration"
    assert kiosk.sent[-1]["value"]["scale_x"] == 1.1


def test_a_live_drag_does_not_write_to_disk(client, appmod):
    client.post("/eyes/calibration", json={"value": {"scale_x": 1.1}})
    assert not appmod.calibration.DEFAULT_PATH.exists()


def test_saving_writes_the_file(client, appmod):
    client.post("/eyes/calibration",
                json={"value": {"scale_x": 1.4}, "persist": True})
    stored = json.loads(appmod.calibration.DEFAULT_PATH.read_text())
    assert stored["scale_x"] == 1.4


def test_out_of_range_values_are_clamped_not_rejected(client):
    """A slider cannot send these, but a stale tab or a curl can."""
    resp = client.post("/eyes/calibration", json={"value": {"scale_x": 99}})
    assert resp.get_json()["value"]["scale_x"] == cal.LIMITS["scale_x"][1]


def test_non_object_body_is_rejected(client):
    assert client.post("/eyes/calibration", json=[1, 2, 3]).status_code == 400


def test_calibration_survives_for_the_next_page_that_connects(client, appmod):
    client.post("/eyes/calibration", json={"value": {"scale_y": 0.75}})
    late = FakeWs()
    appmod.hub.add(late)
    appmod.hub.send(late, {"type": "calibration", "value": appmod._calibration})
    assert late.sent[0]["value"]["scale_y"] == 0.75


# --- status ----------------------------------------------------------------

def test_status_counts_connected_eyes(client, appmod):
    assert client.get("/status").get_json()["eyes"] == 0
    appmod.hub.add(FakeWs())
    assert client.get("/status").get_json()["eyes"] == 1


def test_status_reports_a_silent_node_as_down(client, appmod):
    assert client.get("/status").get_json()["nodes"] == {"robot": False}


def test_status_reports_a_recently_heard_node_as_up(client, appmod):
    import time
    appmod._last_seen["robot"] = time.time()
    assert client.get("/status").get_json()["nodes"]["robot"] is True
