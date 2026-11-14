"""Flask app: HTTP routes, WebSockets, and the built frontend.

Every route does the same three things: build a Command, call mes.dispatch(),
then hub.publish(result). Routes hold no rules.
"""
import json
import os

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_sock import Sock

import config
from hub import Hub
from models import (
    ALERT, INFO, INSPECTOR_SIGNOFF, PANEL_INTENTS, QUALITY_ACK, QUALITY_TRIGGER, RESET, Command,
)
from parser import parse
from state import MES

app = Flask(__name__, static_folder=None)
sock = Sock(app)
mes = MES(config.DATA_PATH)
hub = Hub(mes)


# ---------- helpers ----------
def run(cmd):
    res = mes.dispatch(cmd)
    hub.publish(res)
    return jsonify(ok=res.ok, message=res.message, state=mes.snapshot())


def body():
    """JSON body as a dict, or 400 for malformed / non-object JSON."""
    b = request.get_json(silent=True)
    if not isinstance(b, dict):
        abort(400, "Body must be a JSON object")
    return b


@app.after_request
def cors(resp):
    # lets the Vite dev server (another port) call the API during development
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.errorhandler(400)
def bad_request(e):
    return jsonify(ok=False, message=e.description), 400


# ---------- tech / voice ----------
@app.post("/api/command")
def command():
    b = body()
    text = b.get("text")
    if not isinstance(text, str):
        abort(400, "'text' is required")
    try:
        confidence = float(b.get("confidence", 1.0))
    except (TypeError, ValueError):
        abort(400, "'confidence' must be a number")
    score = b.get("speaker_score")
    try:
        score = None if score is None else float(score)
    except (TypeError, ValueError):
        abort(400, "'speaker_score' must be a number or null")
    return run(parse(text, confidence, b.get("source", "debug"),
                     role=b.get("role"), speaker_score=score))


# ---------- supervisor ----------
@app.post("/api/inspector/signoff")
def inspector_signoff():
    b = body()
    args = {k: b[k] for k in ("pin", "page", "step") if b.get(k) is not None}
    return run(Command(INSPECTOR_SIGNOFF, "supervisor", args, raw="inspector sign-off"))


@app.post("/api/quality/trigger")
def quality_trigger():
    msg = body().get("message", "")
    return run(Command(QUALITY_TRIGGER, "supervisor", {"message": msg},
                       raw=f"quality alert: {msg}"))


@app.post("/api/quality/acknowledge")
def quality_acknowledge():
    pin = body().get("pin")
    return run(Command(QUALITY_ACK, "supervisor", {"pin": pin}, raw="quality acknowledge"))


@app.post("/api/speak")
def speak():
    """Make the bench say something (supervisor screen, testers, faked demo alerts).
    Only broadcasts an announce; the voice process does the audio."""
    b = body()
    text = b.get("text")
    if not isinstance(text, str) or not text.strip():
        abort(400, "'text' is required")
    try:
        priority = int(b.get("priority", INFO))
    except (TypeError, ValueError):
        abort(400, "'priority' must be 1, 2 or 3")
    if not ALERT <= priority <= INFO:
        abort(400, "'priority' must be 1, 2 or 3")
    text = text.strip()
    mes.record_announcement(text)
    hub.announce(text, priority)
    return jsonify(ok=True, message=text, priority=priority)


@app.post("/api/reset")
def reset():
    return run(Command(RESET, "supervisor", raw="reset"))


@app.get("/api/state")
def state():
    return jsonify(mes.snapshot())


# ---------- panel (HTTP fallback) ----------
def panel_button(button_id):
    if button_id not in PANEL_INTENTS:
        print(f"[panel] unknown button id {button_id!r}", flush=True)
        return None
    res = mes.dispatch(Command(button_id, "panel", raw=button_id))
    print(f"[panel] {button_id} -> {res.message} (mode {mes.mode})", flush=True)
    hub.publish(res)
    return res


@app.post("/api/panel/button")
def http_panel_button():
    res = panel_button(body().get("id"))
    if res is None:
        abort(400, f"'id' must be one of {sorted(PANEL_INTENTS)}")
    return jsonify(ok=res.ok, message=res.message, lights=mes.lights())


@app.get("/api/panel/lights")
def http_panel_lights():
    return jsonify(mes.lights())


def _git_version():
    try:
        import subprocess
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=config.BASE_DIR,
                              capture_output=True, text=True, timeout=2).stdout.strip() or None
    except Exception:
        return None


VERSION = _git_version()


@app.get("/api/panel/status")
def http_panel_status():
    """Is a panel connected, and which code is running? For debugging on the Pi."""
    return jsonify(version=VERSION, lights=mes.lights(), **hub.status())


# ---------- WebSockets ----------
@sock.route("/ws/ui")
def ws_ui(ws):
    hub.add_ui(ws)
    try:
        while True:
            ws.receive()        # clients don't send anything; this blocks until disconnect
    finally:
        hub.remove(ws)


@sock.route("/ws/panel")
def ws_panel(ws):
    print("[panel] connected", flush=True)
    hub.add_panel(ws)
    try:
        while True:
            raw = ws.receive()
            try:
                msg = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if msg.get("type") == "hello":
                print(f"[panel] hello from {msg.get('panel') or msg.get('id')}", flush=True)
                hub.send_lights(ws)
            elif msg.get("type") == "button":
                panel_button(msg.get("id"))
    finally:
        hub.remove(ws)
        print("[panel] disconnected", flush=True)


# ---------- images and frontend ----------
@app.get("/static/img/<path:name>")
def image(name):
    return send_from_directory(config.IMG_DIR, name)


@app.get("/")
@app.get("/tech")
@app.get("/supervisor")
def index():
    if not os.path.isfile(os.path.join(config.FRONTEND_DIST, "index.html")):
        return ("Frontend not built. Run `npm run build` in the frontend repo, "
                "or set MES_FRONTEND_DIST.", 404)
    return send_from_directory(config.FRONTEND_DIST, "index.html")


@app.get("/<path:name>")
def frontend_file(name):
    return send_from_directory(config.FRONTEND_DIST, name)


def main():
    app.run(host=config.HOST, port=config.PORT, threaded=True)


if __name__ == "__main__":
    main()
