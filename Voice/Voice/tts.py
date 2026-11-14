"""
tts.py - the bench's voice: offline TTS, WAV cache, priority queue, player thread.

The backend sends text in {"type": "announce", "message", "priority"} on /ws/ui;
client.py hands it to Speaker.speak(). Nothing here decides what to say.

  engine   : Piper via sherpa-onnx (models.load_tts), falls back to espeak-ng
  cache    : tts_cache/<sha1(voice|speed|text)>.wav, loudness-normalized, silence-trimmed.
             Common phrases are pre-rendered at startup in the background; anything
             else is synthesized live the first time and then cached on disk.
  queue    : 1 = quality alert (two-tone chime, interrupts anything)
             2 = confirmation  (replaces an older confirmation, playing or queued)
             3 = info          (waits its turn)
  SPEAKING : set from playback start until ECHO_TAIL after the queue empties.
             client.py drops mic audio while it is set, so the bench never hears itself.

Try it on the Pi (needs no backend):
  python3 tts.py --say "Labor started" --out-device 2     # build step 1/2: is it audible?
  python3 tts.py --bench                                   # step 3: synth time per voice
  python3 tts.py --demo                                    # step 6: alert interrupts a confirmation
  python3 tts.py --prerender                               # fill the cache, then exit
"""
import argparse
import glob
import hashlib
import heapq
import io
import itertools
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "tts_cache")
EXTRA_PHRASES = os.path.join(HERE, "extra_phrases.txt")   # optional: one line per phrase

ALERT, CONFIRM, INFO = 1, 2, 3
ECHO_TAIL = 0.3          # keep the mic muted this long after playback (room echo)
TARGET_RMS = 0.12        # every clip ends up this loud (before the soft limiter)

SPEAKING = threading.Event()


def is_speaking():
    return SPEAKING.is_set()


# ---------------- engines ----------------
class PiperEngine:
    """Piper through sherpa-onnx. Raises if the model or library is missing."""
    def __init__(self, voice=None, speed=1.0):
        try:
            import models as M
            self.tts = M.load_tts(voice)
        except SystemExit as e:              # models.py exits on missing files / library
            raise RuntimeError(str(e)) from None
        self.voice = "piper:" + M.tts_voice_name(voice)
        self.speed = speed
        self.sample_rate = int(getattr(self.tts, "sample_rate", 22050))   # low voices: 16 kHz

    def synth(self, text):
        a = self.tts.generate(text, sid=0, speed=self.speed)
        return np.asarray(a.samples, dtype=np.float32), int(a.sample_rate)


class EspeakEngine:
    """espeak-ng: robotic but instant and on most Pi images (the 4-hour fallback)."""
    def __init__(self, voice=None, speed=1.0):
        self.bin = shutil.which("espeak-ng") or shutil.which("espeak")
        if not self.bin:
            raise RuntimeError("espeak-ng not installed (sudo apt install espeak-ng)")
        self.lang = voice or "en-us"
        self.wpm = int(165 * speed)
        self.voice = f"espeak:{self.lang}"
        self.speed = speed
        self.sample_rate = 22050

    def synth(self, text):
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:   # -w writes a correct header
            subprocess.run([self.bin, "-v", self.lang, "-s", str(self.wpm), "-w", f.name, text],
                           check=True, capture_output=True, timeout=10)
            return read_wav(f.name)


def make_engine(kind="piper", voice=None, speed=1.0):
    order = [kind] + [k for k in ("piper", "espeak") if k != kind]
    errors = []
    for k in order:
        try:
            eng = (PiperEngine if k == "piper" else EspeakEngine)(voice if k == kind else None, speed)
            if k != kind:
                print(f"!! TTS: {kind} unavailable ({errors[-1]}), using {k}")
            return eng
        except Exception as e:
            errors.append(f"{k}: {e}")
    print("!! TTS: no engine available -> announcements are printed only. " + "; ".join(errors))
    return None


