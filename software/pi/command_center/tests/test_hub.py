import json
import threading

import pytest

from command_center.hub import WebSocketHub


class FakeWs:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send(self, data):
        if self.fail:
            raise ConnectionResetError("client vanished")
        self.sent.append(data)


def test_broadcast_reaches_every_client():
    hub = WebSocketHub()
    a, b = FakeWs(), FakeWs()
    hub.add(a)
    hub.add(b)
    assert hub.broadcast({"type": "anim", "name": "blink"}) == 2
    assert json.loads(a.sent[0]) == {"type": "anim", "name": "blink"}
    assert a.sent == b.sent


def test_broadcast_with_no_clients_is_harmless():
    assert WebSocketHub().broadcast({"type": "anim", "name": "blink"}) == 0


def test_a_dead_client_is_dropped_and_does_not_block_the_others():
    """The kiosk browser can disappear at any time; one press must still land
    on whatever is still listening."""
    hub = WebSocketHub()
    dead, alive = FakeWs(fail=True), FakeWs()
    hub.add(dead)
    hub.add(alive)
    assert hub.broadcast({"type": "anim", "name": "blink"}) == 1
    assert hub.count() == 1
    assert len(alive.sent) == 1


def test_remove_is_idempotent():
    hub = WebSocketHub()
    ws = FakeWs()
    hub.add(ws)
    hub.remove(ws)
    hub.remove(ws)
    assert hub.count() == 0


def test_send_to_one_client_reports_success_and_failure():
    hub = WebSocketHub()
    good, bad = FakeWs(), FakeWs(fail=True)
    assert hub.send(good, {"hello": 1}) is True
    assert hub.send(bad, {"hello": 1}) is False


def test_concurrent_adds_and_broadcasts_do_not_corrupt_the_client_set():
    """Flask-sock runs each socket on its own thread, so add/remove races with
    broadcast constantly."""
    hub = WebSocketHub()
    errors = []

    def churn():
        try:
            for _ in range(200):
                ws = FakeWs()
                hub.add(ws)
                hub.broadcast({"type": "anim", "name": "blink"})
                hub.remove(ws)
        except Exception as exc:  # pragma: no cover - only on a real race
            errors.append(exc)

    threads = [threading.Thread(target=churn) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert hub.count() == 0
