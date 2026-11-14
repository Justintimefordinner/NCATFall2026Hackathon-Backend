"""
Voice/client.py - the voice process for the Voice MES Assistant.

Follows the team doc's "Integrating voice with the backend" rules:
  1. Send what it hears   -> POST http://<PI>/api/command
                              {"text", "confidence", "source": "voice", "speaker", "role"}
  2. Speak what the backend says -> WebSocket ws://<PI>/ws/ui, {"type": "announce"} -> TTS
  3. Respect the Listen button   -> {"type": "state", "listening": false} -> stop sending

It never decides what a command means; Backend/parser.py does that.
What this process adds on top: noise handling and two-voice speaker ID, so
background talkers and unknown voices never reach the backend at all.

Pipeline:
  USB mic -> 120 Hz high-pass -> Silero VAD -> loudness gate -> speaker ID
          -> Moonshine STT -> POST /api/command
  /ws/ui announce -> tts.py (cache / Piper, priority queue) -> USB speaker
                     (mic muted while tts.SPEAKING is set)

Run:
  python3 client.py                         # backend on this Pi (localhost:5000)
  python3 client.py --pi 10.42.0.1:5000     # backend elsewhere
  python3 client.py --open                  # accept any voice (no speaker check)
"""
import argparse
import difflib
import json
import queue
import threading
import time

import numpy as np
import requests

import models as M
import tts as T
from mic import Mic, list_devices

try:
    import websocket  # pip install websocket-client
except ImportError:
    websocket = None


