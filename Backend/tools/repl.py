"""Stands in for the voice process / debug box.

Each line typed is POSTed to /api/command and the reply printed.
  python tools/repl.py [--url http://localhost:5000] [--source voice] [--confidence 0.9]
Lines starting with ':' are shortcuts:
  :power  :listen  :reset  :state
  :alert <message>   :ack <pin>   :inspect <pin> [page step]
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def call(base, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="GET" if body is None and path == "/api/state" else "POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"ok": False, "message": f"HTTP {e.code}: {e.read().decode()}"}


def shortcut(base, line):
    word, *rest = line[1:].split()
    if word == "power":   return call(base, "/api/panel/button", {"id": "power"})
    if word == "listen":  return call(base, "/api/panel/button", {"id": "listen_toggle"})
    if word == "reset":   return call(base, "/api/reset", {})
    if word == "state":   return call(base, "/api/state")
    if word == "alert":   return call(base, "/api/quality/trigger", {"message": " ".join(rest)})
    if word == "ack":     return call(base, "/api/quality/acknowledge", {"pin": rest[0] if rest else ""})
    if word == "inspect":
        body = {"pin": rest[0] if rest else ""}
        if len(rest) >= 3:
            body.update(page=int(rest[1]), step=int(rest[2]))
        return call(base, "/api/inspector/signoff", body)
    return {"ok": False, "message": f"unknown shortcut :{word}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5000")
    ap.add_argument("--source", default="debug")
    ap.add_argument("--confidence", type=float, default=1.0)
    a = ap.parse_args()
    interactive = sys.stdin.isatty()
    while True:
        try:
            line = input("> " if interactive else "").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line.startswith(":"):
            r = shortcut(a.url, line)
        else:
            r = call(a.url, "/api/command",
                     {"text": line, "confidence": a.confidence, "source": a.source})
        if "message" not in r:                      # :state
            print(json.dumps(r, indent=2))
            continue
        st = r.get("state") or {}
        mode = f" [{st['mode']}, page {st['page']['number']}, " \
               f"{st['progress']['signed']}/{st['progress']['total']}]" if st else ""
        print(("ok   " if r["ok"] else "no   ") + r["message"] + mode)


if __name__ == "__main__":
    main()