# ---------------- audio helpers ----------------
def read_wav(path_or_bytes):
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes
    with wave.open(src, "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(path, x, sr):
    tmp = path + ".tmp"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(to_int16(x).tobytes())
    os.replace(tmp, path)                     # never leave a half-written clip


def to_int16(x):
    return (np.clip(x, -1.0, 1.0) * 32767).astype(np.int16)


def resample(x, sr_in, sr_out):
    if sr_in == sr_out or len(x) == 0:
        return x.astype(np.float32)
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def trim(x, sr, thresh=0.01, pad=0.03):
    """Cut leading/trailing silence so playback starts the instant it's asked to."""
    idx = np.flatnonzero(np.abs(x) > thresh)
    if len(idx) == 0:
        return x
    p = int(pad * sr)
    return x[max(idx[0] - p, 0): idx[-1] + p]


def normalize(x, sr, target=TARGET_RMS):
    """Same loudness for every clip: RMS over the voiced 20 ms frames, then a soft limiter."""
    if len(x) == 0:
        return x
    f = max(int(0.02 * sr), 1)
    frames = x[: len(x) // f * f].reshape(-1, f) if len(x) >= f else x.reshape(1, -1)
    e = np.sqrt((frames ** 2).mean(axis=1))
    voiced = e[e > e.max() * 0.1] if e.max() > 0 else e
    level = float(np.sqrt((voiced ** 2).mean())) if len(voiced) else 0.0
    if level < 1e-5:
        return x.astype(np.float32)
    y = x * (target / level)
    return (np.tanh(y * 1.2) / np.tanh(1.2)).clip(-0.98, 0.98).astype(np.float32)


def tone(freqs, sr, dur, amp, gap=0.0):
    """Sine tones in sequence with 10 ms fades (no clicks)."""
    out = []
    t = np.arange(int(dur * sr)) / sr
    fade = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.01)
    for fq in freqs:
        out += [amp * fade * np.sin(2 * np.pi * fq * t), np.zeros(int(gap * sr))]
    return np.concatenate(out).astype(np.float32)


def alert_chime(sr):
    return np.concatenate([tone([988, 740], sr, 0.16, 0.6, gap=0.04), np.zeros(int(0.12 * sr))])


def earcon(sr):
    return tone([1320], sr, 0.07, 0.35)


# ---------------- phrases worth pre-rendering ----------------
# Copied from Backend/state.py (the voice process never imports backend code).
# A phrase missing here still works: it's synthesized live once, then cached.
FIXED = [
    "Try again", "Operation complete", "Incomplete operation. Start labor or open instructions?",
    "Station off", "Listening on", "Listening off", "Labor started", "Labor already running",
    "Labor is not running", "Labor stopped. Operation complete", "Labor stopped. Operation incomplete",
    "Operation already complete", "Instructions open", "Say start labor or open instructions",
    "No next page", "No previous page", "Start labor before signing off",
    "This step requires supervisor sign-off", "Quality alert open. Supervisor must clear it",
    "Quality alert cleared", "No open quality alert", "Supervisor must sign off",
    "No step waiting on inspector", "Supervisor voice not recognized",
]
CHALLENGE_COLORS = ["red", "blue", "green", "yellow", "orange", "purple", "white", "black"]
CHALLENGE_NUMBERS = ["two", "three", "five", "six", "seven", "nine", "ten"]


def default_phrases(pages=6, steps=12):
    done = lambda s: [s, s + ". Assembly complete"]
    out = list(FIXED)
    for p in range(1, pages + 1):
        out += [f"Page {p}"] + done(f"Page {p} signed off")
    for n in range(1, steps + 1):
        out += done(f"Step {n} signed off") + done(f"Step {n} signed off by supervisor")
        out += [f"Step {n} already signed off", f"No step {n} on this page",
                f"Step {n} needs supervisor sign-off",
                f"Step {n} needs supervisor sign-off before you continue",
                f"Step {n} needs supervisor sign-off before the next page"]
    out += [f"Supervisor, confirm with: {c} {n}" for c in CHALLENGE_COLORS for n in CHALLENGE_NUMBERS]
    if os.path.exists(EXTRA_PHRASES):     # e.g. the demo's quality alerts
        with open(EXTRA_PHRASES) as f:
            out += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    return list(dict.fromkeys(out))


# ---------------- output ----------------
class SoundDeviceOut:
    """Plays float32 samples in small blocks so a clip can be cut off mid-word."""
    BLOCK = 0.04

    def __init__(self, device=None, prefer_sr=22050):
        import sounddevice as sd
        self.sd, self.device, self.stream = sd, device, None
        try:
            sd.check_output_settings(device=device, channels=1, samplerate=prefer_sr, dtype="float32")
            self.sr = prefer_sr
        except Exception:      # lots of USB speakers only do 44.1k / 48k
            self.sr = int(sd.query_devices(device, "output")["default_samplerate"])

    def open(self):
        if self.stream is None:
            self.stream = self.sd.OutputStream(device=self.device, channels=1, samplerate=self.sr,
                                               dtype="float32", latency="low")
            self.stream.start()

    def play(self, x, cut):
        """Returns False if cut short."""
        self.open()
        b = int(self.BLOCK * self.sr)
        for i in range(0, len(x), b):
            if cut.is_set():
                self.stream.abort()             # drop whatever is still buffered
                self.stream.close()
                self.stream = None
                return False
            self.stream.write(x[i:i + b].reshape(-1, 1))
        return True

    def close(self):
        if self.stream is not None:
            try:
                self.stream.stop()              # waits for the buffer to drain
                self.stream.close()
            finally:
                self.stream = None


class AplayOut:
    """Raw PCM to aplay (alsa-utils). Use if sounddevice output misbehaves."""
    def __init__(self, device=None, prefer_sr=22050):
        if not shutil.which("aplay"):
            raise RuntimeError("aplay not found (sudo apt install alsa-utils)")
        self.device, self.sr, self.proc = device, prefer_sr, None

    def open(self):
        if self.proc is None or self.proc.poll() is not None:
            cmd = ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(self.sr), "-c", "1"]
            if self.device is not None:
                cmd += ["-D", str(self.device)]
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def play(self, x, cut):
        self.open()
        b = int(0.04 * self.sr)
        t0, played = time.time(), 0
        for i in range(0, len(x), b):
            if cut.is_set():
                self.proc.kill()
                self.proc = None
                return False
            self.proc.stdin.write(to_int16(x[i:i + b]).tobytes())
            self.proc.stdin.flush()
            played += len(x[i:i + b])
            ahead = played / self.sr - (time.time() - t0)
            if ahead > 0.15:                    # don't race far ahead of the speaker
                time.sleep(ahead - 0.1)
        return True

    def close(self):
        if self.proc is not None:
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            self.proc = None


