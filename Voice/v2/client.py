"""
client.py - the voice process for the Voice MES Assistant (v2).

Follows "Integrating voice with the backend" in the team doc. It never imports
backend code and never decides what a command means.

  1. Send what it hears:   POST /api/command
        {"text", "confidence": 1.0, "source": "voice", "speaker_score"}
  2. Speak what the backend says: only {"type": "announce"} from ws /ws/ui
  3. Respect the Listen button: while listening is false, VAD and STT don't run at all

  USB mic -> 120 Hz high-pass -> Silero VAD -> loudness gate
          -> [speaker score vs supervisor || Moonshine STT] -> POST /api/command
  /ws/ui announce -> TTS -> speaker   (mic muted while speaking, plus a short tail)

Every segment and gate decision is logged with its level (risk plan: catch
silent drops), plus end-of-speech -> spoken-reply latency for each command.
A JSON line per segment goes to logs/ for later analysis.

Run:
  python client.py                          # backend on this Pi
  python client.py --device fifine          # pick the mic by name
  python client.py --set USE_GATE=false     # cut a stage
  python client.py --devices                # list audio devices
"""
import argparse
import difflib
import json
import os
import queue
import threading
import time

import numpy as np
import requests

import engines as E
import vconfig
from audio_io import SR, HighPass, Mic, Player, list_devices, rms
from pipeline import Pipeline

try:
    import websocket  # websocket-client
except ImportError:
    websocket = None


def ts():
    return time.strftime("%H:%M:%S")


