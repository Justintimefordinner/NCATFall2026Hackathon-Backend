# test_server.py
import json
from flask import Flask, request, jsonify
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

lights = {"type": "lights", "listening": False, "labor": False,
          "inspector": False, "alert": False}

def on_button(btn):
    print("BUTTON:", btn)
    if btn == "listen_toggle":
        lights["listening"] = not lights["listening"]

@sock.route("/ws/panel")
def ws_panel(ws):
    print("panel connected")
    try:
        while True:
            msg = ws.receive(timeout=1)
            if msg:
                data = json.loads(msg)
                if data.get("type") == "hello":
                    print("hello from", data.get("panel"))
                elif data.get("type") == "button":
                    on_button(data.get("id"))
            ws.send(json.dumps(lights))      # state change + 1 s heartbeat
    except Exception as e:
        print("panel disconnected:", e)

@app.post("/api/panel/button")
def api_button():
    data = request.get_json(force=True, silent=True) or {}
    on_button(data.get("id"))
    return jsonify(ok=True)

@app.get("/api/panel/lights")
def api_lights():
    return jsonify(lights)

# Toggle lights from a browser: /api/test/labor, /inspector, /alert, /listening
@app.get("/api/test/<name>")
def api_test(name):
    if name in ("listening", "labor", "inspector", "alert"):
        lights[name] = not lights[name]
    return jsonify(lights)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)