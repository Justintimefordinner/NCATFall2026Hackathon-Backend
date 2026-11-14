"""Connected sockets and broadcasting. Never touches MES state directly except
through snapshot() / lights(), and never holds MES.lock while sending."""
import json
import threading
import time


class Hub:
    def __init__(self, mes):
        self.mes, self.ui, self.panels = mes, set(), set()
        self.lock = threading.Lock()     # serializes sends and set changes

    # ---------- messages ----------
    def state_msg(self):
        return json.dumps({"type": "state", **self.mes.snapshot()})

    def lights_msg(self):
        return json.dumps({"type": "lights", **self.mes.lights()})

    # ---------- clients ----------
    def add_ui(self, ws):
        msg = self.state_msg()
        with self.lock:
            self.ui.add(ws)
            self._try_send(self.ui, ws, [msg])

    def add_panel(self, ws):
        msg = self.lights_msg()
        with self.lock:
            self.panels.add(ws)
            self._try_send(self.panels, ws, [msg])

    def remove(self, ws):
        with self.lock:
            self.ui.discard(ws)
            self.panels.discard(ws)

    def send_to(self, ws, msg):
        """Send one message to one client, safely alongside broadcasts."""
        with self.lock:
            group = self.panels if ws in self.panels else self.ui
            self._try_send(group, ws, [msg])

    # ---------- broadcast ----------
    def publish(self, result=None):
        msgs = [self.state_msg()]
        if result is not None and result.speak:
            msgs.append(json.dumps({"type": "announce", "message": result.message}))
        lights = self.lights_msg()
        with self.lock:
            for ws in list(self.ui):
                self._try_send(self.ui, ws, msgs)
            for ws in list(self.panels):
                self._try_send(self.panels, ws, [lights])

    def heartbeat(self, interval=1.0):
        """Run in a daemon thread: resend lights so the panel knows the Pi is alive."""
        while True:
            time.sleep(interval)
            lights = self.lights_msg()
            with self.lock:
                for ws in list(self.panels):
                    self._try_send(self.panels, ws, [lights])

    @staticmethod
    def _try_send(group, ws, msgs):
        try:
            for m in msgs:
                ws.send(m)
        except Exception:
            group.discard(ws)      # dead socket, drop it
