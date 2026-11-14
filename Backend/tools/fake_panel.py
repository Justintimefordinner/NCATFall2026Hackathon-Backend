"""Stands in for the ESP32 panel.

  python tools/fake_panel.py [--url ws://localhost:5000/ws/panel]
Type p + Enter for power, l + Enter for listen. Prints every lights message
(heartbeats only when they change, unless --verbose).
"""
import argparse
import asyncio
import json

import websockets

KEYS = {"p": "power", "l": "listen_toggle"}


async def main(url, verbose):
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"type": "hello", "id": "fake-panel"}))
        print("connected. p = power, l = listen, q = quit")

        async def reader():
            last = None
            async for raw in ws:
                msg = json.loads(raw)
                if verbose or msg != last:
                    print("lights:", {k: v for k, v in msg.items() if k != "type"})
                last = msg

        async def writer():
            loop = asyncio.get_running_loop()
            while True:
                key = (await loop.run_in_executor(None, input)).strip().lower()
                if key == "q":
                    return
                if key in KEYS:
                    await ws.send(json.dumps({"type": "button", "id": KEYS[key]}))

        r = asyncio.create_task(reader())
        await writer()
        r.cancel()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:5000/ws/panel")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    try:
        asyncio.run(main(a.url, a.verbose))
    except (KeyboardInterrupt, EOFError):
        pass