class VoiceClient:
    def __init__(self, cfg, listen_default=False):
        self.cfg = cfg
        self.http = f"http://{cfg.BACKEND}"
        self.ws_url = f"ws://{cfg.BACKEND}/ws/ui"

        print(f"Voice v2  sherpa-onnx {E.sherpa_version()}  stages: {vconfig.stages(cfg)}")
        if str(E.sherpa_version()).startswith("2."):
            print("  !! sherpa-onnx 2.x: Piper TTS is known to break. Fix: pip install 'sherpa-onnx<2'")
        print("Loading models...")
        self.vad, self.window = E.load_vad(cfg)
        self.asr, asr_name = E.load_asr(cfg)
        print(f"  stt: {asr_name}")

        sup, info = (None, None)
        speaker = center = None
        if cfg.USE_SPEAKER_ID:
            sup, info = E.load_supervisor(cfg)
            if sup is not None:
                speaker = E.load_speaker(cfg)
                print(f"  speaker: supervisor '{info.get('name', '?')}' enrolled "
                      f"({info.get('samples', '?')} samples, consistency {info.get('consistency', '?')})")
                if cfg.USE_ROOM_ADJUST:
                    center, n = E.load_room(cfg)
                    print(f"  speaker: room-adjusted scores ({n} room samples)" if center is not None
                          else "  speaker: no room samples -> raw scores (enroll.py --room)")
            else:
                print("  speaker: no supervisor enrolled -> speaker_score 0.0 "
                      "(supervisor voice confirm will fail; PIN still works). Run enroll.py")
        self.has_supervisor = sup is not None
        self.pipe = Pipeline(cfg, self.asr, speaker, sup, center)

        self.tts = E.TTS(cfg)
        print(f"  tts: {self.tts.engine}")
        self.player = None
        if self.tts.engine != "none":
            try:
                self.player = Player(cfg.SPEAKER_DEVICE)
                print(f"  speaker out: {self.player.name} @ {self.player.rate} Hz")
            except Exception as e:
                print(f"  [tts] no usable speaker ({e}); announcements printed only")

        self.hp = HighPass(fc=cfg.HIGHPASS_HZ)
        self.listening = listen_default
        self.ws_up = False
        self.say_q = queue.Queue()
        self.muted_until = 0.0          # mic ignored until this time (TTS + tail)
        self.speaking = threading.Event()
        self.flush = True
        self.floor = cfg.NOISE_FLOOR_START
        self.buf = np.zeros(0, np.float32)
        self.last_said = ("", 0.0)
        self.pending = None             # (end_of_speech_time, text) of the last command sent
        self.n = 0

        os.makedirs(cfg.LOG_DIR, exist_ok=True)
        self.log_path = os.path.join(cfg.LOG_DIR, time.strftime("voice-%Y%m%d.jsonl"))

    # ---------------- logging ----------------
    def jlog(self, **kw):
        kw["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(kw) + "\n")
        except OSError:
            pass

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
                    print(f"{ts()} [backend] listening -> {new}")
                    self.flush = True
                self.listening = new
        elif kind == "announce" and msg.get("message"):
            self.say_q.put((msg["message"], time.time()))

    def start_ws(self):
        if websocket is None:
            print("  !! websocket-client missing: no Listen state, no announcements. pip install websocket-client")
            return

        def opened(_):
            self.ws_up = True
            print(f"{ts()} [backend] connected {self.ws_url}")

        def closed(*_):
            if self.ws_up:
                print(f"{ts()} [backend] connection lost, retrying...")
            self.ws_up = False

        app = websocket.WebSocketApp(self.ws_url, on_message=self.on_ws_message,
                                     on_open=opened, on_close=closed, on_error=lambda *_: None)

        def loop():
            while True:
                try:
                    app.run_forever(ping_interval=10, ping_timeout=5)
                except Exception as e:
                    print(f"  [backend] ws error: {e}")
                time.sleep(2)

        threading.Thread(target=loop, daemon=True).start()

    def post(self, r):
        body = {"text": r.text, "confidence": self.cfg.CONFIDENCE, "source": "voice",
                "speaker_score": r.spk if r.spk is not None else 0.0}
        try:
            resp = requests.post(f"{self.http}/api/command", json=body, timeout=2)
            try:
                j = resp.json()
                return resp.status_code, j.get("ok"), j.get("message", "")
            except ValueError:
                return resp.status_code, None, resp.text[:80]
        except requests.RequestException as e:
            return None, None, f"backend unreachable ({e.__class__.__name__})"

    # ---------------- speaking ----------------
    def tts_worker(self):
        while True:
            text, t_arrived = self.say_q.get()
            e2e = None
            if self.pending and t_arrived - self.pending[0] < 6:
                e2e = self.pending[0]
                self.pending = None
            print(f"{ts()}   BENCH: {text}")
            self.last_said = (text.lower(), time.time())
            if not self.player:
                if e2e:
                    print(f"           latency: end of speech -> announce {int((t_arrived - e2e) * 1000)} ms")
                continue
            x, sr = self.tts.synth(text)
            if not len(x):
                continue
            self.speaking.set()
            self.flush = True
            try:
                if e2e:
                    ms = int((time.time() - e2e) * 1000)
                    flag = "" if ms <= 1000 else "  (over 1 s target)"
                    print(f"           latency: end of speech -> spoken reply {ms} ms{flag}")
                    self.jlog(kind="latency", ms=ms, text=text)
                self.player.play(x, sr)
            except Exception as e:
                print(f"  [tts] playback error: {e}")
            finally:
                self.muted_until = time.time() + float(self.cfg.TTS_TAIL)
                self.last_said = (text.lower(), time.time())
                self.speaking.clear()

    @staticmethod
    def _norm(s):
        return " ".join("".join(ch for ch in s.lower() if ch.isalnum() or ch == " ").split())

    def is_echo(self, text):
        """Mic picked up the bench's own announcement (right after it finished talking)."""
        said, t = self.last_said
        if not self.cfg.USE_ECHO_FILTER or not said or time.time() - t > self.cfg.ECHO_WINDOW:
            return False
        return difflib.SequenceMatcher(None, self._norm(text), self._norm(said)).ratio() >= self.cfg.ECHO_SIMILARITY

    # ---------------- listening ----------------
    def reset_front(self):
        if hasattr(self.vad, "reset"):
            self.vad.reset()
        self.hp.reset()
        self.buf = np.zeros(0, np.float32)
        self.mic.drain()

    def segments(self):
        """Yields (segment, end_of_speech_time). Skips VAD/STT while not listening or speaking."""
        c = self.cfg
        while True:
            try:
                chunk = self.mic.read(timeout=1.0)
            except queue.Empty:
                continue
            if not self.listening or self.speaking.is_set() or time.time() < self.muted_until:
                self.flush = True
                continue
            if self.flush:
                self.flush = False
                self.reset_front()
                continue
            if c.USE_HIGHPASS:
                chunk = self.hp(chunk)
            if not c.USE_VAD:
                yield from self._no_vad(chunk)
                continue
            if not self.vad.is_speech_detected():
                self.floor = max(c.NOISE_FLOOR_MIN, 0.97 * self.floor + 0.03 * rms(chunk))
            self.buf = np.concatenate([self.buf, chunk])
            while len(self.buf) >= self.window:
                self.vad.accept_waveform(self.buf[: self.window])
                self.buf = self.buf[self.window:]
            while not self.vad.empty():
                seg = np.array(self.vad.front.samples, dtype=np.float32)
                self.vad.pop()
                yield seg, time.time() - c.VAD_END_SILENCE

    def _no_vad(self, chunk):
        """VAD switched off: crude energy-based segmentation so the demo still runs."""
        c = self.cfg
        loud = rms(chunk) > self.floor * c.GATE_SNR
        if loud:
            self.buf = np.concatenate([self.buf, chunk])
            self._quiet = 0.0
        elif len(self.buf):
            self._quiet = getattr(self, "_quiet", 0.0) + len(chunk) / SR
            self.buf = np.concatenate([self.buf, chunk])
            if self._quiet >= c.VAD_END_SILENCE:
                seg, self.buf = self.buf, np.zeros(0, np.float32)
                yield seg, time.time() - self._quiet
        else:
            self.floor = max(c.NOISE_FLOOR_MIN, 0.97 * self.floor + 0.03 * rms(chunk))
        if len(self.buf) > SR * c.VAD_MAX_SPEECH:
            seg, self.buf = self.buf, np.zeros(0, np.float32)
            yield seg, time.time()

    def calibrate(self, seconds=1.5):
        print(f"Measuring the room for {seconds:.1f}s, stay quiet...")
        x = self.mic.record(seconds)
        if self.cfg.USE_HIGHPASS:
            x = HighPass(fc=self.cfg.HIGHPASS_HZ)(x)
        n = len(x) // 1600
        lv = np.sqrt((x[: n * 1600].reshape(n, 1600) ** 2).mean(axis=1)) if n else np.array([rms(x)])
        self.floor = max(float(np.median(lv)), self.cfg.NOISE_FLOOR_MIN)
        note = "  !! almost silent: mic muted, gain at 0, or wrong device?" if self.floor <= self.cfg.NOISE_FLOOR_MIN else ""
        print(f"  room level {self.floor:.4f}{note}")

    def handle(self, seg, t_end):
        self.n += 1
        r = self.pipe.process(seg, self.floor)
        if r.passed and self.is_echo(r.text):
            r.passed, r.reason = False, f'echo of the bench: "{r.text}"'
        if r.passed and not self.listening:
            r.passed, r.reason = False, "listen turned off mid-command"

        print(f"{ts()} #{self.n} {r.summary()}")
        entry = dict(kind="segment", n=self.n, dur=round(r.dur, 2), level=round(r.level, 5),
                     floor=round(r.floor, 5), passed=r.passed, reason=r.reason, text=r.text,
                     stt_ms=r.stt_ms, spk=r.spk)
        if r.passed:
            self.pending = (t_end, r.text)
            code, ok, msg = self.post(r)
            print(f"           -> {code} {'ok' if ok else 'not ok'}: {msg}")
            entry.update(http=code, ok=ok, message=msg)
        self.jlog(**entry)

    def run(self, device):
        threading.Thread(target=self.tts_worker, daemon=True).start()
        self.start_ws()
        self.mic = Mic(device)
        print(f"  mic: {self.mic.name} ({self.mic.rate} Hz)")
        self.calibrate()
        for _ in range(20):
            if self.ws_up:
                break
            time.sleep(0.1)
        if not self.ws_up:
            print(f"  !! backend not reachable at {self.ws_url} yet (is the mes service running?). Will keep trying.")
        print(f"Ready. listening={self.listening}. Log: {self.log_path}. Ctrl+C to quit.\n")
        for seg, t_end in self.segments():
            try:
                self.handle(seg, t_end)
            except Exception as e:  # never crash mid-demo
                print(f"  (error: {e})")


def main():
    ap = argparse.ArgumentParser(description="Voice MES voice client v2")
    ap.add_argument("--pi", help="backend host:port (default from vconfig: BACKEND)")
    ap.add_argument("--device", help="mic name piece or index (see --devices)")
    ap.add_argument("--out-device", help="speaker name piece or index")
    ap.add_argument("--devices", action="store_true", help="list audio devices and exit")
    ap.add_argument("--mute", action="store_true", help="don't speak (print announcements only)")
    ap.add_argument("--listen-default", action="store_true",
                    help="start with listening on until the backend says otherwise")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override any vconfig setting, e.g. --set GATE_SNR=3")
    a = ap.parse_args()
    if a.devices:
        return list_devices()
    sets = list(a.set)
    if a.pi:
        sets.append(f"BACKEND={a.pi}")
    if a.out_device:
        sets.append(f"SPEAKER_DEVICE={a.out_device}")
    if a.mute:
        sets.append("USE_TTS=false")
    cfg = vconfig.load(sets)
    device = a.device if a.device is not None else cfg.MIC_DEVICE
    try:
        VoiceClient(cfg, a.listen_default).run(device)
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
