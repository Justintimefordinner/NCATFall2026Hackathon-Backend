"""Connected sockets and broadcasting. Never touches MES state directly except
through snapshot() / lights(), and never holds MES.lock while sending.

Panels get lights on connect, on hello, and after every command. There is no
periodic heartbeat: the ESP32 decides the Pi is gone from its WebSocket
connection (the library pings on its own), not from message timing.

Messages are built *inside* Hub.lock, right before they're sent, so two
broadcasts can't go out in the wrong order. Lock order is always
Hub.lock -> MES.lock (snapshot()/lights() take it briefly); MES.dispatch never
touches the hub, so this can't deadlock.
"""
import json
import os
import threading


class Hub:
    def __init__(self, mes):
        self.mes, self.ui, self.panels = mes, set(), set()
        self.lock = threading.Lock()     # serializes sends and set changes
        self.dropped = 0                 # panel sockets dropped after a failed send

    # ---------- messages ----------
    def state_msg(self):
        return json.dumps({"type": "state", **self.mes.snapshot()})

    def lights_msg(self):
        return json.dumps({"type": "lights", **self.mes.lights()})

    # ---------- clients ----------
    def add_ui(self, ws):
        with self.lock:
            self.ui.add(ws)
            self._try_send(self.ui, ws, [self.state_msg()])

    def add_panel(self, ws):
        with self.lock:
            self.panels.add(ws)
            self._try_send(self.panels, ws, [self.lights_msg()])

    def remove(self, ws):
        with self.lock:
            self.ui.discard(ws)
            self.panels.discard(ws)

    def send_lights(self, ws):
        """Current lights to one panel (reply to hello)."""
        with self.lock:
            self._try_send(self.panels, ws, [self.lights_msg()])

    # ---------- broadcast ----------
    def publish(self, result=None):
        announce = None
        if result is not None and result.speak:
            announce = json.dumps({"type": "announce", "message": result.message})
        with self.lock:
            # panels first: a tiny message, and the physical lights should feel instant
            lights = self.lights_msg()
            for ws in list(self.panels):
                self._try_send(self.panels, ws, [lights])
            msgs = [self.state_msg()] + ([announce] if announce else [])
            for ws in list(self.ui):
                self._try_send(self.ui, ws, msgs)

    def status(self):
        with self.lock:
            return {
                "pid": os.getpid(),
                "panels_connected": len(self.panels),
                "screens_connected": len(self.ui),
                "panels_dropped": self.dropped,
            }

    def _try_send(self, group, ws, msgs):
        try:
            for m in msgs:
                ws.send(m)
        except Exception as e:
            group.discard(ws)      # dead socket, drop it
            if group is self.panels:
                self.dropped += 1
                print(f"[panel] dropped after failed send: {e!r}", flush=True)
