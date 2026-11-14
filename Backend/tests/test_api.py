import pytest

import config
from app import app, mes


@pytest.fixture
def client():
    mes.reset()
    return app.test_client()


def post(client, url, json=None):
    r = client.post(url, json=json)
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()


def test_walkthrough_over_http(client):
    assert post(client, "/api/panel/button", {"id": "power"})["ok"]
    r = post(client, "/api/command", {"text": "start labor", "source": "debug"})
    assert r["ok"] and r["state"]["mode"] == "working"
    # voice is ignored while listening is off: still a 200, ok false
    r = post(client, "/api/command", {"text": "step one done", "confidence": 0.9, "source": "voice"})
    assert r["ok"] is False and r["message"] == "Ignored, listening off"
    post(client, "/api/panel/button", {"id": "listen_toggle"})
    r = post(client, "/api/command", {"text": "step one done", "confidence": 0.9, "source": "voice"})
    assert r["message"] == "Step 1 signed off"
    r = post(client, "/api/command", {"text": "step two done", "source": "voice"})
    assert r["state"]["pending_inspector"] == [{"page": 1, "step": 2}]
    r = post(client, "/api/quality/trigger", {"message": "Bolt 6 not torqued"})
    assert r["state"]["quality_alert"] == "Bolt 6 not torqued"
    assert post(client, "/api/quality/acknowledge", {"pin": "nope"})["ok"] is False
    assert post(client, "/api/quality/acknowledge", {"pin": config.PIN})["ok"]
    r = post(client, "/api/inspector/signoff", {"pin": config.PIN, "page": 1, "step": 2})
    assert r["message"] == "Step 2 signed off by supervisor"
    post(client, "/api/command", {"text": "page done"})
    post(client, "/api/command", {"text": "next page"})
    r = post(client, "/api/command", {"text": "page done"})
    assert r["state"]["mode"] == "complete" and r["message"].endswith("Assembly complete")
    r = post(client, "/api/reset")
    assert r["state"]["mode"] == "idle"


def test_state_shape(client):
    s = client.get("/api/state").get_json()
    assert set(s) == {"operation", "mode", "listening", "labor", "page", "pending_inspector",
                      "progress", "quality_alert", "supervisor_challenge", "last", "log"}
    assert s["page"]["steps"][0]["image"] == "/static/img/p1s1.jpg"


def test_malformed_json_is_400(client):
    r = client.post("/api/command", data="not json", content_type="application/json")
    assert r.status_code == 400
    assert client.post("/api/command", json={"no_text": 1}).status_code == 400
    assert client.post("/api/panel/button", json={"id": "self_destruct"}).status_code == 400


def test_power_off_over_http_and_ws_ids(client):
    post(client, "/api/panel/button", {"id": "power"})
    r = post(client, "/api/panel/button", {"id": "power_off"})
    assert r["message"] == "Station off" and r["lights"]["power"] is False
    assert client.get("/api/state").get_json()["mode"] == "idle"


def test_lights_route(client):
    assert client.get("/api/panel/lights").get_json()["power"] is False


def test_cors_header(client):
    assert client.get("/api/state").headers["Access-Control-Allow-Origin"] == "*"