# ---------------- the speaker ----------------
class Speaker:
    def __init__(self, engine="piper", voice=None, speed=1.1, out_device=None, player="sounddevice",
                 mute=False, cache_dir=CACHE_DIR, chime=True, out=None):
        self.engine = None if mute else (make_engine(engine, voice, speed)
                                         if isinstance(engine, str) else engine)
        self.out = out
        if self.engine is not None and self.out is None:
            try:
                self.out = (AplayOut if player == "aplay" else SoundDeviceOut)(
                    out_device, getattr(self.engine, "sample_rate", 22050))
            except Exception as e:
                print(f"!! TTS: no audio output ({e}) -> announcements are printed only")
                self.engine = None
        self.cache_dir, self.chime = cache_dir, chime
        self.mem = {}                         # cache key -> samples at self.out.sr
        self.synth_lock = threading.Lock()    # engines aren't thread-safe
        self.cv = threading.Condition()
        self.pending = []                     # heap of (priority, seq, kind, text)
        self.seq = itertools.count()
        self.current = None                   # priority of the clip playing now
        self.cut = threading.Event()
        self.last_said = ("", 0.0)            # (lowercased text, time) for client.py's echo filter
        self.started = False
        if self.engine is not None:
            os.makedirs(cache_dir, exist_ok=True)
            print(f"TTS: {self.engine.voice}, output {type(self.out).__name__} @ {self.out.sr} Hz")

    # ---- public ----
    def start(self, prerender=True):
        if self.started:
            return self
        self.started = True
        if self.engine is not None:
            threading.Thread(target=self._player, name="tts-player", daemon=True).start()
            if prerender:
                threading.Thread(target=self.prerender, name="tts-prerender", daemon=True).start()
        return self

    def speak(self, text, priority=CONFIRM):
        text = " ".join(str(text).split())
        if not text:
            return
        priority = priority if priority in (ALERT, CONFIRM, INFO) else CONFIRM
        print(f"  BENCH[{priority}]: {text}")
        self.last_said = (text.lower(), time.time())
        if self.engine is None:
            return
        with self.cv:
            if priority <= CONFIRM:           # a newer alert/confirmation makes queued confirmations stale
                self.pending = [p for p in self.pending if p[0] != CONFIRM]
                heapq.heapify(self.pending)
            if self.current is not None and priority <= self.current and priority != INFO \
                    and not (priority == ALERT and self.current == ALERT):
                self.cut.set()                # alert beats anything; confirmation replaces confirmation/info
            heapq.heappush(self.pending, (priority, next(self.seq), "say", text))
            self.cv.notify()

    def earcon(self):
        """Short beep: "I heard you" before STT finishes. Never interrupts speech."""
        if self.engine is None:
            return
        with self.cv:
            if self.current is None and not self.pending:
                heapq.heappush(self.pending, (CONFIRM, next(self.seq), "earcon", ""))
                self.cv.notify()

    def prerender(self, phrases=None):
        if self.engine is None:
            return
        phrases = default_phrases() if phrases is None else phrases
        todo = [p for p in phrases if not os.path.exists(self._path(p))]
        if not todo:
            print(f"TTS: all {len(phrases)} common phrases cached")
            return
        print(f"TTS: pre-rendering {len(todo)} of {len(phrases)} phrases in the background...")
        t0 = time.time()
        for p in todo:
            try:
                self._render(p, keep=False)
            except Exception as e:
                print(f"  (tts prerender failed for {p!r}: {e})")
        print(f"TTS: pre-render done in {time.time() - t0:.1f}s")

    def wait(self, timeout=30):
        """Block until everything queued has played (for the CLI / tests)."""
        end = time.time() + timeout
        while time.time() < end and (self.pending or self.current is not None or is_speaking()):
            time.sleep(0.02)

    # ---- cache ----
    def _key(self, text):
        return hashlib.sha1(f"{self.engine.voice}|{self.engine.speed}|{text}".encode()).hexdigest()

    def _path(self, text):
        return os.path.join(self.cache_dir, self._key(text) + ".wav")

    def _render(self, text, keep=True):
        """Synthesize + normalize + write to disk. Returns samples at the output rate."""
        path = self._path(text)
        if not os.path.exists(path):              # cached reads never wait on the synth lock
            with self.synth_lock:
                if not os.path.exists(path):
                    x, sr = self.engine.synth(text)
                    write_wav(path, normalize(trim(x, sr), sr), sr)
        if not keep:
            return None
        x, sr = read_wav(path)
        y = resample(x, sr, self.out.sr)
        if keep:
            self.mem[self._key(text)] = y
        return y

    def clip(self, text):
        y = self.mem.get(self._key(text))
        if y is not None:
            return y
        t0 = time.time()
        cached = os.path.exists(self._path(text))
        y = self._render(text)
        if not cached:
            print(f"  (tts live synth {int((time.time() - t0) * 1000)} ms: {text!r})")
        return y

    # ---- player thread ----
    def _next(self):
        """Next item, or None after ECHO_TAIL of silence (then the mic may listen again)."""
        with self.cv:
            if not self.pending:
                self.cv.wait(ECHO_TAIL if is_speaking() else None)
            if not self.pending:
                return None
            item = heapq.heappop(self.pending)
            self.current = item[0]
            self.cut.clear()
            return item

    def _player(self):
        while True:
            item = self._next()
            if item is None:
                try:
                    self.out.close()
                except Exception as e:
                    print(f"  (tts output close error: {e})")
                SPEAKING.clear()
                continue
            prio, _, kind, text = item
            try:
                x = earcon(self.out.sr) if kind == "earcon" else self.clip(text)
                if prio == ALERT and self.chime:
                    x = np.concatenate([alert_chime(self.out.sr), x])
                if not self.cut.is_set():
                    SPEAKING.set()
                    self.out.play(x, self.cut)
            except Exception as e:
                print(f"  (tts/playback error: {e})")
                try:
                    self.out.close()
                except Exception:
                    pass
            finally:
                with self.cv:
                    self.current = None
                    idle = not self.pending
                if kind == "say":
                    self.last_said = (text.lower(), time.time())
            if idle:                              # let the speaker finish before the echo tail starts
                try:
                    self.out.close()
                except Exception as e:
                    print(f"  (tts output close error: {e})")


