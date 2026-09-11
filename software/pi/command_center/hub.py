"""Fan-out for WebSocket clients.

Flask-sock gives every socket its own thread, so the client set is touched
concurrently by each connection and by whichever request thread is pushing a
message. Keeping that behind one small lock-guarded object means the routes in
app.py stay free of threading concerns, and it can be tested without a server.
"""
import json
import threading


class WebSocketHub:
    def __init__(self):
        self._clients = set()
        self._lock = threading.Lock()

    def add(self, ws):
        with self._lock:
            self._clients.add(ws)

    def remove(self, ws):
        with self._lock:
            self._clients.discard(ws)

    def count(self) -> int:
        with self._lock:
            return len(self._clients)

    def send(self, ws, message: dict) -> bool:
        """Send to one client. A failure drops it rather than raising."""
        try:
            ws.send(json.dumps(message))
            return True
        except Exception:
            self.remove(ws)
            return False

    def broadcast(self, message: dict) -> int:
        """Send to every client; returns how many actually received it.

        The send happens outside the lock so a slow or wedged socket cannot
        stall connections opening elsewhere."""
        data = json.dumps(message)
        with self._lock:
            clients = list(self._clients)
        delivered = 0
        for ws in clients:
            try:
                ws.send(data)
                delivered += 1
            except Exception:
                self.remove(ws)
        return delivered
