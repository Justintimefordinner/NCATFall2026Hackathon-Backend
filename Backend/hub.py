"""Connected sockets and broadcasting. Never touches MES state directly except
through snapshot() / lights(), and never holds MES.lock while sending.

Messages are built *inside* Hub.lock, right before they're sent. Building them
first and then waiting for the lock let a heartbeat built from old state go out
after a newer broadcast, flipping panel lights back for up to a second.
Lock order is always Hub.lock -> MES.lock (snapshot()/lights() take it briefly);
MES.dispatch never touches the hub, so this can't deadlock.
"""
import json
import os
import threading
import time
import traceback


class Hub:
    def __init__(self, mes):
        self.mes, self.ui, self.panels = mes, set(), set()
        self.lock = threading.Lock()     # serializes sends and set changes
        self._beating = False
        self._thread = None
        self.beats = 0                   # heartbeats sent to at least one panel
        self.last_beat = None            # time.time() of the last heartbeat tick
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

    def beat(self):
        """One heartbeat: resend current lights to every panel."""
        with self.lock:
            self.last_beat = time.time()
            if not self.panels:
                return
            lights = self.lights_msg()
            for ws in list(self.panels):
                self._try_send(self.panels, ws, [lights])
            self.beats += 1

    def heartbeat(self, interval=1.0):
        print(f"[panel] heartbeat running every {interval:g} s (pid {os.getpid()})", flush=True)
        while True:
            time.sleep(interval)
            try:
                self.beat()
            except Exception:            # never let one bad tick kill the heartbeat
                traceback.print_exc()

    def status(self):
        with self.lock:
            return {
                "pid": os.getpid(),
                "panels_connected": len(self.panels),
                "screens_connected": len(self.ui),
                "heartbeat_running": bool(self._thread and self._thread.is_alive()),
                "heartbeats_sent": self.beats,
                "seconds_since_heartbeat": (None if self.last_beat is None
                                            else round(time.time() - self.last_beat, 1)),
                "panels_dropped": self.dropped,
            }

    def start_heartbeat(self, interval=1.0):
        """Start the heartbeat thread once, however the app was launched.
        The panel turns every light off after 3 s without a message."""
        with self.lock:
            if self._beating:
                return
            self._beating = True
        self._thread = threading.Thread(target=self.heartbeat, args=(interval,), daemon=True,
                                        name="panel-heartbeat")
        self._thread.start()

    def _try_send(self, group, ws, msgs):
        try:
            for m in msgs:
                ws.send(m)
        except Exception as e:
            group.discard(ws)      # dead socket, drop it
            if group is self.panels:
                self.dropped += 1
                print(f"[panel] dropped after failed send: {e!r}", flush=True)