# ---------------- CLI ----------------
def _bench(args):
    sys.path.insert(0, HERE)
    import models as M
    voices = sorted(os.path.basename(p)[len("vits-piper-"):]
                    for p in glob.glob(os.path.join(M.MODELS, "vits-piper-*")) if os.path.isdir(p))
    lines = ["Labor started", "Step three signed off", "Quality alert: bolt 6 is not torqued to spec"]
    engines = [("piper", v) for v in voices] + [("espeak", None)]
    for kind, v in engines:
        try:
            eng = (PiperEngine if kind == "piper" else EspeakEngine)(v, args.speed)
        except Exception as e:
            print(f"{kind} {v or ''}: unavailable ({e})")
            continue
        eng.synth("warm up")
        for line in lines:
            t0 = time.time()
            x, sr = eng.synth(line)
            dt = time.time() - t0
            print(f"{eng.voice:40s} {dt * 1000:6.0f} ms  RTF {dt / (len(x) / sr):.2f}  {line!r}")
    print("Use a medium voice only if a short sentence stays under ~1500 ms.")


def main():
    ap = argparse.ArgumentParser(description="Bench TTS test tool")
    ap.add_argument("--say", help="speak this text and exit")
    ap.add_argument("--priority", type=int, default=CONFIRM)
    ap.add_argument("--bench", action="store_true", help="time synthesis for every installed voice")
    ap.add_argument("--demo", action="store_true", help="play a confirmation, then interrupt it with an alert")
    ap.add_argument("--prerender", action="store_true", help="fill the cache and exit")
    ap.add_argument("--tts", default="piper", choices=["piper", "espeak"])
    ap.add_argument("--voice", default=None, help="Piper voice, e.g. en_US-amy-medium")
    ap.add_argument("--speed", type=float, default=1.1)
    ap.add_argument("--out-device", default=None)
    ap.add_argument("--player", default="sounddevice", choices=["sounddevice", "aplay"])
    a = ap.parse_args()
    if a.out_device is not None and str(a.out_device).isdigit():
        a.out_device = int(a.out_device)
    if a.bench:
        return _bench(a)
    s = Speaker(a.tts, a.voice, a.speed, a.out_device, a.player)
    if a.prerender:
        return s.prerender()
    s.start(prerender=False)
    if a.say:
        s.speak(a.say, a.priority)
    elif a.demo:
        s.speak("Incomplete operation. Start labor or open instructions?", INFO)
        time.sleep(0.8)
        s.speak("Step 3 signed off", CONFIRM)
        time.sleep(0.5)
        s.speak("Quality alert: bolt 6 is not torqued to spec", ALERT)
        s.speak("Labor stopped. Operation incomplete", INFO)
    else:
        ap.print_help()
        return
    time.sleep(0.1)
    s.wait()


if __name__ == "__main__":
    main()
