"""Hub sends: fresh lights every time, panels first, heartbeat always running."""
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


def test_heartbeat_never_sends_stale_lights():
    m, h, log = setup()
    m.dispatch(Command(POWER, "panel")); m.dispatch(Command(START_LABOR, "debug"))
    h.publish()
    m.dispatch(Command(STOP_LABOR, "debug"))       # state changes after the broadcast
    h.beat()                                        # heartbeat builds from *current* state
    panel_msgs = [msg for n, msg in log if n == "panel"]
    assert [p["labor"] for p in panel_msgs] == [True, False]


def test_lights_include_every_key_the_firmware_reads():
    m, h, log = setup()
    h.beat()
    keys = set(log[0][1])
    assert {"type", "listening", "labor", "inspector", "alert"} <= keys
    assert log[0][1]["type"] == "lights"


def test_alert_and_inspector_reach_the_panel():
    m, h, log = setup()
    m.dispatch(Command(POWER, "panel")); m.dispatch(Command(START_LABOR, "debug"))
    m.dispatch(Command(QUALITY_TRIGGER, "supervisor", {"message": "x"}))
    m.dispatch(Command(NEXT_PAGE, "debug"))         # blocked by alert, harmless
    h.beat()
    assert log[-1][1]["alert"] is True
    m.dispatch(Command(QUALITY_ACK, "supervisor", {"pin": config.PIN}))
    m.dispatch(Command(SIGN_STEP, "debug", {"step": 2}))
    h.beat()
    assert log[-1][1]["alert"] is False and log[-1][1]["inspector"] is True


def test_heartbeat_started_on_import():
    from app import hub
    assert hub._beating is True
    hub.start_heartbeat()                           # second call is a no-op


def test_heartbeat_survives_an_exception(monkeypatch):
    import threading, time as t
    m, h, log = setup()
    calls = {"n": 0}
    real = h.mes.lights

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return real()
    monkeypatch.setattr(h.mes, "lights", flaky)
    h.start_heartbeat(interval=0.02)
    t.sleep(0.2)
    assert h.status()["heartbeat_running"] is True and h.beats >= 2


def test_dropped_panel_is_counted():
    m, h, log = setup()

    class Dead:
        def send(self, m):
            raise OSError("gone")
    h.panels.add(Dead())
    h.beat()
    s = h.status()
    assert s["panels_dropped"] == 1 and s["panels_connected"] == 1


def test_status_route():
    from app import app
    s = app.test_client().get("/api/panel/status").get_json()
    assert s["heartbeat_running"] is True
    assert {"version", "lights", "panels_connected", "heartbeats_sent",
            "seconds_since_heartbeat", "panels_dropped"} <= set(s)
