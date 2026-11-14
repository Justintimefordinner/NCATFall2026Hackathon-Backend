"""Hub sends: fresh lights every time, panels first, no heartbeat."""
import json

import config
from hub import Hub
from models import *
from state import MES


class FakeWS:
    def __init__(self, log, name):
        self.log, self.name = log, name

    def send(self, m):
        self.log.append((self.name, json.loads(m)))


def setup():
    m = MES(config.DATA_PATH)
    h = Hub(m)
    log = []
    panel, ui = FakeWS(log, "panel"), FakeWS(log, "ui")
    h.add_panel(panel); h.add_ui(ui)
    log.clear()
    return m, h, log


def test_publish_sends_panels_first_with_current_lights():
    m, h, log = setup()
    m.dispatch(Command(POWER, "panel")); m.dispatch(Command(START_LABOR, "debug"))
    h.publish(Result(True, "Labor started"))
    assert [n for n, _ in log] == ["panel", "ui", "ui"]
    assert log[0][1]["labor"] is True and log[2][1]["type"] == "announce"


def test_each_publish_reflects_current_state():
    m, h, log = setup()
    m.dispatch(Command(POWER, "panel")); m.dispatch(Command(START_LABOR, "debug"))
    h.publish()
    m.dispatch(Command(STOP_LABOR, "debug"))
    h.publish()
    assert [msg["labor"] for n, msg in log if n == "panel"] == [True, False]


def test_lights_include_every_key_the_firmware_reads():
    m, h, log = setup()
    h.publish()
    assert {"type", "listening", "labor", "inspector", "alert"} <= set(log[0][1])
    assert log[0][1]["type"] == "lights"


def test_alert_and_inspector_reach_the_panel():
    m, h, log = setup()
    m.dispatch(Command(POWER, "panel")); m.dispatch(Command(START_LABOR, "debug"))
    m.dispatch(Command(QUALITY_TRIGGER, "supervisor", {"message": "x"}))
    h.publish()
    assert log[0][1]["alert"] is True
    m.dispatch(Command(QUALITY_ACK, "supervisor", {"pin": config.PIN}))
    m.dispatch(Command(SIGN_STEP, "debug", {"step": 2}))
    h.publish()
    panel = [msg for n, msg in log if n == "panel"]
    assert panel[-1]["alert"] is False and panel[-1]["inspector"] is True


def test_no_heartbeat_thread():
    import threading
    import app  # noqa: F401
    assert not [t for t in threading.enumerate() if "heartbeat" in t.name]


def test_dropped_panel_is_counted():
    m, h, log = setup()

    class Dead:
        def send(self, m):
            raise OSError("gone")
    h.panels.add(Dead())
    h.publish()
    s = h.status()
    assert s["panels_dropped"] == 1 and s["panels_connected"] == 1


def test_status_route():
    from app import app
    s = app.test_client().get("/api/panel/status").get_json()
    assert {"version", "lights", "pid", "panels_connected", "screens_connected",
            "panels_dropped"} <= set(s)
    assert "heartbeat_running" not in s
