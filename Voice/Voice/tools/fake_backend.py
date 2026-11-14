"""
tools/fake_backend.py - stand-in for Justin's backend so Voice can be tested alone.

  pip install flask flask-sock
  python3 tools/fake_backend.py            # then, in another terminal: python3 client.py

Prints every transcript the voice client POSTs, and echoes it back as an
"announce" over /ws/ui so you hear the full round trip through the speaker.
Type  l  + Enter here to toggle listening (simulates the Listen button),
      a  + Enter to fire a quality alert (priority 1, should interrupt speech).
"""
import json
import threading

from flask import Flask, request, jsonify

try:
    from flask_sock import Sock
except ImportError:
    raise SystemExit("pip install flask-sock")

app = Flask(__name__)
sock = Sock(app)
clients, lock = set(), threading.Lock()
state = {"type": "state", "listening": True}


def broadcast(msg):
    data = json.dumps(msg)
    with lock:
        for ws in list(clients):
            try:
                ws.send(data)
            except Exception:
                clients.discard(ws)


@app.post("/api/command")
def command():
    d = request.get_json(force=True, silent=True) or {}
    print(f"[voice] {d.get('speaker')}/{d.get('role')} said {d.get('text')!r} conf={d.get('confidence')}")
    broadcast({"type": "announce", "message": f"Heard: {d.get('text', '')}", "priority": 2})
    return jsonify({"ok": True, "message": "heard"})


@app.post("/api/speak")
def speak():
    d = request.get_json(force=True, silent=True) or {}
    broadcast({"type": "announce", "message": d.get("text", ""), "priority": int(d.get("priority", 3))})
    return jsonify({"ok": True})


@sock.route("/ws/ui")
def ws_ui(ws):
    with lock:
        clients.add(ws)
    ws.send(json.dumps(state))
    try:
        while True:
            ws.receive()
    finally:
        with lock:
            clients.discard(ws)


def keyboard():
    while True:
        key = input().strip().lower()
        if key == "a":
            broadcast({"type": "announce", "priority": 1,
                       "message": "Quality alert: bolt 6 is not torqued to spec"})
        if key == "l":
            state["listening"] = not state["listening"]
            print(f"listening = {state['listening']}")
            broadcast(state)
            broadcast({"type": "announce",
                       "message": "Listening on" if state["listening"] else "Listening off"})


if __name__ == "__main__":
    threading.Thread(target=keyboard, daemon=True).start()
    print("Fake backend on :5000  (l + Enter: toggle listening, a + Enter: quality alert)")
    app.run(host="0.0.0.0", port=5000, threaded=True)