class VoiceClient:
    def __init__(self, a):
        self.a = a
        self.http = f"http://{a.pi}"
        self.ws_url = f"ws://{a.pi}/ws/ui"
        print("Loading models...")
        self.vad, self.window = M.load_vad(threshold=a.vad)
        self.asr = M.load_asr()
        self.tts = T.Speaker(a.tts, a.voice, a.speed, a.out_device, a.player, mute=a.mute,
                             lead_in=a.lead_in)
        self.voices = M.load_voices()
        self.ext = M.load_speaker() if self.voices else None
        self.hp = M.HighPass()
        print(f"Enrolled voices: { {n: r for n, (_, r) in self.voices.items()} or 'NONE'}")
        if not self.voices and not a.open:
            print("!! No voices enrolled -> accepting anyone (--open). Run enroll.py to add the 2 voices.")
            a.open = True

        # listening comes from the backend's state messages (Listen button / panel).
        # Until we hear from the backend we follow --listen-default.
        self.listening = a.listen_default
        self.ws_connected = False
        self.flush = False
        self.noise_floor = 0.003
        self.buf = np.zeros(0, np.float32)

    # ---------------- backend link ----------------
    def on_ws_message(self, _ws, raw):
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        kind = msg.get("type")
        if kind == "state":
            st = msg.get("state") if isinstance(msg.get("state"), dict) else msg
            if "listening" in st:
                new = bool(st["listening"])
                if new != self.listening:
                    print(f"  [backend] listening -> {new}")
                self.listening = new
        elif kind == "announce" and msg.get("message"):
            try:
                priority = int(msg.get("priority", T.CONFIRM))
            except (TypeError, ValueError):
                priority = T.CONFIRM
            self.tts.speak(msg["message"], priority)

    def on_ws_open(self, _ws):
        self.ws_connected = True
        print(f"  [backend] connected to {self.ws_url}")

    def on_ws_close(self, *_):
        if self.ws_connected:
            print("  [backend] websocket closed, reconnecting...")
        self.ws_connected = False

    def start_ws(self):
        if websocket is None:
            print("!! websocket-client not installed: no spoken announcements. pip install websocket-client")
            return
        app = websocket.WebSocketApp(self.ws_url, on_message=self.on_ws_message,
                                     on_open=self.on_ws_open, on_close=self.on_ws_close,
                                     on_error=lambda *_: None)

        def loop():
            while True:  # run_forever returns on failure; keep retrying every 2 s
                try:
                    app.run_forever(ping_interval=10, ping_timeout=5)
                except Exception as e:
                    print(f"  [backend] ws error: {e}")
                time.sleep(2)

        threading.Thread(target=loop, daemon=True).start()

    def post(self, text, who, role, sscore):
        body = {"text": text, "confidence": 1.0, "source": "voice",
                "speaker": who, "role": role, "speaker_score": sscore}
        try:
            r = requests.post(f"{self.http}/api/command", json=body, timeout=2)
            print(f"  -> backend {r.status_code}: {r.text[:120]}")
        except requests.RequestException as e:
            print(f"  -> backend unreachable ({e.__class__.__name__})")

    # ---------------- speaking (tts.py) ----------------
    def is_echo(self, text):
        """True if the mic just picked up the bench's own announcement."""
        said, t = self.tts.last_said
        if time.time() - t > 4 or not said:
            return False
        return difflib.SequenceMatcher(None, text.lower(), said).ratio() > 0.6

    # ---------------- listening ----------------
    def calibrate(self, seconds=2.0):
        print(f"Measuring background noise for {seconds:.0f}s - stay quiet...")
        x = self.hp(self.mic.record(seconds))
        frames = x[: len(x) // 1600 * 1600].reshape(-1, 1600)
        self.noise_floor = max(float(np.median(np.sqrt((frames ** 2).mean(axis=1)))), 1e-4)
        print(f"Noise floor RMS = {self.noise_floor:.4f} (speech must be {self.a.snr}x louder)")

    def reset_vad(self):
        if hasattr(self.vad, "reset"):
            self.vad.reset()
        self.buf = np.zeros(0, np.float32)
        self.mic.drain()

    def segments(self):
        while True:
            try:
                chunk = self.mic.read(timeout=1.0)
            except queue.Empty:
                continue
            if T.is_speaking() or not self.listening:
                self.flush = True     # drop audio while talking or while Listen is off
                continue
            if self.flush:
                self.flush = False
                self.reset_vad()
                continue
            chunk = self.hp(chunk)
            if not self.vad.is_speech_detected():
                self.noise_floor = 0.98 * self.noise_floor + 0.02 * max(M.rms(chunk), 1e-4)
            self.buf = np.concatenate([self.buf, chunk])
            while len(self.buf) >= self.window:
                self.vad.accept_waveform(self.buf[: self.window])
                self.buf = self.buf[self.window:]
            while not self.vad.empty():
                seg = np.array(self.vad.front.samples, dtype=np.float32)
                self.vad.pop()
                yield seg

    def handle(self, seg):
        dur, level = len(seg) / M.SR, M.rms(seg)
        if dur < 0.3:
            return
        if level < self.noise_floor * self.a.snr:
            print(f"  [skip] too quiet vs background ({level:.4f})")
            return

        who, role, sscore = None, "operator", None
        if self.voices:
            who, sscore = M.identify(M.embed(self.ext, seg), self.voices, self.a.spk_threshold)
            if who:
                role = self.voices[who][1]
        if not who and not self.a.open:
            print(f"  [skip] unknown voice (best score {sscore})")
            return
        who = who or "guest"
        if self.a.earcon:
            self.tts.earcon()       # "heard you" before STT finishes

        t0 = time.time()
        text = M.transcribe(self.asr, M.normalize_level(seg))
        ms = int((time.time() - t0) * 1000)
        if not text.strip(" .,!?"):
            return
        if self.is_echo(text):
            print(f"  [skip] echo of own announcement: {text!r}")
            return
        if self.a.wake and not text.lower().lstrip(" ,.").startswith(("bench", "workbench", "hey bench")):
            print(f"  [skip] no wake word: {text!r}")
            return
        print(f"[{who}/{role} spk={sscore}] {text!r}  (stt {ms} ms)")
        if not self.listening:      # Listen got turned off while we were transcribing
            return
        self.post(text, who, role, sscore)

    def run(self):
        self.tts.start(prerender=not self.a.no_prerender)
        self.start_ws()
        self.mic = Mic(self.a.device).start()
        self.calibrate()
        print(f"Ready. Backend: {self.http}  listening={self.listening}  Ctrl+C to quit.\n")
        for seg in self.segments():
            try:
                self.handle(seg)
            except Exception as e:   # never crash mid-demo
                print(f"  (error: {e})")


def main():
    ap = argparse.ArgumentParser(description="Voice MES voice client")
    ap.add_argument("--pi", default="localhost:5000", help="backend host:port (e.g. 10.42.0.1:5000)")
    ap.add_argument("--device", default=None, help="mic device index/name (see --devices)")
    ap.add_argument("--out-device", default=None, help="speaker device index/name")
    ap.add_argument("--devices", action="store_true", help="list audio devices and exit")
    ap.add_argument("--open", action="store_true", help="accept any voice (skip speaker check)")
    ap.add_argument("--wake", action="store_true", help='require "bench" before each command')
    ap.add_argument("--mute", action="store_true", help="don't speak announcements (print only)")
    ap.add_argument("--listen-default", action="store_true",
                    help="send transcripts before the backend reports listening state")
    ap.add_argument("--vad", type=float, default=0.55, help="VAD threshold 0-1 (raise in loud rooms)")
    ap.add_argument("--snr", type=float, default=2.5, help="speech must be this many x louder than background")
    ap.add_argument("--spk-threshold", type=float, default=0.45, help="speaker match threshold")
    ap.add_argument("--speed", type=float, default=1.1, help="TTS speed")
    ap.add_argument("--tts", default="piper", choices=["piper", "espeak"],
                    help="TTS engine (falls back to the other if missing)")
    ap.add_argument("--voice", default=None, help="Piper voice, e.g. en_US-amy-medium (default amy-low)")
    ap.add_argument("--player", default="sounddevice", choices=["sounddevice", "aplay"],
                    help="audio output; aplay takes an ALSA name for --out-device, e.g. plughw:2,0")
    ap.add_argument("--lead-in", type=float, default=T.LEAD_IN,
                    help="seconds of silence before speech after idle (Bluetooth wake-up), default 0")
    ap.add_argument("--earcon", action="store_true", help="beep when a command is heard, before STT")
    ap.add_argument("--no-prerender", action="store_true", help="skip pre-rendering common phrases")
    a = ap.parse_args()
    if a.devices:
        return list_devices()
    to_dev = lambda d: int(d) if d is not None and str(d).isdigit() else d
    a.device = to_dev(a.device)
    a.out_device = a.out_device if a.player == "aplay" else to_dev(a.out_device)
    try:
        VoiceClient(a).run()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
