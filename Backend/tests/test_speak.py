"""Announce priority and POST /api/speak (TTS plan, section 4)."""
import json

import pytest

import config
from app import app, hub, mes
from models import *


class FakeWS:
    def __init__(self):
        self.msgs = []

    def send(self, m):
        self.msgs.append(json.loads(m))

    def announces(self):
        return [m for m in self.msgs if m["type"] == "announce"]


@pytest.fixture
def ui():
    mes.reset()
    ws = FakeWS()
    hub.add_ui(ws)
    yield ws
    hub.remove(ws)


def test_confirmations_default_to_priority_2(ui):
    c = app.test_client()
    c.post("/api/panel/button", json={"id": "power"})
    c.post("/api/command", json={"text": "start labor"})
    assert ui.announces()[-1] == {"type": "announce", "message": "Labor started", "priority": CONFIRM}


def test_arrival_prompt_is_info(ui):
    app.test_client().post("/api/panel/button", json={"id": "power"})
    assert ui.announces()[-1]["priority"] == INFO


def test_quality_alert_is_priority_1(ui):
    c = app.test_client()
    c.post("/api/panel/button", json={"id": "power"})
    c.post("/api/quality/trigger", json={"message": "Bolt 6 not torqued"})
    a = ui.announces()[-1]
    assert a["priority"] == ALERT and a["message"] == "Quality alert: Bolt 6 not torqued"


def test_speak_broadcasts_and_logs(ui):
    r = app.test_client().post("/api/speak", json={"text": " Hello bench ", "priority": 1})
    assert r.status_code == 200 and r.get_json() == {"ok": True, "message": "Hello bench", "priority": 1}
    assert ui.announces()[-1] == {"type": "announce", "message": "Hello bench", "priority": 1}
    last = mes.snapshot()["log"][-1]
    assert last["source"] == "speak" and last["message"] == "Hello bench"
    # state changes don't happen: speech only
    assert mes.mode == IDLE


def test_speak_defaults_to_info(ui):
    app.test_client().post("/api/speak", json={"text": "hi"})
    assert ui.announces()[-1]["priority"] == INFO


@pytest.mark.parametrize("b", [{}, {"text": ""}, {"text": 3}, {"text": "x", "priority": 0},
                               {"text": "x", "priority": "high"}])
def test_speak_rejects_bad_bodies(ui, b):
    assert app.test_client().post("/api/speak", json=b).status_code == 400
